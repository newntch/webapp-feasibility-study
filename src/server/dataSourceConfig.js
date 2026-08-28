const SUPPORTED_DATA_SOURCES = new Set(['json', 'sqlserver', 'omop-duckdb']);
const DATA_SOURCE_ALIASES = new Map([
  ['omop', 'omop-duckdb'],
  ['omop-cdm', 'omop-duckdb'],
  ['omop_cdm', 'omop-duckdb'],
  ['omop_duckdb', 'omop-duckdb']
]);

export function normalizeDataSource(value) {
  const requested = String(value || 'json').trim().toLowerCase();
  const normalized = DATA_SOURCE_ALIASES.get(requested) || requested;
  if (SUPPORTED_DATA_SOURCES.has(normalized)) return normalized;
  throw new Error(`Unsupported DATA_SOURCE "${value}". Use "json", "sqlserver", or "omop-duckdb".`);
}
