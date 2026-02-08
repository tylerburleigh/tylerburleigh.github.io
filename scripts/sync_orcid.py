#!/usr/bin/env python3
"""Sync publications from ORCID to local research/articles/ directory.

Fetches works from an ORCID profile, reconciles against existing local
articles (matched by DOI), and generates stub index.md files for new works.
Never overwrites existing articles.

Usage:
    python scripts/sync_orcid.py --dry-run    # Preview what would be created
    python scripts/sync_orcid.py              # Create stubs
    python scripts/sync_orcid.py --verbose    # Detailed API output
"""

import argparse
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
import yaml

ORCID_ID = "0000-0002-9064-8876"
ORCID_API = f"https://pub.orcid.org/v3.0/{ORCID_ID}"
ARTICLES_DIR = Path("research/articles")

# Rate-limit delay between API calls (seconds)
API_DELAY = 0.5

# Titles to exclude from sync (e.g. unpublished posters with no public record)
EXCLUDED_TITLES = [
    "The Uncanny Valley: Do Framing and Familiarity Effects Alter Affective Responses?",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def make_article_slug(authors: list[dict], year: str, existing_slugs: set[str]) -> str:
    """Generate a slug like first-author-et-al-2024, avoiding collisions."""
    if not authors:
        return f"unknown-{year}"

    def last_name(author: dict) -> str:
        family = author.get("family", "")
        if family:
            return slugify(family)
        # Fall back to full name, take last word
        name = author.get("name", "unknown")
        parts = name.strip().split()
        return slugify(parts[-1]) if parts else "unknown"

    n = len(authors)
    first = last_name(authors[0])

    if n == 1:
        base = f"{first}-{year}"
    elif n == 2:
        second = last_name(authors[1])
        base = f"{first}-{second}-{year}"
    else:
        base = f"{first}-et-al-{year}"

    slug = base
    suffix_idx = 0
    while slug in existing_slugs:
        suffix_idx += 1
        # b, c, d, ...
        letter = chr(ord("a") + suffix_idx)
        slug = f"{base}{letter}"

    return slug


def normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace for comparison."""
    t = title.lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def titles_similar(a: str, b: str) -> bool:
    """Check if two titles are similar enough to be the same work."""
    na, nb = normalize_title(a), normalize_title(b)
    if na == nb:
        return True
    # Check if one is a substring of the other (covers truncated titles)
    if len(na) > 20 and len(nb) > 20:
        shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
        if shorter in longer:
            return True
    return False


# ---------------------------------------------------------------------------
# ORCID API
# ---------------------------------------------------------------------------

def fetch_orcid_works(verbose: bool = False) -> list[dict]:
    """Fetch all works from ORCID profile. Returns list of work summaries."""
    url = f"{ORCID_API}/works"
    headers = {"Accept": "application/json"}

    if verbose:
        print(f"  GET {url}")

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    works = []
    for group in data.get("group", []):
        summaries = group.get("work-summary", [])
        if not summaries:
            continue
        # Take the first (preferred) summary
        summary = summaries[0]
        work = parse_work_summary(summary)
        if work:
            works.append(work)

    return works


def parse_work_summary(summary: dict) -> dict | None:
    """Extract key fields from an ORCID work summary."""
    title_obj = summary.get("title", {})
    title_val = title_obj.get("title", {})
    title = title_val.get("value", "") if isinstance(title_val, dict) else ""
    if not title:
        return None

    # Extract DOI from external IDs
    doi = None
    ext_ids = summary.get("external-ids", {}).get("external-id", [])
    for eid in ext_ids:
        if eid.get("external-id-type", "").lower() == "doi":
            doi = eid.get("external-id-value", "")
            break

    # Publication date
    pub_date = summary.get("publication-date") or {}
    year = (pub_date.get("year") or {}).get("value", "")
    month = (pub_date.get("month") or {}).get("value", "01")
    day = (pub_date.get("day") or {}).get("value", "01")

    # Put code (for fetching detailed record)
    put_code = summary.get("put-code")

    return {
        "title": title,
        "doi": doi,
        "year": year,
        "month": month,
        "day": day,
        "put_code": put_code,
        "type": summary.get("type", ""),
    }


def fetch_orcid_work_detail(put_code: int, verbose: bool = False) -> dict:
    """Fetch detailed work record from ORCID (for works without DOI)."""
    url = f"{ORCID_API}/work/{put_code}"
    headers = {"Accept": "application/json"}

    if verbose:
        print(f"  GET {url}")

    time.sleep(API_DELAY)
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    authors = []
    contributors = data.get("contributors", {}).get("contributor", [])
    for contrib in contributors:
        credit_name = contrib.get("credit-name", {})
        name = credit_name.get("value", "") if isinstance(credit_name, dict) else ""
        if name:
            authors.append({"name": name})

    citation_text = ""
    citation_obj = data.get("citation", {})
    if citation_obj and citation_obj.get("citation-type") == "bibtex":
        citation_text = citation_obj.get("citation-value", "")

    return {"authors": authors, "citation_bibtex": citation_text}


# ---------------------------------------------------------------------------
# DOI metadata
# ---------------------------------------------------------------------------

def fetch_doi_metadata(doi: str, verbose: bool = False) -> dict:
    """Fetch structured metadata from doi.org via content negotiation."""
    url = f"https://doi.org/{doi}"

    # CSL JSON for structured data
    if verbose:
        print(f"  GET {url} (CSL JSON)")

    time.sleep(API_DELAY)
    resp = requests.get(
        url,
        headers={"Accept": "application/vnd.citationstyles.csl+json"},
        timeout=30,
        allow_redirects=True,
    )
    resp.raise_for_status()
    csl = resp.json()

    # APA citation
    if verbose:
        print(f"  GET {url} (APA)")

    time.sleep(API_DELAY)
    resp = requests.get(
        url,
        headers={"Accept": "text/x-bibliography; style=apa"},
        timeout=30,
        allow_redirects=True,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    apa = resp.text.strip()

    authors = []
    for author in csl.get("author", []):
        if "family" in author:
            authors.append({"family": author["family"], "given": author.get("given", "")})
        elif "literal" in author:
            authors.append({"name": author["literal"]})

    # Parse date
    date_parts = csl.get("issued", {}).get("date-parts", [[]])
    parts = date_parts[0] if date_parts else []
    year = str(parts[0]) if len(parts) > 0 else ""
    month = str(parts[1]).zfill(2) if len(parts) > 1 else "01"
    day = str(parts[2]).zfill(2) if len(parts) > 2 else "01"

    return {
        "title": csl.get("title", ""),
        "authors": authors,
        "year": year,
        "month": month,
        "day": day,
        "apa_citation": apa,
        "doi": doi,
    }


# ---------------------------------------------------------------------------
# Local article scanning
# ---------------------------------------------------------------------------

def scan_local_articles() -> tuple[dict[str, dict], list[dict]]:
    """Scan existing articles. Returns (doi_index, all_articles).

    doi_index: dict keyed by lowercase DOI
    all_articles: list of all articles (including those without DOI)
    """
    doi_index = {}
    all_articles = []

    if not ARTICLES_DIR.exists():
        return doi_index, all_articles

    for index_path in sorted(ARTICLES_DIR.glob("*/index.md")):
        try:
            text = index_path.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            if len(parts) < 3:
                continue
            meta = yaml.safe_load(parts[1])
            if not meta:
                continue
            doi = meta.get("doi", "")
            slug = index_path.parent.name
            entry = {
                "slug": slug,
                "title": meta.get("title", ""),
                "doi": doi,
                "path": str(index_path.parent),
            }
            all_articles.append(entry)
            if doi:
                doi_index[doi.lower()] = entry
        except Exception:
            continue

    return doi_index, all_articles


# ---------------------------------------------------------------------------
# Stub generation
# ---------------------------------------------------------------------------

def format_author_name(author: dict) -> str:
    """Format an author dict into a display name."""
    if "given" in author and "family" in author:
        return f"{author['given']} {author['family']}"
    return author.get("name", "Unknown")


def format_apa_with_doi_link(apa: str, doi: str) -> str:
    """Append DOI link to APA citation if not already present."""
    # Remove trailing DOI URL if doi.org already appended by the API
    apa = re.sub(r"\s*https?://doi\.org/\S+\s*$", "", apa)
    # Remove trailing period for clean append
    apa = apa.rstrip(". ")
    return f"{apa}. doi: <a href=\"https://doi.org/{doi}\"><code>{doi}</code></a>"


def generate_stub(metadata: dict) -> str:
    """Generate index.md content for a new article."""
    fm = {
        "title": metadata["title"],
        "date": f"{metadata['year']}-{metadata['month']}-{metadata['day']}",
        "author": [{"name": format_author_name(a)} for a in metadata["authors"]],
    }

    if metadata.get("doi"):
        fm["doi"] = metadata["doi"]

    doi = metadata.get("doi", "")
    apa = metadata.get("apa_citation", "")
    reference = ""
    if apa and doi:
        reference = format_apa_with_doi_link(apa, doi)
    elif apa:
        reference = apa

    links = []
    if doi:
        links.append({
            "name": "Final version",
            "url": f"https://doi.org/{doi}",
            "icon": "fa-solid fa-scroll",
        })

    fm["options"] = {
        "categories": [],
        "pub-info": {
            "reference": reference,
            "links": links,
        },
    }

    # Use block scalar style for reference
    yaml_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return f"---\n{yaml_str}---\n"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def run(dry_run: bool = False, verbose: bool = False) -> None:
    print(f"Fetching works from ORCID {ORCID_ID}...")
    orcid_works = fetch_orcid_works(verbose=verbose)
    print(f"  Found {len(orcid_works)} works on ORCID\n")

    print("Scanning local articles...")
    local_doi_index, all_local = scan_local_articles()
    local_dois = set(local_doi_index.keys())
    existing_slugs = {a["slug"] for a in all_local}
    print(f"  Found {len(all_local)} local articles\n")

    # Collect all ORCID titles and DOIs for SSRN dedup
    all_orcid_titles = [w["title"] for w in orcid_works]
    all_orcid_dois = {w["doi"].lower() for w in orcid_works if w.get("doi")}

    skipped = []
    existing = []
    to_create = []

    for work in orcid_works:
        doi = work.get("doi", "")
        title = work["title"]

        # Check exclusion list
        if any(titles_similar(title, exc) for exc in EXCLUDED_TITLES):
            skipped.append({"title": title, "doi": doi, "reason": "excluded"})
            continue

        # Check if already exists locally by DOI
        if doi and doi.lower() in local_dois:
            existing.append({"title": title, "doi": doi, "reason": "DOI match"})
            continue

        # Check if already exists locally by title similarity
        if any(titles_similar(title, a["title"]) for a in all_local):
            existing.append({"title": title, "doi": doi, "reason": "title match"})
            continue

        # SSRN dedup: skip preprints when a published version exists
        if doi and doi.lower().startswith("10.2139/ssrn"):
            has_published = False
            for other_work in orcid_works:
                other_doi = other_work.get("doi", "")
                if other_doi and not other_doi.lower().startswith("10.2139/ssrn"):
                    if titles_similar(title, other_work["title"]):
                        has_published = True
                        break
            # Also check local articles
            if not has_published:
                for local in all_local:
                    if titles_similar(title, local["title"]):
                        has_published = True
                        break
            if has_published:
                skipped.append({"title": title, "doi": doi, "reason": "SSRN preprint (published version exists)"})
                continue

        to_create.append(work)

    # Report
    print("=" * 60)
    print(f"  Existing (skip):  {len(existing)}")
    print(f"  SSRN dupes (skip): {len(skipped)}")
    print(f"  New to create:    {len(to_create)}")
    print("=" * 60)

    if verbose or dry_run:
        if existing:
            print("\n--- Existing articles (skipped) ---")
            for e in existing:
                print(f"  [{e['reason']}] {e['title']}")
                if e['doi']:
                    print(f"    DOI: {e['doi']}")

        if skipped:
            print("\n--- SSRN duplicates (skipped) ---")
            for s in skipped:
                print(f"  {s['title']}")
                print(f"    DOI: {s['doi']} — {s['reason']}")

    if not to_create:
        print("\nNothing new to create. All synced!")
        return

    print(f"\n--- New articles to create ({len(to_create)}) ---")
    for work in to_create:
        doi = work.get("doi", "")
        print(f"\n  Title: {work['title']}")
        print(f"  DOI:   {doi or '(none)'}")
        print(f"  Year:  {work['year']}")

    if dry_run:
        print("\n[DRY RUN] No files created.")
        return

    # Create stubs
    print("\nCreating article stubs...\n")
    created = 0

    for work in to_create:
        doi = work.get("doi", "")
        title = work["title"]

        try:
            if doi:
                # Fetch rich metadata from DOI
                print(f"  Fetching metadata for: {title[:60]}...")
                metadata = fetch_doi_metadata(doi, verbose=verbose)
            else:
                # Fetch from ORCID detailed record
                print(f"  Fetching ORCID detail for: {title[:60]}...")
                detail = fetch_orcid_work_detail(work["put_code"], verbose=verbose)
                metadata = {
                    "title": title,
                    "authors": detail["authors"],
                    "year": work["year"],
                    "month": work["month"],
                    "day": work["day"],
                    "doi": "",
                    "apa_citation": "",
                }

            if not metadata.get("authors"):
                # Fallback: use title to create a minimal stub
                metadata["authors"] = []

            slug = make_article_slug(metadata.get("authors", []), metadata.get("year", work["year"]), existing_slugs)
            existing_slugs.add(slug)

            article_dir = ARTICLES_DIR / slug
            article_dir.mkdir(parents=True, exist_ok=True)

            stub = generate_stub(metadata)
            index_path = article_dir / "index.md"
            index_path.write_text(stub, encoding="utf-8")

            print(f"  -> Created {index_path}")
            created += 1

        except Exception as e:
            print(f"  !! Error processing '{title}': {e}")
            if verbose:
                import traceback
                traceback.print_exc()

    print(f"\nDone! Created {created} new article stubs.")


def main():
    parser = argparse.ArgumentParser(description="Sync ORCID publications to local research/articles/")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating files")
    parser.add_argument("--verbose", action="store_true", help="Show detailed API output")
    args = parser.parse_args()

    # Ensure we run from repo root
    if not ARTICLES_DIR.exists():
        script_dir = Path(__file__).resolve().parent
        repo_root = script_dir.parent
        os.chdir(repo_root)
        if not ARTICLES_DIR.exists():
            print(f"Error: {ARTICLES_DIR} not found. Run from repo root.", file=sys.stderr)
            sys.exit(1)

    run(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
