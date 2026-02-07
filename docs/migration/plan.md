# Migrate tylerburleigh.com from Quarto to MyST

## Context

The site at tylerburleigh.com is currently built with Quarto (`.qmd` files, knitr, custom SCSS theme, EJS listing templates). The goal is to migrate to MyST (Markedly Structured Text) following Chris Holdgraf's approach — a `myst.yml` config, `book-theme`, Python executable plugins for blog listing + RSS, and a simple GitHub Actions deployment pipeline. This simplifies the toolchain, drops the R/SCSS dependencies, and aligns with the MyST/Jupyter ecosystem.

**Decisions:**
- Preserve current URL paths (`/blog/YYYY/MM/DD/`) for SEO
- Minimal custom CSS (accept book-theme defaults, port fonts + brand colors only)
- All code output is static (extracted from existing `_freeze/` cache)
- Keep the Research section (14 articles, custom plugin)

**Reference:** Chris Holdgraf's site cloned at `/tmp/choldgraf-site`

---

## Progress

**Last updated:** 2026-02-07

| Phase | Status | Notes |
|-------|--------|-------|
| 0 | DONE | Branch `myst-migration` created, inventory documented |
| 1 | DONE | All scaffold files created |
| 2 | DONE | Both plugins implemented (blogpost.py, researchlist.py) |
| 3 | DONE | All .md files created, .qmd originals deleted |
| 4 | DONE | Quarto artifacts deleted, .gitignore updated |
| 5 | MOSTLY DONE | Giscus added to all blog posts; build succeeds; manual verification remaining |

### What was completed in Phases 3-5:
- All 19 blog posts converted from .qmd → .md (including freeze data extraction)
- All 14 research articles converted from .qmd → .md
- Top-level pages created: index.md, blog.md, research.md, cv/index.md, 404.md
- Code-fold blocks converted to `<details><summary>` HTML
- Quarto shortcodes replaced with HTML equivalents
- Freeze data (text outputs, Plotly charts, HTML tables) extracted and inlined
- All 39 .qmd files deleted
- All Quarto artifacts removed (_quarto.yml, _variables.yml, renv/, _freeze/, _extensions/, html/, etc.)
- .gitignore updated for MyST (_build/, rss.xml, atom.xml, __pycache__/)
- Plugins made executable (chmod +x)
- Fixed myst.yml nav URL (/ → /index)
- Installed feedgen dependency
- Giscus comment widget added to all 19 blog posts (repo-id: R_kgDOKMo8ww)
- `myst build --html` succeeds with 38 pages, zero errors

### Remaining (manual verification):
1. `myst start` — visually verify homepage, blog listing, individual posts, research listing, CV, 404
2. Verify Giscus comments load and existing threads preserved
3. Verify Font Awesome icons render (404 page, CV)
4. Verify custom fonts (Jost headings, Libre Franklin body) and orange link color
5. Verify RSS feed at rss.xml
6. Verify Google Analytics tag present
7. Merge to main and deploy

---

## Phase Index

| Phase | Description | Detail file |
|-------|-------------|-------------|
| 0 | Preparation (branch, inventory) | [phase-0-preparation.md](./phase-0-preparation.md) |
| 1 | Scaffold MyST project | [phase-1-scaffold.md](./phase-1-scaffold.md) |
| 2 | Build plugins (`src/`) | [phase-2-plugins.md](./phase-2-plugins.md) |
| 3 | Convert content (`.qmd` → `.md`) | [phase-3-content.md](./phase-3-content.md) |
| 4 | Cleanup Quarto artifacts | [phase-4-cleanup.md](./phase-4-cleanup.md) |
| 5 | Giscus comments + verification | [phase-5-comments-and-verification.md](./phase-5-comments-and-verification.md) |

---

## Files to create

| File | Purpose |
|------|---------|
| `myst.yml` | Central MyST config |
| `requirements.txt` | Python deps (mystmd, feedgen, pyyaml, pandas) |
| `src/blogpost.py` | Blog listing + RSS plugin |
| `src/researchlist.py` | Research listing plugin |
| `_static/custom.css` | Fonts + brand color overrides |
| `.github/workflows/deploy.yml` | GitHub Actions deployment |
| `index.md` | Homepage (converted from index.qmd) |
| `blog.md` | Blog listing page (new, at root) |
| `research.md` | Research listing page (new, at root) |
| `cv/index.md` | CV page (converted from cv/index.qmd) |
| `404.md` | Error page (converted from 404.qmd) |

Plus 20 blog `.qmd` → `.md` conversions and 14 research `.qmd` → `.md` conversions.

## Features that will be lost

| Feature | Workaround |
|---------|------------|
| Code folding | `<details><summary>` HTML |
| Title block color banners | None (accept book-theme header) |
| Margin notes/figures | Figures in main column only |
| Footnote hover | Standard footnotes |
| `{{< fa >}}` shortcodes | Inline `<i>` tags + FA CDN |
| SCSS theming | Plain CSS overrides |
| R/Python execution at build | Pre-rendered static output |
