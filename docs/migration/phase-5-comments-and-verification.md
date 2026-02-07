# Phase 5 — Giscus Comments + Verification

**Goal:** Restore Giscus commenting on blog posts and perform final verification that the site works correctly before merging.

**Depends on:** Phase 4 complete (all cleanup done, `myst build` succeeds)

---

## Steps

### 5.1 Add Giscus comment widget to blog posts

In Quarto, Giscus was configured globally via `blog/_metadata.yml`. In MyST, there is no built-in comment integration, so we add the Giscus `<script>` tag directly.

**Approach: Append raw HTML to each blog post**

Add the following block at the bottom of each `blog/*/index.md` file:

```html
<script src="https://giscus.app/client.js"
        data-repo="tylerburleigh/tylerburleigh.github.io"
        data-repo-id=""
        data-category="Blog comments"
        data-category-id="DIC_kwDOIg6EJc4CSz92"
        data-mapping="pathname"
        data-strict="0"
        data-reactions-enabled="1"
        data-emit-metadata="0"
        data-input-position="bottom"
        data-theme="light"
        data-lang="en"
        crossorigin="anonymous"
        async>
</script>
```

**Notes:**
- `data-repo-id` needs to be filled in (get from https://giscus.app/ configuration tool)
- `data-mapping="pathname"` preserves existing comment threads since URL paths are unchanged
- The theme is set to `light` to match the book-theme defaults
- This goes at the very end of each blog post `.md` file, after all content

**Alternative approach:** If adding to every file is too repetitive, consider creating a MyST transform plugin that injects the Giscus script into blog pages automatically. However, the manual approach is simpler and more transparent.

### 5.2 Verify URL path preservation

Check that all existing URLs still resolve:

**Blog posts:**
```
/blog/2019/09/27/    → blog/2019/09/27/index.md
/blog/2020/03/20/    → blog/2020/03/20/index.md
/blog/2020/03/21/    → blog/2020/03/21/index.md
/blog/2020/04/01/    → blog/2020/04/01/index.md
/blog/2020/04/04/    → blog/2020/04/04/index.md
/blog/2020/04/11/    → blog/2020/04/11/index.md
/blog/2020/05/12/    → blog/2020/05/12/index.md
/blog/2023/08/19/    → blog/2023/08/19/index.md
/blog/2023/08/25/    → blog/2023/08/25/index.md
/blog/2023/08/31/    → blog/2023/08/31/index.md
/blog/2023/09/08/    → blog/2023/09/08/index.md
/blog/2023/09/19/    → blog/2023/09/19/index.md
/blog/2023/10/08/    → blog/2023/10/08/index.md
/blog/2023/12/04/    → blog/2023/12/04/index.md
/blog/2023/12/09/    → blog/2023/12/09/index.md
/blog/2025/01/12/    → blog/2025/01/12/index.md
/blog/2025/01/24/    → blog/2025/01/24/index.md
/blog/2025/02/02/    → blog/2025/02/02/index.md
/blog/2025/03/02/    → blog/2025/03/02/index.md
/cv/                 → cv/index.md
/research/articles/* → research/articles/*/index.md
```

**Verification steps:**
1. Run `myst build --html`
2. Check `_build/html/` output directory for expected paths
3. Start local server: `myst start` or `python -m http.server -d _build/html`
4. Spot-check several URLs in browser

### 5.3 Verify blog listing and RSS

1. Open `/blog` — should show all posts as cards via `postlist` directive
2. Open `/` — should show latest 3 posts via `postlist` directive
3. Check `rss.xml` and `atom.xml` at project root — should contain all blog post entries
4. Validate RSS feed with an online validator (e.g., https://validator.w3.org/feed/)

### 5.4 Verify research listing

1. Open `/research` — should show all 14 articles with citations, categories, and links
2. Click "Full details" on a few articles — should navigate to the article page
3. Check that preprint PDF links work (local file references)

### 5.5 Verify static code output

For posts with executed code (`blog/2025/01/12/`, `blog/2025/03/02/`):
1. Verify that code blocks render with syntax highlighting
2. Verify that static output (charts, text) appears after code blocks
3. Verify that `<details>` code-fold blocks expand/collapse correctly

### 5.6 Verify CSS and fonts

1. Check that Jost font loads for headings
2. Check that Libre Franklin font loads for body text
3. Check that link colors are orange (`#FF9500`)
4. Check that the CV PDF embed works
5. Check that Font Awesome icons render (404 page, CV download button)

### 5.7 Verify Giscus comments

1. Open a blog post that has existing comments
2. Verify the Giscus widget loads
3. Verify existing comments appear (pathname mapping should match)
4. Test posting a new comment

### 5.8 Verify Google Analytics

1. Check page source for GA4 tag (`G-PRHQZ8HPLB`)
2. Verify in GA4 real-time dashboard that pageviews are tracked

### 5.9 Final build and preview

```bash
myst build --html
myst start
```

Walk through every page type:
- [ ] Homepage
- [ ] Blog listing
- [ ] Individual blog post (simple)
- [ ] Individual blog post (with code)
- [ ] Individual blog post (with executed code output)
- [ ] Research listing
- [ ] Individual research article
- [ ] CV page
- [ ] 404 page

### 5.10 Merge and deploy

Once verification is complete:

```bash
git add -A
git commit -m "Migrate site from Quarto to MyST"
git checkout main
git merge myst-migration
git push origin main
```

The GitHub Actions workflow (`.github/workflows/deploy.yml`) will automatically build and deploy the site.

**Post-deploy verification:**
1. Check https://tylerburleigh.com/ loads correctly
2. Check a few blog post URLs
3. Check RSS feed at https://tylerburleigh.com/rss.xml
4. Check Giscus comments on a blog post
5. Check Google Analytics real-time

---

## Rollback plan

If issues are found after deploying:

```bash
git revert HEAD
git push origin main
```

This reverts to the Quarto site. The old `gh-pages.yml` workflow would need to be restored if the revert doesn't include it.

---

## Acceptance criteria

- [ ] Giscus comments load on blog posts
- [ ] Existing comment threads are preserved (pathname mapping)
- [ ] All URL paths from the old site resolve correctly
- [ ] Blog listing shows all posts
- [ ] Research listing shows all 14 articles
- [ ] RSS feed is valid and contains all posts
- [ ] Static code output renders correctly
- [ ] Custom fonts and colors load
- [ ] Google Analytics is tracking
- [ ] Site builds and deploys successfully via GitHub Actions
- [ ] CNAME/custom domain works
