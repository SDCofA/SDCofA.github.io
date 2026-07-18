from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PRODUCTS = {
    "border-neighbor-threat-index": {
        "name": "Border Neighbor Threat Index",
        "canonicalUrl": "https://sdcofa.github.io/border-neighbor-threat-index/",
        "methodologyUrl": (
            "https://github.com/SDCofA/border-neighbor-threat-index/blob/main/README.md"
        ),
        "lifecycle": "review-required",
        "updateFrequency": "every 2 hours",
        "logo": "assets/bnti-logo.png",
    },
    "mena-threat-index": {
        "name": "MENA Threat Index",
        "canonicalUrl": "https://sdcofa.github.io/mena-threat-index/",
        "methodologyUrl": (
            "https://github.com/SDCofA/mena-threat-index/blob/main/README.md"
        ),
        "lifecycle": "production",
        "updateFrequency": "every 2 hours",
        "logo": "assets/mena-logo.png",
    },
    "world-threat-index": {
        "name": "World Threat Index",
        "canonicalUrl": "https://sdcofa.github.io/world-threat-index/",
        "methodologyUrl": (
            "https://github.com/SDCofA/world-threat-index/blob/main/docs/"
            "wti-methodology.md"
        ),
        "lifecycle": "production",
        "updateFrequency": "every few hours",
        "logo": "assets/wti-logo.png",
    },
}

TRUST_FIELDS = {
    "id",
    "name",
    "canonicalUrl",
    "logo",
    "lifecycle",
    "coverage",
    "methodologyUrl",
    "updateFrequency",
    "freshness",
    "provenance",
    "owner",
    "endorsement",
    "forecastEvidenceStatus",
    "forecastLimitations",
}


def load_json(relative_path: str) -> object:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class ProductDataContractTest(unittest.TestCase):
    def test_product_registry_has_exact_known_ids_and_trust_fields(self) -> None:
        payload = load_json("data/products.json")
        self.assertEqual(payload["schemaVersion"], "1.0.0")
        products = payload["products"]
        by_id = {product["id"]: product for product in products}
        self.assertEqual(set(by_id), set(EXPECTED_PRODUCTS))
        self.assertEqual(len(by_id), len(products))

        for product_id, expected in EXPECTED_PRODUCTS.items():
            with self.subTest(product=product_id):
                product = by_id[product_id]
                self.assertTrue(TRUST_FIELDS.issubset(product))
                for key, value in expected.items():
                    self.assertEqual(product[key], value)
                self.assertEqual(product["owner"], "SDCofA")
                self.assertEqual(
                    product["endorsement"], "Part of Monarch Castle Technologies"
                )
                self.assertTrue(product["coverage"].strip())
                self.assertTrue(product["freshness"].strip())
                self.assertTrue(product["provenance"].strip())
                self.assertTrue(product["forecastEvidenceStatus"].strip())
                self.assertTrue(product["forecastLimitations"].strip())
                self.assertTrue((ROOT / product["logo"]).is_file())

    def test_product_urls_are_https_and_canonical(self) -> None:
        products = load_json("data/products.json")["products"]
        for product in products:
            with self.subTest(product=product["id"]):
                for field in ("canonicalUrl", "methodologyUrl"):
                    parsed = urlsplit(product[field])
                    self.assertEqual(parsed.scheme, "https")
                    self.assertTrue(parsed.netloc)
                self.assertEqual(
                    product["canonicalUrl"],
                    f"https://sdcofa.github.io/{product['id']}/",
                )

    def test_runtime_validator_accepts_registry_and_rejects_unknown_ids(self) -> None:
        harness = r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("portal.js", "utf8");
const registry = JSON.parse(fs.readFileSync("data/products.json", "utf8"));
const sandbox = {
  console,
  URL,
  document: { getElementById: () => null },
  fetch: async () => { throw new Error("not called"); },
};
vm.createContext(sandbox);
vm.runInContext(source.replace(/loadProducts\(\);\s*$/, ""), sandbox);
for (const product of registry.products) sandbox.validateProduct(product);
let rejected = false;
try {
  sandbox.validateRegistry({
    schemaVersion: "1.0.0",
    products: [...registry.products, { ...registry.products[0], id: "unknown" }],
  });
} catch (error) {
  rejected = /unknown|exact/i.test(String(error));
}
if (!rejected) process.exit(2);
"""
        completed = subprocess.run(
            ["node", "-e", harness],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )


class ExistingDataBehaviorTest(unittest.TestCase):
    def test_catalog_references_resolve_and_ids_remain_stable(self) -> None:
        catalog = load_json("mcp-catalog.json")
        surfaces = catalog["data_surfaces"]
        by_id = {surface["id"]: surface for surface in surfaces}
        self.assertEqual(
            set(by_id),
            {
                "sdcofa.country_almanac",
                "sdcofa.weekly_letter_template",
                "sdcofa.index_scores_future",
            },
        )
        self.assertEqual(
            by_id["sdcofa.country_almanac"]["json"],
            "https://sdcofa.github.io/data/countries.json",
        )
        self.assertTrue((ROOT / "almanac.html").is_file())
        self.assertTrue((ROOT / "data" / "countries.json").is_file())
        self.assertTrue((ROOT / "downloads" / "weekly-letter-template.md").is_file())

    def test_country_records_have_unique_codes_slugs_and_generated_pages(self) -> None:
        countries = load_json("data/countries.json")
        self.assertGreaterEqual(len(countries), 195)
        for key in ("alpha2", "alpha3", "slug"):
            values = [country[key] for country in countries]
            self.assertEqual(len(values), len(set(values)), key)
        missing = [
            country["slug"]
            for country in countries
            if not (ROOT / "country" / f"{country['slug']}.html").is_file()
        ]
        self.assertEqual(missing, [])

    def test_almanac_search_filters_real_records_and_keeps_deep_links(self) -> None:
        harness = r"""
const fs = require("fs");
const vm = require("vm");
const countries = JSON.parse(fs.readFileSync("data/countries.json", "utf8"));
let inputHandler = null;
const list = { innerHTML: "" };
const sandbox = {
  window: { SDCOFA_COUNTRIES: countries },
  document: {
    getElementById(id) {
      if (id === "country-list") return list;
      if (id === "country-search") {
        return { addEventListener: (_, handler) => { inputHandler = handler; } };
      }
      throw new Error(`unexpected id: ${id}`);
    },
  },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync("almanac.js", "utf8"), sandbox);
if (!inputHandler || !list.innerHTML.includes("country/turkiye.html")) process.exit(2);
inputHandler({ target: { value: "TURKIYE" } });
if (!list.innerHTML.includes("country/turkiye.html")) process.exit(3);
if ((list.innerHTML.match(/class="country-link"/g) || []).length !== 1) process.exit(4);
inputHandler({ target: { value: "zzzz-not-a-country" } });
if (list.innerHTML.trim() !== "") process.exit(5);
"""
        completed = subprocess.run(
            ["node", "-e", harness],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
