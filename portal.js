"use strict";

const EXPECTED_PRODUCT_IDS = Object.freeze([
  "border-neighbor-threat-index",
  "mena-threat-index",
  "world-threat-index",
]);

const REQUIRED_PRODUCT_FIELDS = Object.freeze([
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
]);

function requireText(product, field) {
  if (typeof product[field] !== "string" || !product[field].trim()) {
    throw new Error(`${product.id || "unknown product"}: missing ${field}`);
  }
}

function requireHttpsUrl(product, field) {
  requireText(product, field);
  const parsed = new URL(product[field]);
  if (parsed.protocol !== "https:") {
    throw new Error(`${product.id}: ${field} must use HTTPS`);
  }
}

function validateProduct(product) {
  if (!product || typeof product !== "object" || Array.isArray(product)) {
    throw new Error("Product entry must be an object");
  }
  for (const field of REQUIRED_PRODUCT_FIELDS) {
    requireText(product, field);
  }
  if (!EXPECTED_PRODUCT_IDS.includes(product.id)) {
    throw new Error(`Unknown product id: ${product.id}`);
  }
  requireHttpsUrl(product, "canonicalUrl");
  requireHttpsUrl(product, "methodologyUrl");
  if (
    product.canonicalUrl !== `https://sdcofa.github.io/${product.id}/`
  ) {
    throw new Error(`${product.id}: canonical URL drift`);
  }
  if (!/^assets\/[a-z0-9-]+\.png$/.test(product.logo)) {
    throw new Error(`${product.id}: logo must be an approved local PNG`);
  }
  if (product.owner !== "SDCofA") {
    throw new Error(`${product.id}: owner drift`);
  }
  if (product.endorsement !== "Part of Monarch Castle Technologies") {
    throw new Error(`${product.id}: endorsement drift`);
  }
  return product;
}

function validateRegistry(payload) {
  if (
    !payload ||
    payload.schemaVersion !== "1.0.0" ||
    !Array.isArray(payload.products)
  ) {
    throw new Error("Unsupported product registry contract");
  }
  const products = payload.products.map(validateProduct);
  const ids = products.map((product) => product.id);
  if (
    ids.length !== EXPECTED_PRODUCT_IDS.length ||
    new Set(ids).size !== EXPECTED_PRODUCT_IDS.length ||
    EXPECTED_PRODUCT_IDS.some((id) => !ids.includes(id))
  ) {
    throw new Error("Product registry must contain the exact approved product IDs");
  }
  return products;
}

function appendDefinition(list, label, value, className = "") {
  const term = document.createElement("dt");
  term.textContent = label;
  const detail = document.createElement("dd");
  detail.textContent = value;
  if (className) {
    detail.className = className;
  }
  list.append(term, detail);
}

function productCard(product, onAssetFailure) {
  const article = document.createElement("article");
  article.className = "product-card";
  article.dataset.productId = product.id;

  const logoLink = document.createElement("a");
  logoLink.className = "product-logo-link";
  logoLink.href = product.canonicalUrl;
  logoLink.setAttribute("aria-label", `Open ${product.name}`);

  const logo = document.createElement("img");
  logo.className = "product-logo";
  logo.src = product.logo;
  logo.alt = `${product.name} approved product logo`;
  logo.addEventListener("error", onAssetFailure, { once: true });
  logoLink.append(logo);

  const title = document.createElement("h3");
  const productLink = document.createElement("a");
  productLink.href = product.canonicalUrl;
  productLink.textContent = product.name;
  title.append(productLink);

  const endorsement = document.createElement("p");
  endorsement.className = "endorsement";
  endorsement.textContent = product.endorsement;

  const metadata = document.createElement("dl");
  metadata.className = "trust-list";
  appendDefinition(metadata, "Lifecycle", product.lifecycle, "status-label");
  appendDefinition(metadata, "Coverage", product.coverage);
  appendDefinition(metadata, "Update cadence", product.updateFrequency);
  appendDefinition(metadata, "Freshness", product.freshness);
  appendDefinition(metadata, "Provenance", product.provenance);
  appendDefinition(metadata, "Owner", product.owner);
  appendDefinition(
    metadata,
    "Forecast evidence",
    product.forecastEvidenceStatus,
    "status-label",
  );
  appendDefinition(metadata, "Forecast limitations", product.forecastLimitations);

  const actions = document.createElement("p");
  actions.className = "card-actions";
  const open = document.createElement("a");
  open.className = "text-link";
  open.href = product.canonicalUrl;
  open.textContent = "Open product";
  const method = document.createElement("a");
  method.className = "text-link";
  method.href = product.methodologyUrl;
  method.textContent = "Read methodology";
  actions.append(open, method);

  article.append(logoLink, title, endorsement, metadata, actions);
  return article;
}

function renderFailure(error) {
  const grid = document.getElementById("product-grid");
  const status = document.getElementById("product-status");
  if (grid) {
    grid.replaceChildren();
  }
  if (status) {
    status.hidden = false;
    status.setAttribute("role", "alert");
    status.textContent =
      "Product registry unavailable. No partial or unverified product data is shown.";
  }
  console.error("SDCofA product registry rejected:", error);
}

function renderProducts(products) {
  const grid = document.getElementById("product-grid");
  const status = document.getElementById("product-status");
  if (!grid || !status) {
    return;
  }
  let failed = false;
  const onAssetFailure = () => {
    if (!failed) {
      failed = true;
      renderFailure(new Error("Approved product logo failed to load"));
    }
  };
  const cards = products.map((product) => productCard(product, onAssetFailure));
  grid.replaceChildren(...cards);
  status.hidden = true;
  status.textContent = "";
}

async function loadProducts() {
  if (!document.getElementById("product-grid")) {
    return;
  }
  try {
    const response = await fetch("data/products.json", {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new Error(`Product registry returned HTTP ${response.status}`);
    }
    renderProducts(validateRegistry(await response.json()));
  } catch (error) {
    renderFailure(error);
  }
}

loadProducts();
