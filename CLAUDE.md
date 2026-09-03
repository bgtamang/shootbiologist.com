# shootbiologist.com — Personal Academic Portfolio

## Site Info
- **URL**: www.shootbiologist.com
- **Hosting**: GitHub Pages (repo: bgtamang/shootbiologist.com)
- **Structure**: Single-page static site (`index.html` + `images/` + CV PDF), plus `404.html`, `robots.txt`, `sitemap.xml`

## Deployment Workflow
When the user asks to make changes to the website:
1. Edit the relevant files (usually `index.html`)
2. Stage the changed files with `git add`
3. Commit with a short descriptive message
4. Push to origin (`git push origin master`)
5. Confirm the push succeeded — site updates in ~30 seconds

## Important Notes
- The live file is `index.html` — all content is in this single file (HTML + inline CSS + JS)
- Images go in `images/` organized by subfolder: `news/`, `research/`, `gallery/field/`, `gallery/lab/`, `gallery/phenotyping/`, `gallery/team/`
- CV PDF is `CV_Bishal_Tamang.pdf` in the root
- Old version files (`index-V*.html`, `index-test.html`) are in `.gitignore` — do not track them
- CNAME file must stay in root (maps custom domain to GitHub Pages)
- Always commit and push after making changes — the user expects deploy on every edit session

## After adding an image
1. Reference it from `index.html` as usual
2. Run `python optimize_images.py` — it reads `index.html`, caps every referenced
   raster at 1400px on the longest edge, re-encodes it, and writes a `.webp` sibling.
   It only touches files the page actually references, and is safe to re-run.
3. Wrap the `<img>` in a `<picture>` with the WebP source:
   ```html
   <picture>
       <source srcset="images/.../name.webp" type="image/webp">
       <img src="images/.../name.jpg" alt="..." loading="lazy">
   </picture>
   ```
   Exception: `<video poster="...">` cannot use `<picture>`, so poster frames are
   listed in the script's `NO_WEBP_FILES` and get no `.webp`.
4. Keep `images/` free of files the page does not reference — they bloat every clone.

## Other maintenance scripts
- `make_og_card.py` regenerates `og-card.jpg` (the 1200x630 link-preview image)
  from the canopy figure. Re-run if that figure is replaced.

## Gallery videos
Video tiles carry the file in `data-src`, not `src`, so the MP4 is only fetched
when the visitor opens the lightbox. Do not add `autoplay` — the two clips are
~24 MB combined.
