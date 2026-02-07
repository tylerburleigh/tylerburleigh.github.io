#!/usr/bin/env python3
import argparse
import json
import sys
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

# Build AST nodes for each article
children = []
for article in articles:
    pub_info = article.get("pub-info", {})
    reference = pub_info.get("reference", article.get("title", "Untitled"))
    links = pub_info.get("links", [])

    # Build link list
    link_nodes = [
        u.list_item([
            {"type": "paragraph", "children": [
                u.link([u.text("Full details")], f"/{article['path']}")
            ]}
        ])
    ]
    for lnk in (links or []):
        url = lnk.get("url", "")
        if lnk.get("local"):
            article_dir = "/".join(article["path"].split("/")[:-1])
            url = f"/{article_dir}/{url}"
        link_nodes.append(
            u.list_item([
                {"type": "paragraph", "children": [
                    u.link([u.text(lnk.get("name", "Link"))], url)
                ]}
            ])
        )

    # Build category tags
    cat_text = ", ".join(article.get("categories", []) or [])

    card_children = [
        {"type": "paragraph", "children": [{"type": "html", "value": reference}]},
    ]
    if cat_text:
        card_children.append(
            {"type": "paragraph", "children": [
                u.strong([u.text("Topics: ")]),
                u.text(cat_text)
            ]}
        )
    card_children.append(u.list_(link_nodes))

    children.append({
        "type": "div",
        "children": card_children,
    })


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
