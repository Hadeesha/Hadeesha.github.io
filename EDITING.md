# Editing this website yourself

This site is a set of ordinary files. There is no content-management system and no visual editor built into the site. You change words by opening a file, editing the sentence, and saving. A browser then shows the saved file.

The copy you are editing now is a private Origin draft. It is not on the public web. A GitHub repository named `Hadeesha/Hadeesha.github.io` does not exist yet. Do not turn on GitHub Pages. A private folder of source files is not a private website.

## Preview on your own computer

1. Install Python 3 if it is not already installed. On macOS it is often already present.
2. Download this project folder to your computer.
3. Open Terminal.
4. Go into the project folder. The folder must be the one that contains `index.html`. Example, after you change the path:

```bash
cd ~/Desktop/lab-site
python3 -m http.server 8741
```

5. Open a browser to `http://127.0.0.1:8741/`.
6. Leave that Terminal window open while you preview. Press Control-C in Terminal when you want to stop the preview.
7. After you edit a file, save it and reload the browser.

`127.0.0.1` is your own computer. It is not an address other people can open.

## Where the words live

| What you want to change | File |
| --- | --- |
| Home introduction and the glioma picture caption | `index.html` |
| Research introduction, framework caption, and program sections | `research/index.html` |
| Biography | `people/index.html` |
| Emails, profiles, and the contact section | `join/index.html` |
| Publication titles, authors, and DOI links | `publications/index.html` |
| The name in the header, footer, and browser tab | `js/site-config.js` only |
| Members placeholder | `members/index.html` |

The header and footer are repeated at the top and bottom of each HTML file. If you rename a navigation label, change it in every file, in both the header and the footer.

### Change the lab name

Open `js/site-config.js`. The only name line looks like this:

```js
labName: "Lab name forthcoming",
```

Change the words inside the quotes, save, and reload. Do not also type the name into the HTML files. Do not use `Piyadasa Lab` while the name is still undecided.

### Change a sentence on the home page

Open `index.html`. Find the paragraph and replace only the sentence. For example, the first paragraph begins:

```html
<p>We investigate how molecular components interact to shape cell and tissue function, in development and in disease.
```

Keep the `<p>` and `</p>`. Those tags mark a paragraph. Save and reload.

### Change a research section

Open `research/index.html`. Each section has a heading and one or more paragraphs. The lung section starts at:

```html
<h2 id="lung-heading">Lung development and molecular organization</h2>
```

You may change the heading words and the paragraph under it. Leave `id="lung-heading"` as it is, because the “On this page” links use that id.

The research page states plans. It does not report finished measurements of every molecular layer. Keep lung development and pediatric brain tumour biology as the two applications.

### Change contact details

Open `join/index.html`. The CHEO address line is:

```html
<a href="mailto:HPiyadasa@cheo.on.ca">HPiyadasa@cheo.on.ca</a>
```

The text between `>` and `</a>` is what readers see. The address after `mailto:` is what the mail program opens. Change both if an address changes, and keep them the same as each other. Do not add a phone number or an office until you have confirmed them. Do not put a personal address or a Stanford address on this page.

### Add a person

Open `people/index.html`. Add a heading and a short paragraph only when that person has joined and has agreed to be listed. Do not invent names.

### Publications

Open `publications/index.html`. Each paper is one block that starts with `<li class="citation`. A DOI link looks like this:

```html
<a href="https://doi.org/10.1016/j.ccell.2025.11.006">10.1016/j.ccell.2025.11.006</a>
```

Copy an existing block, then replace the title, authors, journal, year, and DOI. The `href` and the visible DOI text should match. Do not add a paper that is not yet published. The preprint section must stay labelled as not peer reviewed. Author names and titles of older papers stay as they were published.

## Where the pictures live

| Picture | File | Caption in the HTML |
| --- | --- | --- |
| Home glioma micrograph, page size | `images/glioma-multiplex.jpg` | Multiplex imaging of human glioma tissue. |
| Home glioma micrograph, original size | `images/glioma-multiplex-full.jpg` | Opened by “Open full size” |
| Research framework drawing | `images/research-program.png` | Our research framework: from molecular layers to spatial organization and tissue function. Conceptual schematic; not experimental data. |
| Research framework, original PDF | `documents/research-program.pdf` | Linked as “Original PDF” |
| Glioma imaging panels | `images/glioma-imaging-panels.png` | In `research/index.html`, under Published glioma spatial imaging |
| Glioma segmentation | `images/glioma-segmentation.png` | Same section |

To replace a picture without moving it on the page, export the new picture under the **same file name**, then reload. Do not crop away scale bars, legends, or labels that belong in the figure. Do not recolour a data image.

The framework drawing was rendered from `documents/research-program.pdf`. If you replace the PDF, replace `images/research-program.png` with a new render of that same PDF so the page and the PDF match. Do not put the older generated diagram back on the research page. That older file, if you still have it, is only in `archive/generated-concept/`.

## Colours and type

`css/styles.css` holds the chalky blue colours and the Inter font. You do not need to edit it to change sentences or pictures.

## Save safely

Each save in git is a commit. The history is the undo list.

On your computer, after a change you want to keep:

```bash
git status
git add index.html
git commit -m "Update the home introduction"
```

Use the real file name you changed. Write a short commit message that says what you changed. If a later edit is wrong, the old commit is still there. Do not delete the git history to “clean up.”

`git status` lists files you have changed and not yet committed.

## When a private GitHub repository exists

That repository is not available yet. Someone has to create an empty **private** repository named `Hadeesha.github.io` under the GitHub account `Hadeesha`. This project cannot create it.

After it exists, you can edit in the browser:

1. Open the repository on github.com while you are signed in.
2. Click a file, then the pencil icon, edit, and use the green button to commit. That is a save.
3. Or, on the repository page, press the period key (`.`). That opens github.dev, an editor in the browser. Edit, then use the Source Control icon to commit.

Leave **Settings → Pages** off. Do not choose a branch to publish. Do not add a custom domain.

### A private repository is not a private website

GitHub Pages is a separate switch that publishes HTML as a website. For a repository named `Hadeesha.github.io`, that website’s address is `https://hadeesha.github.io`.

GitHub’s documentation says:

- GitHub Pages on a free plan is for public repositories.
- On GitHub Pro, Team, and Enterprise, Pages can also be used from a private repository.
- A control that limits a Pages site to people who can read the repository exists for **project** sites on GitHub Enterprise Cloud. GitHub says you cannot use that control for an organization site at `<owner>.github.io`. A personal site named `Hadeesha.github.io` is that same kind of site: one site for the account, at `https://hadeesha.github.io`.

So turning Pages on for this repository name would put the site on the internet. Keeping the repository private does not make that website private. Leave Pages off until you explicitly decide to launch.

Do not commit private proposals, a CV file, or source notes into the repository. The public pages already contain the checked biography, contacts, and publication list.

## What not to add

- Do not invent trainees, job openings, phone numbers, or office numbers.
- Do not describe NSERC or CFI proposals as awarded grants.
- Do not add a Canada Research Chair until that credential is formally verified.
- Do not add a password or a sign-in form to the members page.
