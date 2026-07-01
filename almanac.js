function normalizeSearch(value) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function renderCountries(countries, query = "") {
  const list = document.getElementById("country-list");
  const normalized = normalizeSearch(query.trim());
  const filtered = countries.filter(country => {
    const haystack = normalizeSearch(`${country.name} ${country.official_name} ${country.alpha2} ${country.alpha3}`);
    return haystack.includes(normalized);
  });
  list.innerHTML = filtered.slice(0, 249).map(country => `
    <a class="country-link" href="country/${country.slug}.html">
      <strong>${country.name}</strong>
      <span>${country.alpha2} / ${country.alpha3}</span>
    </a>
  `).join("");
}

const countries = window.SDCOFA_COUNTRIES || [];
renderCountries(countries);
document.getElementById("country-search").addEventListener("input", event => {
  renderCountries(countries, event.target.value);
});
