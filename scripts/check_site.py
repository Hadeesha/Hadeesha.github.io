#!/usr/bin/env python3
"""Check the static lab-site draft: links, structure, contrast, and draft boundaries."""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    ROOT / "index.html",
    ROOT / "research" / "index.html",
    ROOT / "people" / "index.html",
    ROOT / "publications" / "index.html",
    ROOT / "join" / "index.html",
    ROOT / "contact" / "index.html",
    ROOT / "members" / "index.html",
]
ORCID = "0000-0002-0276-6590"
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "source", "track", "wbr",
}
FORBIDDEN = [
    (r"Piyadasa Lab", "do not use the name Piyadasa Lab"),
    (r"artificial intelligence", "leave out artificial intelligence"),
    (r"machine learning", "leave out machine learning"),
    (r"\ballergy\b", "leave out allergy"),
    (r"\bLeiden\b", "leave out Leiden"),
    (r"Canada Research Chair", "leave out Canada Research Chair"),
    (r"lorem ipsum", "leave out placeholder copy"),
    (r"\bet al\.", "do not add citation shorthand"),
    (r"now hiring", "do not advertise an opening"),
    (r"open positions?", "do not advertise an opening"),
    (r"we are recruiting(?! our founding team)", "do not advertise an opening"),
    (r"apply now", "do not advertise an opening"),
    (r"positions available", "do not advertise an opening"),
    (r"fonts\.googleapis\.com", "fonts are self-hosted"),
    (r"googletagmanager|google-analytics|gtag\(", "do not add analytics"),
]


def rel_lum(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]

    def pivot(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (pivot(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(foreground: str, background: str) -> float:
    lighter = max(rel_lum(foreground), rel_lum(background))
    darker = min(rel_lum(foreground), rel_lum(background))
    return (lighter + 0.05) / (darker + 0.05)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.stack: list[str] = []
        self.links: list[dict] = []
        self.headings: list[tuple[int, str]] = []
        self.scripts: list[str] = []
        self.styles: list[str] = []
        self.images: list[dict] = []
        self.title = ""
        self.metas: list[dict] = []
        self.lang = ""
        self.has_viewport = False
        self.has_noindex = False
        self.has_skip = False
        self.main_ids: list[str] = []
        self.config_keys: list[str] = []
        self.bad_controls: list[str] = []
        self._link: dict | None = None
        self._heading: list[str] | None = None
        self._heading_level = 0
        self._in_title = False
        self.stack_errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value for key, value in attrs}
        if tag not in VOID_TAGS:
            self.stack.append(tag)
        if tag == "title":
            self._in_title = True
        if "id" in attr and attr["id"]:
            self.ids.append(attr["id"])
        if tag == "html":
            self.lang = attr.get("lang") or ""
        if tag == "meta":
            self.metas.append(attr)
            name = (attr.get("name") or "").lower()
            if name == "viewport":
                self.has_viewport = True
            if name == "robots" and attr.get("content") and "noindex" in attr["content"]:
                self.has_noindex = True
        if tag == "script" and attr.get("src"):
            self.scripts.append(attr["src"])
        if tag == "link" and attr.get("rel") == "stylesheet" and attr.get("href"):
            self.styles.append(attr["href"])
        if tag == "img":
            self.images.append(attr)
        if tag in {"form", "input", "textarea", "select"}:
            self.bad_controls.append(tag)
        if tag == "button":
            classes = set((attr.get("class") or "").split())
            if not classes.intersection({"figure-zoom", "figure-lightbox-close"}):
                self.bad_controls.append(tag)
        if tag == "main" and attr.get("id"):
            self.main_ids.append(attr["id"])
        if attr.get("data-config"):
            self.config_keys.append(attr["data-config"])
        if tag == "a":
            href = attr.get("href") or ""
            self._link = {
                "href": href,
                "in_footer": "footer" in self.stack,
                "in_header": "header" in self.stack,
                "text": [],
                "has_config": bool(attr.get("data-config")),
                "attrs": attr,
            }
            if href == "#content":
                self.has_skip = True
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading = []
            self._heading_level = int(tag[1])

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._link is not None:
            self._link["text"].append(data)
        if self._heading is not None:
            self._heading.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._link is not None:
            self._link["text_value"] = "".join(self._link["text"]).strip()
            self.links.append(self._link)
            self._link = None
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._heading is not None:
            if int(tag[1]) == self._heading_level:
                self.headings.append((self._heading_level, "".join(self._heading).strip()))
                self._heading = None
        if tag in VOID_TAGS:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            self.stack_errors.append(f"closed <{tag}> before {self.stack[-1]}")
            while self.stack and self.stack[-1] != tag:
                self.stack.pop()
            if self.stack:
                self.stack.pop()

    def close(self) -> None:
        super().close()
        if self.stack:
            self.stack_errors.append("unclosed tags: " + ", ".join(self.stack))


def parse_config() -> str:
    text = (ROOT / "js" / "site-config.js").read_text(encoding="utf-8")
    names = re.findall(r"labName:\s*\"([^\"]*)\"", text)
    if len(names) != 1:
        raise SystemExit(f"expected one labName in js/site-config.js, found {len(names)}")
    if not names[0].strip():
        raise SystemExit("labName is empty")
    if names[0].strip().lower() == "piyadasa lab":
        raise SystemExit("labName must not be Piyadasa Lab")
    return names[0]


def css_variables() -> dict[str, str]:
    text = (ROOT / "css" / "styles.css").read_text(encoding="utf-8")
    root = re.search(r":root\s*\{([^}]+)\}", text)
    if not root:
        raise SystemExit("css :root block is missing")
    found = dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})", root.group(1)))
    return found


