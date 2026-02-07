# Phase 3 — Convert Content (`.qmd` → `.md`)

**Goal:** Convert all Quarto Markdown files to standard MyST-compatible Markdown, handling frontmatter translation, Quarto-specific syntax removal, and static code output extraction.

**Depends on:** Phase 1 (scaffold) and Phase 2 (plugins) complete

---

## General conversion rules

Every `.qmd` → `.md` conversion follows these steps:

1. **Rename** `index.qmd` → `index.md`
2. **Clean frontmatter:** Remove Quarto-only keys (`freeze`, `title-block-banner`, `engine`, `page-layout`, `toc-location`, `toc-title`, `code-tools`, `comments`, `published-title`, `format`, `listing`)
3. **Keep frontmatter:** Preserve `title`, `date`, `description`, `categories`, `author`, `doi`, and any custom keys needed by plugins (`pub-info`)
4. **Replace Quarto syntax:**
   - ```` ```{python} ```` → ```` ```python ```` (plain fenced code, no execution)
   - ```` ```{r} ```` → ```` ```r ````
   - ```` ```{=html} ```` → raw HTML (remove the wrapper)
   - ```` ```{css echo=FALSE} ```` → `<style>` block or move to CSS
   - `::: {.grid}` / `::: {.g-col-*}` → MyST `::::{grid}` / `:::{grid-item}` or plain HTML
   - `:::{#listing_id}` listing references → `:::{postlist}` or `:::{researchlist}` directives
   - `{{< fa icon-name >}}` → `<i class="fa-solid fa-icon-name"></i>` (with Font Awesome CDN)
   - `{{< meta key >}}` → hardcoded values
   - `{{< var key >}}` → hardcoded values
5. **Code cell options:** Remove `#| eval: false`, `#| echo: true`, `#| code-fold: true`, `#| code-summary: "..."`, etc. For code-fold, wrap in `<details><summary>` HTML
6. **Extract static output:** For posts with `_freeze/` data, extract the rendered HTML/images and inline them

---

## Steps

### 3.1 Convert top-level pages

#### `index.qmd` → `index.md`

**Current structure:** Profile photo in a grid layout, "About me" text, latest blog posts listing.

**Conversion approach:**
- Replace Quarto grid syntax (`::: {.grid}`, `::: {.g-col-*}`) with MyST grid directives or a simpler layout
- Replace `{{< meta main-photo >}}` / `{{< meta main-photo-square >}}` with hardcoded image paths
- Replace `{{< meta author-meta >}}` with "Tyler Burleigh"
- Replace `:::{#posts_2025}` with `:::{postlist}` directive (`:number: 3`)
- Remove `title-block-banner`, `listing`, `format` from frontmatter
- Add `site: { hide_toc: true }` to frontmatter

**Target output:**
```markdown
---
title: "Hello there!"
site:
  hide_toc: true
---

:::{figure} /files/profiles/tyler-burleigh-2023.jpg
:alt: Tyler Burleigh
:align: center
:width: 190px
:::

## About me

Hi! I'm an AI Research Scientist with a multidisciplinary background...

## My latest blog posts

:::{postlist}
:number: 3
:::
```

#### `cv/index.qmd` → `cv/index.md`

**Current structure:** Uses R inline code (`` `r rmarkdown::metadata$cv$pdf` ``) to reference a PDF filename, embeds it in an iframe.

**Conversion approach:**
- Hardcode the PDF filename (`Tyler_Burleigh_Resume_2024_12.pdf`) instead of R inline code
- Keep the `<style>` block for embed-container (or rely on `_static/custom.css`)
- Keep the noindex meta tag script
- Replace Font Awesome icon `fa-solid fa-file-arrow-down` with `<i>` tag
- Remove `engine: knitr`, `title-block-banner`, `published-title`, `cv` from frontmatter

**Target output:**
```markdown
---
title: Curriculum vitae
date: 2024-12-31
---

<script>
  const newMeta = document.createElement("meta");
  newMeta.setAttribute("name", "robots");
  newMeta.setAttribute("content", "noindex,nofollow");
  document.head.appendChild(newMeta);
</script>

<p style="text-align:center;">
  <a href="Tyler_Burleigh_Resume_2024_12.pdf" target="_blank">
    <i class="fa-solid fa-file-arrow-down"></i> Download current CV
  </a>
</p>

<div class="embed-container">
  <iframe src="Tyler_Burleigh_Resume_2024_12.pdf" style="border: 0.5px"></iframe>
</div>
```

#### `404.qmd` → `404.md`

**Conversion approach:**
- Replace `{{< fa magnifying-glass >}}` with `<i class="fa-solid fa-magnifying-glass"></i>`
- Remove `title-block-banner` from frontmatter

### 3.2 Create new root listing pages

#### `blog.md` (new file at project root)

Replaces `blog/index.qmd`. Uses the `postlist` directive instead of Quarto listings.

```markdown
# Blog

Below are my blog posts. You can browse by year in the sidebar.

:::{postlist}
:number: 50
:::
```

#### `research.md` (new file at project root)

Replaces `research/index.qmd`. Uses the `researchlist` directive.

```markdown
# Research

My research is mainly related to cognitive and social psychology. Areas of research include: student perceptions of classroom grading practices, the "Uncanny Valley", zero-sum thinking, prejudice, social justice, competitiveness, and online research methods.

## Journal articles

:::{researchlist}
:::
```

