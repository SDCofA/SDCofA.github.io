from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PAGES = ("index.html", "almanac.html", "mcp.html", "newsletter.html")
PROHIBITED_CLAIMS = re.compile(
    r"\b(most accurate|best[- ]in[- ]class|leading|unmatched|unrivaled|"
    r"superior|validated forecast|proven accuracy)\b",
    re.IGNORECASE,
)


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.tags.append((tag, {key: value or "" for key, value in attrs}))


def parse_page(name: str) -> tuple[str, DocumentParser]:
    text = (ROOT / name).read_text(encoding="utf-8")
    parser = DocumentParser()
    parser.feed(text)
    return text, parser


class SiteContractTest(unittest.TestCase):
    def test_public_pages_have_one_h1_and_complete_landmarks(self) -> None:
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                _, parsed = parse_page(page)
                tags = [tag for tag, _ in parsed.tags]
                self.assertEqual(tags.count("h1"), 1)
                for landmark in ("header", "nav", "main", "footer"):
                    self.assertIn(landmark, tags)

                viewports = [
                    attrs
                    for tag, attrs in parsed.tags
                    if tag == "meta" and attrs.get("name") == "viewport"
                ]
                self.assertEqual(len(viewports), 1)
                self.assertIn("width=device-width", viewports[0].get("content", ""))

    def test_home_identifies_endorsed_unit_and_editorial_independence(self) -> None:
        text, _ = parse_page("index.html")
        self.assertIn("endorsed analytical unit of Monarch Castle Technologies", text)
        self.assertIn("editorially independent", text)
        self.assertIn("Observation", text)
        self.assertIn("Assessment", text)
        self.assertIn("Forecast", text)
        self.assertIn("uncertainty", text)
        self.assertIn("limitations", text)

    def test_product_surface_is_registry_driven_and_fails_closed(self) -> None:
        text, parsed = parse_page("index.html")
        scripts = [
            attrs.get("src")
            for tag, attrs in parsed.tags
            if tag == "script" and attrs.get("src")
        ]
        self.assertIn("portal.js", scripts)
        self.assertIn('id="product-grid"', text)
        self.assertIn('role="status"', text)

        portal = (ROOT / "portal.js").read_text(encoding="utf-8")
        for expected in (
            "data/products.json",
            "EXPECTED_PRODUCT_IDS",
            "validateProduct",
            "renderFailure",
        ):
            self.assertIn(expected, portal)

    def test_local_links_and_assets_resolve(self) -> None:
        missing: list[str] = []
        for page in PUBLIC_PAGES:
            _, parsed = parse_page(page)
            for tag, attrs in parsed.tags:
                values: list[str] = []
                if tag in {"a", "link"} and attrs.get("href"):
                    values.append(attrs["href"])
                if tag in {"img", "script"} and attrs.get("src"):
                    values.append(attrs["src"])
                if tag == "source" and attrs.get("srcset"):
                    values.extend(
                        item.strip().split()[0]
                        for item in attrs["srcset"].split(",")
                    )
                for raw in values:
                    target = urlsplit(raw)
                    if target.scheme or target.netloc or raw.startswith(("#", "mailto:")):
                        continue
                    local_path = unquote(target.path)
                    if not local_path or local_path.endswith("/"):
                        continue
                    candidate = (ROOT / local_path).resolve()
                    try:
                        candidate.relative_to(ROOT.resolve())
                    except ValueError:
                        missing.append(f"{page}: unsafe path {raw}")
                        continue
                    if not candidate.is_file():
                        missing.append(f"{page}: {raw}")
        self.assertEqual(missing, [])

    def test_images_have_useful_alt_text_except_decorative_images(self) -> None:
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                _, parsed = parse_page(page)
                for tag, attrs in parsed.tags:
                    if tag != "img":
                        continue
                    self.assertIn("alt", attrs)

    def test_styles_include_accessibility_and_375px_layout_gates(self) -> None:
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        for expected in (
            ":focus-visible",
            "@media (prefers-reduced-motion: reduce)",
            "overflow-wrap:",
            "min-width: 0",
            "@media (max-width: 760px)",
        ):
            self.assertIn(expected, css)
        self.assertNotRegex(css, r"(?m)^\s*width:\s*[4-9]\d{2,}px")

    def test_public_copy_has_no_prohibited_performance_claims(self) -> None:
        candidates = [
            *[ROOT / page for page in PUBLIC_PAGES],
            ROOT / "portal.js",
            ROOT / "data" / "products.json",
            ROOT / "mcp-catalog.json",
        ]
        violations: list[str] = []
        for path in candidates:
            if not path.is_file():
                continue
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if PROHIBITED_CLAIMS.search(line):
                    violations.append(f"{path.relative_to(ROOT)}:{line_number}")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
