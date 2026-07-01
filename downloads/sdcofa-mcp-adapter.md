# SDCofA MCP Adapter Notes

This adapter note describes how an MCP server can expose SDCofA data without inventing analysis.

## Readable sources

- `https://sdcofa.github.io/data/countries.json`
- `https://sdcofa.github.io/almanac.html`
- `https://sdcofa.github.io/mcp-catalog.json`

## Allowed operations

- List countries.
- Read ISO reference fields.
- Link to a country almanac page.
- Return the publication status of a data surface.

## Disallowed operations

- Generate unpublished risk scores.
- Produce AI-written country judgments.
- Claim BNTI, WTI, or MENA outputs exist before the public data files are published.

## Future hosted server tools

- `list_countries`
- `get_country_reference`
- `get_publication_status`
- `get_index_metadata`