### 3.3 Convert blog posts (20 files)

Each blog post conversion follows the general rules above. Posts are grouped by complexity:

#### Simple posts (no code execution, no special Quarto features)

These just need frontmatter cleanup and rename:

| Post | Special handling |
|------|-----------------|
| `blog/2019/09/27/index.qmd` | Straightforward |
| `blog/2020/03/20/index.qmd` | Check for `{{< fa >}}` shortcodes |
| `blog/2020/03/21/index.qmd` | Check for `{{< fa >}}` shortcodes |
| `blog/2020/04/01/index.qmd` | Check for `{{< fa >}}` shortcodes |
| `blog/2020/04/04/index.qmd` | Check for `{{< fa >}}` shortcodes |
| `blog/2020/04/11/index.qmd` | Check for `{{< fa >}}` shortcodes |
| `blog/2020/05/12/index.qmd` | Check for `{{< fa >}}` shortcodes |

#### Posts with code blocks but no execution

These have ` ```{python} ` or ` ```{r} ` blocks with `#| eval: false` — just need syntax conversion:

| Post | Special handling |
|------|-----------------|
| `blog/2023/08/19/index.qmd` | Convert code blocks |
| `blog/2023/08/25/index.qmd` | Convert code blocks |
| `blog/2023/08/31/index.qmd` | Convert code blocks |
| `blog/2023/09/08/index.qmd` | Convert code blocks |
| `blog/2023/09/19/index.qmd` | Convert code blocks |
| `blog/2023/10/08/index.qmd` | Convert code blocks |
| `blog/2023/12/04/index.qmd` | Convert code blocks |
| `blog/2023/12/09/index.qmd` | Convert code blocks |
| `blog/2025/01/24/index.qmd` | Convert code blocks |
| `blog/2025/02/02/index.qmd` | Convert code blocks |

#### Posts with executed code (freeze data exists)

These need static output extracted from `_freeze/`:

| Post | Freeze path | Output type |
|------|------------|-------------|
| `blog/2025/01/12/index.qmd` | `_freeze/blog/2025/01/12/index/execute-results/` | Check |
| `blog/2025/03/02/index.qmd` | `_freeze/blog/2025/03/02/index/execute-results/` | Plotly charts, print output |

**Process for extracting freeze data:**
1. Read `_freeze/blog/YYYY/MM/DD/index/execute-results/html.json`
2. This JSON contains pre-rendered output for each code cell
3. Extract the HTML output and inline it after the corresponding code block
4. For Plotly/interactive charts: extract as static `<div>` with the rendered HTML
5. For text output: wrap in ` ```text ` fenced blocks
6. For `code-fold` blocks: wrap code in `<details><summary>Click to view code</summary>...</details>`

### 3.4 Convert research articles (14 files)

All research articles follow an identical pattern. The conversion is mechanical:

**For each `research/articles/*/index.qmd`:**
1. Rename to `index.md`
2. Keep all frontmatter as-is (the `pub-info`, `categories`, `doi`, `author` fields are used by `researchlist.py`)
3. Replace `fa-solid fa-*` icon references in `pub-info.links` — these are read by the plugin, not rendered as shortcodes, so they can stay as metadata strings
4. No body content changes needed (just `## Abstract` and `## Highlights` sections)

### 3.5 Handle Font Awesome CDN

Add Font Awesome CDN to the site. Options:
- Add a `<link>` tag to `_static/custom.css` via `@import`
- Or add to `myst.yml` under a site options field if supported

```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
```

This is needed for all `<i class="fa-solid fa-*">` replacements to render.

### 3.6 Delete old `.qmd` files

After converting each file, delete the original `.qmd` version. Also delete:
- `blog/index.qmd` (replaced by root `blog.md`)
- `blog/_footer.qmd` (R session info — no longer needed)
- `research/index.qmd` (replaced by root `research.md`)

---

## URL path preservation

The directory structure `blog/YYYY/MM/DD/index.md` naturally produces URLs at `/blog/YYYY/MM/DD/` — matching the existing Quarto output. No redirects needed.

Similarly, `research/articles/slug/index.md` produces `/research/articles/slug/`.

---

## Files modified in this phase

| File | Action |
|------|--------|
| `index.md` | New (converted from `index.qmd`) |
| `blog.md` | New (replaces `blog/index.qmd`) |
| `research.md` | New (replaces `research/index.qmd`) |
| `cv/index.md` | New (converted from `cv/index.qmd`) |
| `404.md` | New (converted from `404.qmd`) |
| 20× `blog/*/index.md` | New (converted from `.qmd`) |
| 14× `research/articles/*/index.md` | New (converted from `.qmd`) |
| All original `.qmd` files | Deleted |

## Acceptance criteria

- [ ] All `.qmd` files converted to `.md`
- [ ] No Quarto-specific syntax remains (`{{< >}}`, `::: {.class}`, ```` ```{lang} ````)
- [ ] Frontmatter contains only MyST-compatible keys
- [ ] Posts with freeze data have static output inlined
- [ ] `code-fold` blocks converted to `<details>` HTML
- [ ] Font Awesome CDN is loaded
- [ ] `myst build --html` succeeds with all content
- [ ] URL paths match existing site structure
