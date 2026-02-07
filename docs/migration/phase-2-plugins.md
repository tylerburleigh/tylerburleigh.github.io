# Phase 2 — Build Plugins (`src/`)

**Goal:** Implement the two MyST executable plugins that generate dynamic content: the blog post listing (with RSS) and the research article listing.

**Depends on:** Phase 1 complete (myst.yml registers the plugins)

---

## Background

MyST supports [executable plugins](https://mystmd.org/guide/plugins) — Python scripts that:
1. Declare custom directives/roles when invoked with no arguments
2. Execute directive logic when invoked with `--directive <name>` and receive JSON on stdin
3. Return MyST AST nodes (JSON) on stdout

The reference implementation is Chris Holdgraf's `src/blogpost.py`.

---

## Steps

### 2.1 Create `src/unist.py`

Copy from `/tmp/choldgraf-site/src/unist.py` — provides helper functions for building AST nodes:

- `text(value)` — text node
- `strong(children)` — bold wrapper
- `link(children, url)` — hyperlink
- `table()`, `table_row()`, `table_cell()` — table builders
- `list_()`, `list_item()` — list builders
- `div()`, `span()`, `image()`, `grid()` — layout helpers

No modifications needed.

### 2.2 Implement `src/blogpost.py`

Adapted from Chris Holdgraf's version, customized for Tyler's site.

**What it does at import time (top-level execution):**
1. Scans `blog/**/*.md` for all blog posts
2. Parses YAML frontmatter from each (title, date, description, categories, author)
3. Builds a sorted DataFrame of posts
4. Generates `rss.xml` and `atom.xml` feeds at project root
5. Pre-builds a list of card AST nodes for the directive

**Directive: `postlist`**

Options:
- `number` (int, default 10) — how many posts to show

Output: A list of `card` nodes, each containing:
- `cardTitle` — post title
- `paragraph` — description or first 50 words
- `footer` — "Date: Month DD, YYYY | Author: Tyler Burleigh"

**Key differences from reference:**
- Author default: `"Tyler Burleigh"` (not Chris Holdgraf)
- Feed URLs: `https://tylerburleigh.com/...`
- Feed metadata: Tyler's name, email, site title
- Site URL: `https://tylerburleigh.com`
- Profile image URL for feed logo: `https://tylerburleigh.com/files/profiles/tyler-burleigh-2023.jpg`

**Template structure:**

```python
#!/usr/bin/env python3
import argparse
import json
import sys
from yaml import safe_load
from pathlib import Path
import pandas as pd
from feedgen.feed import FeedGenerator
import unist as u

DEFAULTS = {"number": 10}
root = Path(__file__).parent.parent

# 1. Scan and parse all blog posts
posts = []
for ifile in root.rglob("blog/**/*.md"):
    if "drafts" in str(ifile):
        continue
    text = ifile.read_text()
    try:
        _, meta, content = text.split("---", 2)
    except Exception:
        print(f"Skipping file with error: {ifile}", file=sys.stderr)
        continue
    meta = safe_load(meta)
    meta["path"] = ifile.relative_to(root).with_suffix("")
    # ... extract title, content summary, author ...
    posts.append(meta)

posts = pd.DataFrame(posts)
posts["date"] = pd.to_datetime(posts["date"]).dt.tz_localize("US/Eastern")
posts = posts.dropna(subset=["date"]).sort_values("date", ascending=False)

# 2. Generate RSS/Atom feeds
fg = FeedGenerator()
fg.id("https://tylerburleigh.com")
fg.title("Tyler Burleigh's blog")
fg.author({"name": "Tyler Burleigh", "email": "tylerburleigh@gmail.com"})
fg.link(href="https://tylerburleigh.com", rel="alternate")
fg.logo("https://tylerburleigh.com/files/profiles/tyler-burleigh-2023.jpg")
fg.subtitle("Tyler Burleigh's personal blog")
fg.link(href="https://tylerburleigh.com/rss.xml", rel="self")
fg.language("en")
# ... add entries from posts DataFrame ...
fg.atom_file(root / "atom.xml", pretty=True)
fg.rss_file(root / "rss.xml", pretty=True)

# 3. Plugin declaration + directive handler
plugin = {
    "name": "Blog Post list",
    "directives": [{
        "name": "postlist",
        "doc": "Display a list of blog posts as cards",
        "alias": ["bloglist"],
        "arg": {},
        "options": {
            "number": {"type": "int", "doc": "Number of posts to include"}
        },
    }],
}

# 4. Build card nodes
children = []
for ix, irow in posts.iterrows():
    children.append({
        "type": "card",
        "url": f"/{irow['path']}",
        "children": [
            {"type": "cardTitle", "children": [u.text(irow["title"])]},
            {"type": "paragraph", "children": [u.text(irow["content"])]},
            {"type": "footer", "children": [
                u.strong([u.text("Date: ")]),
                u.text(f"{irow['date']:%B %d, %Y} | "),
                u.strong([u.text("Author: ")]),
                u.text(f"{irow['author']}"),
            ]},
        ]
    })

# 5. CLI entrypoint
def declare_result(content):
    json.dump(content, sys.stdout, indent=2)
    raise SystemExit(0)

def run_directive(name, data):
    assert name == "postlist"
    opts = data["node"].get("options", {})
    number = int(opts.get("number", DEFAULTS["number"]))
    return children[:number]

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
    else:
        declare_result(plugin)
```

### 2.3 Implement `src/researchlist.py`

A new plugin (no reference equivalent) that renders the research article listing.

**What it does:**
1. Scans `research/articles/*/index.md` for all research articles
2. Parses YAML frontmatter: `title`, `date`, `author`, `categories`, `pub-info.reference`, `pub-info.links`, `doi`
3. Builds a sorted list (by date, descending)

**Directive: `researchlist`**

Output: A list of card/div nodes, each containing:
- The full citation text (`pub-info.reference` — already contains HTML `<a>` tags for DOIs)
- Category tags
- Links: "Full details" (to the article page), plus any `pub-info.links` entries (Preprint PDF, Final version, etc.)

**Template structure:**

```python
#!/usr/bin/env python3
import argparse
import json
import sys
from yaml import safe_load
from pathlib import Path
import unist as u

root = Path(__file__).parent.parent

# 1. Scan research articles
articles = []
for ifile in sorted(root.glob("research/articles/*/index.md")):
    text = ifile.read_text()
    try:
        _, meta, content = text.split("---", 2)
    except Exception:
        continue
    meta = safe_load(meta)
    meta["path"] = str(ifile.relative_to(root).with_suffix(""))
    articles.append(meta)

# Sort by date descending
articles.sort(key=lambda x: x.get("date", ""), reverse=True)

# 2. Plugin declaration
plugin = {
    "name": "Research article list",
    "directives": [{
        "name": "researchlist",
        "doc": "Display a list of research articles",
        "arg": {},
        "options": {},
    }],
}

# 3. Build AST nodes for each article
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
    for lnk in links:
        url = lnk["url"]
        if lnk.get("local"):
            # Build path relative to article directory
            article_dir = "/".join(article["path"].split("/")[:-1])
            url = f"/{article_dir}/{url}"
        link_nodes.append(
            u.list_item([
                {"type": "paragraph", "children": [
                    u.link([u.text(lnk["name"])], url)
                ]}
            ])
        )

    # Build category tags
    cat_text = ", ".join(article.get("categories", []))

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

# 4. CLI entrypoint
def declare_result(content):
    json.dump(content, sys.stdout, indent=2)
    raise SystemExit(0)

def run_directive(name, data):
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
    else:
        declare_result(plugin)
```

### 2.4 Test plugins locally

```bash
# Test plugin declaration (should output JSON schema)
python src/blogpost.py
python src/researchlist.py

# Test with MyST build (after some content exists)
myst build --html
```

---

## Files created/modified in this phase

| File | Status |
|------|--------|
| `src/unist.py` | New (copied from reference) |
| `src/blogpost.py` | New (adapted from reference) |
| `src/researchlist.py` | New (custom) |

## Acceptance criteria

- [ ] `python src/blogpost.py` outputs valid plugin JSON declaration
- [ ] `python src/researchlist.py` outputs valid plugin JSON declaration
- [ ] RSS/Atom feeds are generated at project root when blogpost.py runs
- [ ] Both plugins handle missing/malformed frontmatter gracefully (skip with warning)
