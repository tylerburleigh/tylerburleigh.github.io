#!/usr/bin/env python3
import argparse
import json
import sys
from urllib.parse import quote
from yaml import safe_load
from pathlib import Path
import unist as u

root = Path(__file__).parent.parent

# Scan research articles and build slug → metadata lookup
# Slug is the directory name, e.g. "kennedy-et-al-2020"
article_meta = {}
for ifile in sorted(root.glob("research/articles/*/index.md")):
    text = ifile.read_text()
    try:
        _, meta, content = text.split("---", 2)
    except Exception:
        print(f"Skipping file with error: {ifile}", file=sys.stderr)
        continue
    meta = safe_load(meta)
    slug = ifile.parent.name
    meta["_path"] = str(ifile.relative_to(root).with_suffix(""))
    article_meta[slug] = meta

# Plugin declaration
plugin = {
    "name": "Article info injector",
    "directives": [
        {
            "name": "articleinfo",
            "doc": "Display topic and link metadata for a research article.",
            "arg": {"type": "string", "doc": "Article directory slug"},
            "options": {},
        }
    ],
}


def build_info_nodes(meta):
    """Build the metadata AST nodes for an article."""
    opts = meta.get("options", {})
    pub_info = opts.get("pub-info", {})
    categories = opts.get("categories", []) or []
    links = pub_info.get("links", []) or []

    inner_children = []

    # Topics line
    if categories:
        cat_text = ", ".join(categories)
        inner_children.append({
            "type": "paragraph",
            "children": [
                u.strong([u.text("Topics: ")]),
                u.text(cat_text),
            ],
        })

    # Links line
    link_nodes = []
    for lnk in links:
        url = lnk.get("url", "")
        if lnk.get("local"):
            article_dir = "/".join(meta["_path"].split("/")[:-1])
            url = f"https://tylerburleigh.com/{article_dir}/{url}"
        if link_nodes:
            link_nodes.append(u.text(" | "))
        link_nodes.append(u.link([u.text(lnk.get("name", "Link"))], url))

    # Auto-detect full-text markdown (any .md that isn't index.md)
    article_dir_path = root / "/".join(meta["_path"].split("/")[:-1])
    fulltext_md = next((f for f in article_dir_path.glob("*.md") if f.name != "index.md"), None)
    if fulltext_md:
        article_dir = "/".join(meta["_path"].split("/")[:-1])
        md_url = f"https://tylerburleigh.com/{article_dir}/{quote(fulltext_md.name)}"
        if link_nodes:
            link_nodes.append(u.text(" | "))
        link_nodes.append(u.link([u.text("Markdown")], md_url))

    if link_nodes:
        inner_children.append({"type": "paragraph", "children": link_nodes})

    if not inner_children:
        return []

    return [{
        "type": "div",
        "class": "article-info-block",
        "children": inner_children,
    }]


def run_directive(name, data):
    assert name == "articleinfo"
    slug = data.get("arg", "").strip()
    meta = article_meta.get(slug)
    if meta is None:
        return []
    return build_info_nodes(meta)


def declare_result(content):
    json.dump(content, sys.stdout, indent=2)
    raise SystemExit(0)


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