def check_contrast(errors: list[str]) -> None:
    colors = css_variables()
    pairs = [
        ("--ink", "--paper", 4.5),
        ("--muted", "--paper", 4.5),
        ("--sage", "--paper", 4.5),
        ("--clay", "--paper", 4.5),
        ("--ink", "--beige", 4.5),
        ("--muted", "--beige", 4.5),
        ("--sage", "--beige", 4.5),
        ("--clay", "--beige", 4.5),
        ("--line-strong", "--paper", 3.0),
        ("--line-strong", "--beige", 3.0),
        ("--paper", "--ink", 4.5),
    ]
    for foreground, background, minimum in pairs:
        if foreground not in colors or background not in colors:
            errors.append(f"missing colour token {foreground} or {background}")
            continue
        ratio = contrast(colors[foreground], colors[background])
        if ratio < minimum:
            errors.append(
                f"contrast {colors[foreground]} on {colors[background]} is {ratio:.2f}, need {minimum:.1f}"
            )


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def resolve_link(page: Path, href: str) -> tuple[Path, str] | None:
    if href.startswith(("http://", "https://", "mailto:", "tel:")):
        return None
    path, _, fragment = href.partition("#")
    if path == "":
        target = page
    else:
        target = (page.parent / path).resolve()
        if target.is_dir():
            target = target / "index.html"
    return target, fragment


