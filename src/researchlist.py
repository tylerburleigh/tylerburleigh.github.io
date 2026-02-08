#!/usr/bin/env python3
import argparse
import json
import re
import sys
from urllib.parse import quote
from yaml import safe_load
from pathlib import Path
import unist as u

root = Path(__file__).parent.parent

# Scan research articles
articles = []
for ifile in sorted(root.glob("research/articles/*/index.md")):
    text = ifile.read_text()
    try:
        _, meta, content = text.split("---", 2)
    except Exception:
        print(f"Skipping file with error: {ifile}", file=sys.stderr)
        continue
    meta = safe_load(meta)
    meta["path"] = str(ifile.relative_to(root).with_suffix(""))
    articles.append(meta)

# Sort by date descending
articles.sort(key=lambda x: str(x.get("date", "")), reverse=True)

# Plugin declaration
plugin = {
    "name": "Research article list",
    "directives": [
        {
            "name": "researchlist",
            "doc": "Display a list of research articles",
            "arg": {},
            "options": {},
        }
    ],
}

# Strip HTML tags from reference text
def strip_html(text):
    return re.sub(r"<[^>]+>", "", text)


# Build AST nodes for each article
children = []
for article in articles:
    opts = article.get("options", {})
    pub_info = opts.get("pub-info", {})
    reference = pub_info.get("reference", article.get("title", "Untitled"))
    clean_reference = strip_html(reference)
    links = pub_info.get("links", [])

    # Build footer children: topics on one line, links on the next
    footer_children = []

    cat_text = ", ".join(opts.get("categories", []) or [])
    if cat_text:
        footer_children.append(
            {"type": "paragraph", "children": [
                u.strong([u.text("Topics: ")]),
                u.text(cat_text),
            ]}
        )

    link_nodes = []
    for lnk in (links or []):
        url = lnk.get("url", "")
        if lnk.get("local"):
            article_dir = "/".join(article["path"].split("/")[:-1])
            # Use absolute URL so MyST treats it as external and skips asset hashing
            url = f"https://tylerburleigh.com/{article_dir}/{url}"
        if link_nodes:
            link_nodes.append(u.text(" | "))
        link_nodes.append(
            u.link([u.text(lnk.get("name", "Link"))], url)
        )

    # Auto-detect full-text markdown (any .md that isn't index.md)
    article_dir_path = root / "/".join(article["path"].split("/")[:-1])
    fulltext_md = next((f for f in article_dir_path.glob("*.md") if f.name != "index.md"), None)
    if fulltext_md:
        article_dir = "/".join(article["path"].split("/")[:-1])
        md_url = f"https://tylerburleigh.com/{article_dir}/{quote(fulltext_md.name)}"
        if link_nodes:
            link_nodes.append(u.text(" | "))
        link_nodes.append(u.link([u.text("Markdown")], md_url))

    if link_nodes:
        footer_children.append({"type": "paragraph", "children": link_nodes})

    card = {
        "type": "card",
        "url": f"/{article['path']}",
        "children": [
            {"type": "cardTitle", "children": [u.text(article.get("title", "Untitled"))]},
            {"type": "paragraph", "children": [u.text(clean_reference)]},
        ],
    }
    if footer_children:
        card["children"].append({"type": "footer", "children": footer_children})

    children.append(card)


def declare_result(content):
    """Declare result as JSON to stdout"""
    json.dump(content, sys.stdout, indent=2)
    raise SystemExit(0)


def run_directive(name, data):
    """Execute a directive with the given name and data"""
    assert name == "researchlist"
    return children


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--role")
    group.add_argument("--directive")
    group.add_argument("--transform")
    args = parser.parse_args()

    if args.directive:
        data = json.load(sys.stdin)
        declare_result(run_directive(args.directive, data))
    elif args.transform:
        raise NotImplementedError
    elif args.role:
        raise NotImplementedError
    else:
        declare_result(plugin)
