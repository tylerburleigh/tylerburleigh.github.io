# Phase 4 — Cleanup Quarto Artifacts

**Goal:** Remove all Quarto-specific files, directories, and configuration that are no longer needed after the MyST migration.

**Depends on:** Phase 3 complete (all content converted)

---

## Steps

### 4.1 Delete Quarto configuration files

| File/Directory | Reason |
|---------------|--------|
| `_quarto.yml` | Replaced by `myst.yml` |
| `_variables.yml` | Values hardcoded into content |
| `renv/` | R environment — no longer needed |
| `renv.lock` | R lockfile — no longer needed |
| `tylerburleigh-ath-quarto.Rproj` | RStudio project file |
| `tylerburleigh-ath-quarto.code-workspace` | VS Code workspace (Quarto-specific) |

### 4.2 Delete Quarto theme and template files

| File/Directory | Reason |
|---------------|--------|
| `html/ath.scss` | SCSS theme — replaced by `_static/custom.css` |
| `html/blog/listing.ejs` | EJS blog listing template — replaced by `postlist` plugin |
| `html/research/listing.ejs` | EJS research listing template — replaced by `researchlist` plugin |
| `html/research/title-block.html` | Research title block template |
| `html/` (entire directory) | Can be removed after confirming nothing else references it |
| `_extensions/` | Quarto extensions (code-collapse) — no longer needed |

### 4.3 Delete freeze cache

| File/Directory | Reason |
|---------------|--------|
| `_freeze/` (entire directory) | Quarto freeze cache — output already extracted in Phase 3 |

### 4.4 Delete old workflow

| File | Reason |
|------|--------|
| `gh-pages.yml` | Old Quarto publish workflow — replaced by `.github/workflows/deploy.yml` |

### 4.5 Delete converted `.qmd` source files

If not already done in Phase 3, ensure all `.qmd` files are removed:

```bash
# Verify no .qmd files remain
find . -name "*.qmd" -type f
```

Expected: empty output (all converted to `.md` in Phase 3).

### 4.6 Clean up remaining files

Review and decide on:

| File | Decision |
|------|----------|
| `stepwise_solver_results.ndjson` | Delete if not referenced by any blog post |
| `files/bib/references.bib` | Keep if any content uses citations; delete if not |
| `files/bib/chicago-author-date.csl` | Keep alongside references.bib or delete together |

### 4.7 Update `.gitignore`

Add MyST build artifacts:

```
# MyST build output
_build/

# Generated feeds
rss.xml
atom.xml

# Python
__pycache__/
*.pyc
```

### 4.8 Verify clean state

```bash
# Check that no Quarto artifacts remain
ls _quarto.yml 2>/dev/null && echo "FAIL: _quarto.yml still exists"
ls -d _extensions/ 2>/dev/null && echo "FAIL: _extensions/ still exists"
ls -d _freeze/ 2>/dev/null && echo "FAIL: _freeze/ still exists"
ls -d renv/ 2>/dev/null && echo "FAIL: renv/ still exists"
ls -d html/ 2>/dev/null && echo "FAIL: html/ still exists"
find . -name "*.qmd" -type f | head -5

# Verify MyST build still works
myst build --html
```

---

## Files deleted in this phase

| Path | Type |
|------|------|
| `_quarto.yml` | Config |
| `_variables.yml` | Config |
| `renv/` | Directory |
| `renv.lock` | Lockfile |
| `*.Rproj` | RStudio project |
| `*.code-workspace` | VS Code workspace |
| `html/` | Directory (theme + templates) |
| `_extensions/` | Directory (Quarto extensions) |
| `_freeze/` | Directory (freeze cache) |
| `gh-pages.yml` | Workflow |
| All `.qmd` files | Source files |

## Files modified in this phase

| Path | Change |
|------|--------|
| `.gitignore` | Add `_build/`, `rss.xml`, `atom.xml`, `__pycache__/` |

## Acceptance criteria

- [ ] No `.qmd` files remain in the repository
- [ ] No Quarto config files remain (`_quarto.yml`, `_variables.yml`)
- [ ] No R tooling files remain (`renv/`, `renv.lock`, `*.Rproj`)
- [ ] No Quarto theme/template files remain (`html/`, `_extensions/`)
- [ ] No freeze cache remains (`_freeze/`)
- [ ] `.gitignore` updated for MyST
- [ ] `myst build --html` succeeds
- [ ] Site renders correctly in local preview
