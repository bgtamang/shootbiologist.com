# shootbiologist.com — Personal Academic Portfolio

## Site Info
- **URL**: www.shootbiologist.com
- **Hosting**: GitHub Pages (repo: bgtamang/shootbiologist.com)
- **Structure**: Single-page static site (`index.html` + `images/` + CV PDF)

## Deployment Workflow
When the user asks to make changes to the website:
1. Edit the relevant files (usually `index.html`)
2. Stage the changed files with `git add`
3. Commit with a short descriptive message
4. Push to origin (`git push origin master`)
5. Confirm the push succeeded — site updates in ~30 seconds

## Important Notes
- The live file is `index.html` — all content is in this single file (HTML + inline CSS + JS)
- Images go in `images/` organized by subfolder: `news/`, `gallery/field/`, `gallery/lab/`, `gallery/phenotyping/`, `gallery/team/`, `blog/`
- CV PDF is `CV_Bishal_Tamang.pdf` in the root
- Old version files (`index-V*.html`) are in `.gitignore` — do not track them
- CNAME file must stay in root (maps custom domain to GitHub Pages)
- Always commit and push after making changes — the user expects deploy on every edit session
