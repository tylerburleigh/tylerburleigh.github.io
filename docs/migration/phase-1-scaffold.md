# Phase 1 — Scaffold MyST Project

**Goal:** Create the core MyST configuration, dependencies, CSS overrides, and GitHub Actions workflow so the project can build (even with no content yet).

**Depends on:** Phase 0 complete

---

## Steps

### 1.1 Create `myst.yml`

The central MyST configuration file at project root. Modeled after Chris Holdgraf's site.

**Key structure:**

```yaml
version: 1
project:
  id: <generate-uuid>
  title: "Tyler Burleigh"
  authors:
    - name: Tyler Burleigh
      website: https://tylerburleigh.com
      github: tylerburleigh
  github: https://github.com/tylerburleigh/tylerburleigh.github.io
  thumbnail: files/profiles/tyler-burleigh-2023.jpg
  plugins:
    - type: executable
      path: src/blogpost.py
    - type: executable
      path: src/researchlist.py
  toc:
    - file: index.md
    - file: blog.md
      children:
        - title: "2025"
          children:
            - pattern: "blog/2025/**/*.md"
        - title: "2023"
          children:
            - pattern: "blog/2023/**/*.md"
        - title: "2020"
          children:
            - pattern: "blog/2020/**/*.md"
        - title: "2019"
          children:
            - pattern: "blog/2019/**/*.md"
    - file: research.md
      children:
        - pattern: "research/articles/**/*.md"
    - file: cv/index.md
    - file: 404.md

site:
  template: book-theme
  options:
    folders: true
    logo_text: Tyler Burleigh
    analytics_google: G-PRHQZ8HPLB
    favicon: files/favico.png
  domains:
    - tylerburleigh.github.io
  actions:
    - title: RSS
      url: https://tylerburleigh.com/rss.xml
  nav:
    - title: About
      url: /
    - title: CV
      url: /cv
    - title: Blog
      url: /blog
    - title: Research
      url: /research
```

**Notes:**
- `toc` patterns must match the converted `.md` file paths
- `site.domains` is used by MyST for canonical URLs
- `analytics_google` carries over the existing GA4 measurement ID
- Plugins are registered here and implemented in Phase 2

### 1.2 Create `requirements.txt`

```
mystmd
feedgen
pyyaml
pandas
```

This is the minimal set needed for the MyST build and the custom plugins.

### 1.3 Create `_static/custom.css`

Port only the essential brand elements from `html/ath.scss`:

```css
/* Google Fonts — Jost (headings/nav) + Libre Franklin (body) */
@import url('https://fonts.googleapis.com/css2?family=Jost:ital,wght@0,100..900;1,100..900&family=Libre+Franklin:ital,wght@0,100..900;1,100..900&display=swap');

/* Font overrides */
body {
  font-family: 'Libre Franklin', sans-serif;
  -webkit-font-smoothing: antialiased;
}

h1, h2, h3, h4, h5, h6 {
  font-family: 'Jost', sans-serif;
  font-weight: 600;
}

/* Brand color overrides */
a {
  color: #FF9500;           /* $orange — link color */
  text-decoration: none;
}
a:hover {
  color: #8950F7;           /* $red (purple) — link hover */
  text-decoration: underline;
}

/* Profile image (homepage) */
div.profile-pic img {
  border-radius: 500px;
  width: 80%;
  max-width: 190px;
  margin: 0 auto;
  display: block;
}

/* Giscus comment reactions spacing */
.gsc-reactions {
  margin-top: 1em;
}

/* CV embed */
.embed-container {
  position: relative;
  padding-bottom: 129%;
  height: 0;
  overflow: hidden;
  max-width: 100%;
}
.embed-container iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

/* Font Awesome CDN (for icons replacing {{< fa >}} shortcodes) */
/* Loaded via HTML head in myst.yml or in the CSS */
```

**Notes:**
- We accept the book-theme defaults for navbar/footer colors rather than trying to match the purple/dark scheme exactly
- Font Awesome CDN link will be added as a `<link>` tag in the site head (via `myst.yml` `site.options` or a raw HTML block)

### 1.4 Create `.github/workflows/deploy.yml`

Replace the Quarto-based `gh-pages.yml` with a MyST workflow:

```yaml
name: MyST Deploy

on:
  workflow_dispatch:
  push:
    branches: main

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Build MyST site
        run: myst build --html

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: ./_build/html

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

**Notes:**
- This uses the modern GitHub Pages deployment with `actions/deploy-pages` instead of pushing to a `gh-pages` branch
- The `CNAME` file at project root is automatically included in the build output
- `concurrency` prevents overlapping deployments

### 1.5 Create placeholder `src/` directory

Create empty placeholder files so the project structure is in place before Phase 2:

```
src/
  blogpost.py    # placeholder — implemented in Phase 2
  researchlist.py # placeholder — implemented in Phase 2
  unist.py        # utility module — copy from choldgraf-site
```

Copy `unist.py` from the reference site (`/tmp/choldgraf-site/src/unist.py`) as-is — it provides helper functions for building MyST AST nodes.

### 1.6 Verify build scaffolding

At this point, run:

```bash
pip install -r requirements.txt
myst build --html
```

This should produce a build (possibly with warnings about missing content files) but should not error on the config itself.

---

## Files created in this phase

| File | Status |
|------|--------|
| `myst.yml` | New |
| `requirements.txt` | New |
| `_static/custom.css` | New |
| `.github/workflows/deploy.yml` | New |
| `src/unist.py` | New (copied from reference) |
| `src/blogpost.py` | Placeholder |
| `src/researchlist.py` | Placeholder |

## Acceptance criteria

- [ ] `myst.yml` parses without errors
- [ ] `requirements.txt` installs cleanly
- [ ] `_static/custom.css` exists with font + color overrides
- [ ] `.github/workflows/deploy.yml` is valid YAML
- [ ] `myst build --html` runs without config errors (content warnings OK)