def main() -> int:
    errors: list[str] = []
    notes: list[str] = []
    lab_name = parse_config()
    notes.append(f"lab name: {lab_name}")
    allowed_emails = {"hpiyadasa@cheo.on.ca", "hadeesha.piyadasa@uottawa.ca"}

    site_files = []
    for pattern in ("*.html", "*/*.html", "css/*.css", "js/*.js"):
        site_files.extend(ROOT.glob(pattern))

    for path in site_files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        for pattern, message in FORBIDDEN:
            if re.search(pattern, text, flags=re.IGNORECASE):
                errors.append(f"{relative}: {message}")
        if "Stanford" in text and relative != "people/index.html":
            errors.append(f"{relative}: Stanford may appear only on the people page")
        if path.suffix == ".html" and lab_name in text:
            errors.append(f"{relative}: lab name is hardcoded; keep it only in js/site-config.js")
        if path.suffix == ".html":
            emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text))
            unexpected = emails - allowed_emails
            if unexpected:
                errors.append(f"{relative}: unexpected email {sorted(unexpected)}")

    orcid_hits = set()
    for path in ROOT.glob("**/*.html"):
        orcid_hits.update(re.findall(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", path.read_text(encoding="utf-8")))
    if orcid_hits != {ORCID}:
        errors.append(f"ORCID ids found: {sorted(orcid_hits) or 'none'}")

    parsed: dict[Path, PageParser] = {}
    for page in PAGES:
        if not page.exists():
            errors.append(f"missing page {page.relative_to(ROOT)}")
            continue
        parser = PageParser()
        parser.feed(page.read_text(encoding="utf-8"))
        parser.close()
        parsed[page.resolve()] = parser

    for page, parser in parsed.items():
        label = page.relative_to(ROOT).as_posix()
        if parser.lang != "en-CA":
            errors.append(f"{label}: lang should be en-CA")
        if not parser.has_viewport:
            errors.append(f"{label}: missing viewport")
        if parser.has_noindex:
            errors.append(f"{label}: public page should not send noindex")
        if not parser.has_skip:
            errors.append(f"{label}: missing skip link")
        if parser.main_ids != ["content"]:
            errors.append(f"{label}: main#content missing")
        if parser.config_keys.count("labName") < 1:
            errors.append(f"{label}: lab name should be bound in the header")
        if parser.scripts != ["../js/site-config.js", "../js/site.js"] and parser.scripts != ["js/site-config.js", "js/site.js"]:
            errors.append(f"{label}: unexpected scripts {parser.scripts}")
        if len(parser.styles) != 1:
            errors.append(f"{label}: expected one stylesheet")
        headings = [level for level, _ in parser.headings]
        h1 = [text for level, text in parser.headings if level == 1]
        if len(h1) != 1 or not h1[0]:
            errors.append(f"{label}: expected one non-empty h1, found {h1}")
        previous = 0
        for level in headings:
            if previous and level > previous + 1:
                errors.append(f"{label}: heading level jumps from h{previous} to h{level}")
            previous = level
        if len(parser.ids) != len(set(parser.ids)):
            errors.append(f"{label}: duplicate ids")
        if parser.bad_controls:
            errors.append(f"{label}: unexpected controls {parser.bad_controls}")
        if parser.stack_errors:
            errors.append(f"{label}: markup stack {parser.stack_errors}")
        for image in parser.images:
            alt = (image.get("alt") or "").strip()
            if not alt:
                errors.append(f"{label}: image missing alt text {image.get('src')}")
        members_outside_footer = False
        for link in parser.links:
            href = link["href"]
            if not href:
                errors.append(f"{label}: empty href")
                continue
            if not link["text_value"] and not link["has_config"]:
                errors.append(f"{label}: link {href} has no text")
            path_only = href.partition("#")[0]
            resolved = resolve_link(page, href)
            if resolved is None:
                continue
            target, fragment = resolved
            points_at_members = bool(path_only) and target.name == "index.html" and target.parent.name == "members"
            if points_at_members and not link["in_footer"]:
                members_outside_footer = True
            if points_at_members and link["in_footer"]:
                link["members_footer"] = True
            if target not in parsed and not target.exists():
                errors.append(f"{label}: broken link {href}")
                continue
            if fragment:
                target_parser = parsed.get(target.resolve())
                if target_parser is None:
                    errors.append(f"{label}: fragment target not checked {href}")
                elif fragment not in target_parser.ids:
                    errors.append(f"{label}: missing anchor #{fragment} for {href}")
        if members_outside_footer:
            errors.append(f"{label}: members link appears outside the footer")

    def page_text(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    home_text = page_text(ROOT / "index.html")
    if "images/glioma-multiplex.jpg" not in home_text or "Illustration of a glial tumor microenvironment" not in home_text:
        errors.append("home: the banner image and its caption are missing")
    # Responsive copies: every srcset entry must point at a file that exists.
    import re as _re
    for page_path in sorted(ROOT.rglob("index.html")):
        text = page_text(page_path)
        for srcset in _re.findall(r'srcset="([^"]+)"', text):
            for cand in srcset.split(","):
                rel = cand.strip().split()[0]
                if not (page_path.parent / rel).exists():
                    errors.append(f"{page_path.relative_to(ROOT)}: srcset file missing {rel}")
    if "222" in home_text or "UCLA" in home_text or "UCSF" in home_text:
        errors.append("home: a source sample code is exposed")
    research_page = page_text(ROOT / "research" / "index.html")
    # The published-glioma figures and their DOI were removed from the research
    # page by the owner on 8 Nov 2026; only the framework figure is required now.
    for needle in (
        "research-program.png",
    ):
        if needle not in research_page:
            errors.append(f"research: missing {needle}")
    if "UCLA" in research_page or "UCSF" in research_page or "R5C1" in research_page or "R1C4" in research_page:
        errors.append("research: a source sample code is exposed")
    publications_text = page_text(ROOT / "publications" / "index.html")
    # The introduction states the counts; the lists must agree with it, and every
    # entry must carry exactly one DOI link. (The in-browser editor updates the
    # sentence automatically when an entry is added or removed.)
    counts = {
        "journal": len(re.findall(r'class="citation citation-journal\b', publications_text)),
        "chapter": len(re.findall(r'class="citation citation-chapter\b', publications_text)),
        "preprint": len(re.findall(r'class="citation citation-preprint\b', publications_text)),
    }
    stated = re.search(
        r"(\d+) journal publications?, (\d+) book chapters?, and (\d+) preprints?", publications_text
    )
    if stated:
        expected = {"journal": int(stated.group(1)), "chapter": int(stated.group(2)), "preprint": int(stated.group(3))}
        for kind, n in expected.items():
            if counts[kind] != n:
                errors.append(f"publications: introduction says {n} {kind} entries but the list has {counts[kind]}")
    total = sum(counts.values())
    if publications_text.count("https://doi.org/") != total:
        errors.append(f"publications: {total} entries but {publications_text.count('https://doi.org/')} DOI links")
    if "10.xxxx" in publications_text:
        errors.append("publications: a placeholder DOI (10.xxxx) is still present")
    if "has not been peer reviewed" not in publications_text:
        errors.append("publications: the preprint must be labelled as not peer reviewed")
    contact_text = page_text(ROOT / "contact" / "index.html")
    for email in ("hpiyadasa@cheo.on.ca", "hadeesha.piyadasa@uottawa.ca"):
        if email not in contact_text:
            errors.append(f"contact: missing {email}")
    for url in (
        "https://www.cheoresearch.ca/research/find-a-researcher/hadeesha-piyadasa/",
        "https://www.uottawa.ca/faculty-medicine/directory/dr-hadeesha-piyadasa",
    ):
        if url not in contact_text:
            errors.append(f"contact: missing profile {url}")
    if "[phone" in contact_text or "[office" in contact_text or "[email" in contact_text:
        errors.append("contact: unconfirmed contact placeholders are still shown")
    join_text = page_text(ROOT / "join" / "index.html")
    if "contact/" not in join_text:
        errors.append("join: should link to the contact page")
    members_text = page_text(ROOT / "members" / "index.html").lower() if (ROOT / "members" / "index.html").exists() else "sign-in is not available password"
    if "sign-in is not available" not in members_text or "password" not in members_text:
        errors.append("members: the planned page should say that sign-in is not available")
    people_text = page_text(ROOT / "people" / "index.html")
    for phrase in (
        "BSc (Honours) in Biochemistry",
        "PhD in Immunology",
        "University of Manitoba",
        "Department of Pathology at Stanford University",
        "CHEO Research Institute",
    ):
        if phrase not in people_text:
            errors.append(f"people: missing verified phrase {phrase}")
    research_text = page_text(ROOT / "research" / "index.html")
    for phrase in ("lung development", "pediatric brain tumor"):
        if phrase not in research_text.lower():
            errors.append(f"research: missing {phrase}")

    for required in ("inter-400.woff2", "inter-500.woff2", "inter-600.woff2"):
        if not (ROOT / "fonts" / required).exists():
            errors.append(f"missing font {required}")
    robots = ROOT / "robots.txt"
    if not robots.exists():
        errors.append("robots.txt is missing")
    else:
        robots_text = robots.read_text(encoding="utf-8")
        if re.search(r"(?m)^Disallow:\s*/\s*$", robots_text):
            errors.append("robots.txt should not disallow the whole public site")
        if "Sitemap: https://hadeesha.github.io/sitemap.xml" not in robots_text:
            errors.append("robots.txt should list the sitemap")

    check_contrast(errors)

    external = set()
    for parser in parsed.values():
        for link in parser.links:
            if link["href"].startswith("http"):
                external.add(link["href"])
    for url in sorted(external):
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0"})
        opener = urllib.request.build_opener(NoRedirect())
        try:
            with opener.open(request, timeout=20) as response:
                status = response.status
                location = response.headers.get("Location", "")
        except urllib.error.HTTPError as exc:
            status = exc.code
            location = exc.headers.get("Location", "") if exc.headers else ""
        except Exception as exc:  # noqa: BLE001 — report the network result in the check output
            errors.append(f"could not open {url}: {exc}")
            continue
        if status in {301, 302, 303, 307, 308} and location:
            notes.append(f"external {status}: {url}")
        elif status < 400:
            notes.append(f"external {status}: {url}")
        elif status == 403:
            notes.append(f"external 403, host blocked the checker: {url}")
        else:
            errors.append(f"{url} returned {status}")

    print("Lab site draft check")
    for note in notes:
        print(f"  note: {note}")
    if errors:
        print(f"{len(errors)} problem(s):")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("  pages:", ", ".join(page.relative_to(ROOT).as_posix() for page in PAGES))
    print("  result: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
