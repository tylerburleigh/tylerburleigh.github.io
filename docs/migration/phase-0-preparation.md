# Phase 0 — Preparation

**Goal:** Set up a working branch, take inventory of all content that needs converting, and document the current state of the Quarto site.

---

## Steps

### 0.1 Create migration branch

```bash
git checkout -b myst-migration
```

All work happens on this branch. The `main` branch stays deployable throughout.

### 0.2 Content inventory

Catalog every `.qmd` file that needs converting:

**Blog posts (20 files):**

| Path | Has code output? | Notes |
|------|-----------------|-------|
| `blog/2019/09/27/index.qmd` | No | |
| `blog/2020/03/20/index.qmd` | No | |
| `blog/2020/03/21/index.qmd` | No | |
| `blog/2020/04/01/index.qmd` | No | |
| `blog/2020/04/04/index.qmd` | No | |
| `blog/2020/04/11/index.qmd` | No | |
| `blog/2020/05/12/index.qmd` | No | |
| `blog/2023/08/19/index.qmd` | Check freeze | |
| `blog/2023/08/25/index.qmd` | Check freeze | |
| `blog/2023/08/31/index.qmd` | Check freeze | |
| `blog/2023/09/08/index.qmd` | Check freeze | |
| `blog/2023/09/19/index.qmd` | Check freeze | |
| `blog/2023/10/08/index.qmd` | Check freeze | |
| `blog/2023/12/04/index.qmd` | Check freeze | |
| `blog/2023/12/09/index.qmd` | Check freeze | |
| `blog/2025/01/12/index.qmd` | Yes (freeze exists) | |
| `blog/2025/01/24/index.qmd` | Check freeze | |
| `blog/2025/02/02/index.qmd` | Check freeze | |
| `blog/2025/03/02/index.qmd` | Yes (freeze exists) | Has Plotly output, NDJSON data |

**Listing/index pages (3 files):**

| Path | Notes |
|------|-------|
| `blog/index.qmd` | Blog listing page — replaced by root `blog.md` + plugin |
| `blog/_footer.qmd` | R session info partial — drop entirely |
| `research/index.qmd` | Research listing page — replaced by root `research.md` + plugin |

**Top-level pages (3 files):**

| Path | Notes |
|------|-------|
| `index.qmd` | Homepage — grid layout, profile photo, latest posts |
| `cv/index.qmd` | CV page — PDF embed, uses R inline code for PDF URL |
| `404.qmd` | Error page — uses `{{< fa >}}` shortcode |

**Research articles (14 files):**

All follow the same pattern: YAML frontmatter with `pub-info.reference`, `pub-info.links`, `categories`, `doi`, and an `## Abstract` section.

| Path |
|------|
| `research/articles/burleigh-et-al-2013/index.qmd` |
| `research/articles/burleigh-et-al-2017/index.qmd` |
| `research/articles/burleigh-et-al-2018/index.qmd` |
| `research/articles/burleigh-meegan-2013/index.qmd` |
| `research/articles/burleigh-meegan-2017/index.qmd` |
| `research/articles/burleigh-schoenherr-2015/index.qmd` |
| `research/articles/ferrey-et-al-2015/index.qmd` |
| `research/articles/kennedy-et-al-2020/index.qmd` |
| `research/articles/rubel-burleigh-2018/index.qmd` |
| `research/articles/schoenherr-burleigh-2015/index.qmd` |
| `research/articles/schoenherr-burleigh-2020/index.qmd` |
| `research/articles/sparks-et-al-2016/index.qmd` |
| `research/articles/winter-et-al-2019/index.qmd` |
| `research/articles/wood-et-al-2018/index.qmd` |

### 0.3 Identify static assets to preserve

These directories/files stay as-is and get referenced from the new MyST config:

| Asset | Purpose |
|-------|---------|
| `files/` | Favicons, DOI SVG, profile photos, bib files |
| `files/bib/references.bib` | Bibliography (if any posts cite it) |
| `files/profiles/` | Profile images |
| `CNAME` | Custom domain config for GitHub Pages |
| Blog post local assets | Images, data files within each `blog/YYYY/MM/DD/` directory |
| Research article PDFs | Local PDFs in each `research/articles/*/` directory |

### 0.4 Document Giscus config

Current Giscus settings (from `blog/_metadata.yml`):
- **repo:** `tylerburleigh/tylerburleigh.github.io`
- **category:** `Blog comments`
- **category-id:** `DIC_kwDOIg6EJc4CSz92`
- **mapping:** `pathname`

These will be reused in Phase 5 via a raw HTML snippet appended to blog posts.

### 0.5 Document key theme values to port

From `html/ath.scss`:
- **Fonts:** `Libre Franklin` (body), `Jost` (headings/nav/toc/footer)
- **Google Fonts URL:** `https://fonts.googleapis.com/css2?family=Jost:ital,wght@0,100..900;1,100..900&family=Libre+Franklin:ital,wght@0,100..900;1,100..900&display=swap`
- **Brand colors:** `$orange: #FF9500` (links), `$purple: #5A4E7C` (navbar bg), `$pink: #A52C60` (primary), `$gray-900: #490A3D` (body text, footer bg)
- **Navbar:** purple bg (`#5A4E7C`), white text
- **Footer:** dark bg (`#490A3D`), gray text

---

## Acceptance criteria

- [ ] `myst-migration` branch exists
- [ ] Content inventory is verified (file counts match)
- [ ] Static asset paths are documented
- [ ] Giscus config is recorded
- [ ] Theme values to port are documented
