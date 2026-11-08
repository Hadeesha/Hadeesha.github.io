# Lab website draft

Unpublished first draft of a research-group website for Hadeesha Piyadasa, PhD. The lab name is not chosen. The site uses the placeholder **Lab name forthcoming** until that choice is made.

The pages are static HTML and CSS, with one small script that inserts the shared name and the contact lines. There is no build step, no account system, and no analytics.

This draft has not been deployed, and no domain has been registered for it.

## Preview locally

From the project folder (the folder that contains `index.html`):

```bash
python3 -m http.server 8741 --bind 127.0.0.1
```

Or run `scripts/preview.sh`.

Open [http://127.0.0.1:8741/](http://127.0.0.1:8741/).

Serve the folder as the site root. These are the pages:

| Page | Address | Role |
| --- | --- | --- |
| Home | `/` | Wide banner, a short research introduction, and a link to the research page |
| Research | `/research/` | Lung development, pediatric tumour biology, spatial multi-omics, and a survivor direction that is still in development |
| People | `/people/` | Biography of the principal investigator only |
| Publications | `/publications/` | Selected publications coming soon, plus the ORCID record |
| Join | `/join/` | Trainee interest, with unconfirmed contact lines |
| Members | `/members/` | Reserved placeholder, linked only from the footer |

## Change the lab name in one place

Edit `js/site-config.js` and change the `labName` value:

```js
labName: "Lab name forthcoming",
```

Save the file and reload the browser. The header, the footer, and the browser title all read that value. The HTML files do not contain the name. Leave them that way, so the next rename stays a one-line edit.

Use a distinctive name. A very short name that already appears in the page text (for example a single word such as "Ottawa") would be a poor choice, because the check below expects the configured name to live only in `js/site-config.js`.

Do not title the group "Piyadasa Lab" in this draft. A name has not been chosen.

## Contact details

The join page lists the CHEO and University of Ottawa email addresses, the ORCID record, and the institutional profiles. A phone number and an office are not listed, because they have not been confirmed.

## Edit the prose

Page text lives in the HTML files:

- `index.html` — home
- `research/index.html`
- `people/index.html`
- `publications/index.html`
- `join/index.html`
- `members/index.html`

The header and footer are repeated on each page. If you add a public page, add it to both navigations on every page. Keep **Members (planned)** in the footer only.

Colours and type are in `css/styles.css`, under `:root` and the `@font-face` rules. The site uses Inter, self-hosted in `fonts/` under the SIL Open Font License (`fonts/OFL-Inter.txt`).

The homepage picture is `images/glioma-multiplex.jpg`, with the full-resolution file `images/glioma-multiplex-full.jpg`. Its caption is “Multiplex imaging of human glioma tissue.” The image stays square and is not cropped. The research page uses `images/research-program.png` (original file `documents/research-program.pdf`), `images/glioma-imaging-panels.png`, and `images/glioma-segmentation.png`. Replace a file to change that picture, and keep each caption accurate. Day-to-day editing steps are in `EDITING.md`.

Earlier homepages are kept for reference, not as live pages: `archive/split-editorial/` (git commit `91ecc24`) and `archive/image-first-banner/` (git commit `b997380`).

## What this draft leaves unfinished

- The lab name.
- A phone number and an office. They are omitted until they are confirmed.
- Trainees and staff. The people page names Hadeesha Piyadasa only. Add a person when they have joined, with their consent and the correct details.
- The members area. `/members` is reserved and does not work. It has no sign-in and does not collect a password.

Verified facts already written into the pages:

- Hadeesha Piyadasa, PhD
- Scientist, CHEO Research Institute
- Assistant Professor, Biochemistry, Microbiology and Immunology, Faculty of Medicine, University of Ottawa, from October 2026
- BSc Honours Biochemistry and PhD Immunology, University of Manitoba
- Postdoctoral training in spatial biology at Stanford, completed August 2026
- ORCID `0000-0002-0276-6590`

The research text stays with lung development and pediatric tumour biology (pediatric glioma and medulloblastoma), using spatial proteomics, glycomics, and transcriptomics. Blood-brain barrier function, metabolism, N-glycosylation, and immune and stromal organisation are stated as questions, not as results. Survivor cognitive and cardiac effects, with the Brain-Heart Interconnectome, are described as a direction in development.

Leave these out of the public pages: artificial intelligence and machine learning, allergy, Leiden, a Canada Research Chair, and the names of Stanford principal investigators. Stanford may stay only as the place of the completed postdoctoral training.

## Check the draft

```bash
python3 scripts/check_site.py
```

The script checks internal links and anchors, one `h1` per page, heading order, the skip link, `lang`, the viewport, the draft `noindex` tag, contrast of the colour tokens, the ORCID link, the members link (footer only), and that the HTML does not hardcode the lab name. It also requests the ORCID page and expects a successful response.

## When you publish later

Do not publish this draft as the public site while the name and contact lines are still placeholders.

When you choose to publish:

1. Set the lab name and replace the contact placeholders in `js/site-config.js`.
2. Add publications only after each citation is checked.
3. Remove `<meta name="robots" content="noindex, nofollow">` from each page.
4. Replace `robots.txt`. It currently disallows all crawlers.
5. Upload this folder to a static host and serve it as the site root. Any host that can serve HTML files is enough. There is no database and no server-side code.
6. Leave `/members` as a placeholder, or remove the footer link, until a real private area exists. Do not add a password form to these files. A static page cannot safely collect passwords. Use an institutional sign-in service if a members area is needed later.
7. Keep the source repository private until you decide to share the code.

No domain was purchased for this draft. No hosting was turned on. No login was built.
