#!/usr/bin/env python3
"""Convert research article PDFs to markdown using pymupdf4llm, with optional LLM cleanup."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = ROOT / "research" / "articles"


def find_articles(slug=None):
    """Find articles that have PDFs. Returns list of (slug, pdf_path) tuples."""
    results = []
    if slug:
        article_dir = ARTICLES_DIR / slug
        if not article_dir.is_dir():
            print(f"Article directory not found: {article_dir}", file=sys.stderr)
            return results
        dirs = [article_dir]
    else:
        dirs = sorted(d for d in ARTICLES_DIR.iterdir() if d.is_dir())

    for d in dirs:
        pdfs = list(d.glob("*.pdf"))
        if pdfs:
            results.append((d.name, pdfs[0]))
    return results


def get_md_path(pdf_path):
    """Return the markdown output path: same name as the PDF but with .md extension."""
    return pdf_path.with_suffix(".md")


def find_fulltext_md(article_dir):
    """Find the full-text markdown file in an article directory (any .md that isn't index.md)."""
    for md in article_dir.glob("*.md"):
        if md.name != "index.md":
            return md
    return None


def parse_pdf(pdf_path):
    """Parse a PDF file to markdown using pymupdf4llm."""
    import pymupdf4llm

    return pymupdf4llm.to_markdown(str(pdf_path))


LLM_PROMPT = """\
You are a document cleanup assistant. The following markdown was machine-extracted \
from an academic PDF. Clean it up by fixing these common artifacts:

1. Remove page headers, footers, and page numbers
2. Fix words broken across lines by hyphens (e.g., "re-\\nsearch" → "research")
3. Fix broken tables — reconstruct proper markdown table formatting
4. Remove duplicate section headings caused by page breaks
5. Fix garbled equations and mathematical notation where possible
6. Remove any watermarks or publisher boilerplate
7. Preserve all actual content, citations, and references exactly
8. If the paper uses numerical reference indices (e.g., [1], [2]) as inline \
citations, collect all referenced works and ensure they appear in a proper \
"References" section at the end of the document
9. NEVER omit, abbreviate, or summarize table data. Reproduce ALL table rows \
and columns with their exact numeric values. Do not replace data with "..." or \
placeholder text like "[Table X goes here]". Every table must be fully reproduced.

Return ONLY the cleaned markdown, no commentary.

---

"""


def llm_cleanup(raw_markdown):
    """Clean up raw markdown using GPT-4.1 via OpenAI API."""
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not set, skipping LLM cleanup", file=sys.stderr)
        return raw_markdown

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "user", "content": LLM_PROMPT + raw_markdown},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content


def main():
    parser = argparse.ArgumentParser(description="Convert research PDFs to markdown")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be parsed")
    parser.add_argument("--force", action="store_true", help="Re-parse even if markdown exists")
    parser.add_argument("--article", type=str, help="Parse a single article by slug")
    parser.add_argument("--llm", action="store_true", help="Post-process with GPT-4.1 cleanup")
    args = parser.parse_args()

    articles = find_articles(args.article)

    if not articles:
        print("No articles with PDFs found.")
        return

    for slug, pdf_path in articles:
        output_path = get_md_path(pdf_path)
        existing = find_fulltext_md(pdf_path.parent)

        if existing and not args.force:
            print(f"  SKIP {slug} ({existing.name} exists, use --force to overwrite)")
            continue

        # If forcing and there's an old file with a different name, remove it
        if args.force and existing and existing != output_path:
            existing.unlink()

        if args.dry_run:
            print(f"  WOULD PARSE {slug}: {pdf_path.name} → {output_path.name}")
            continue

        print(f"  PARSING {slug}: {pdf_path.name} ...", end=" ", flush=True)
        markdown = parse_pdf(pdf_path)

        if args.llm:
            print("cleaning with LLM ...", end=" ", flush=True)
            markdown = llm_cleanup(markdown)

        output_path.write_text(markdown, encoding="utf-8")
        print(f"done → {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
