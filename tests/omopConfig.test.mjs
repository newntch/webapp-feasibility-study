import assert from 'node:assert/strict';
import test from 'node:test';
import { createFeasibilityService } from '../src/server/createFeasibilityService.js';
import { loadServerConfig } from '../src/server/config.js';
import { normalizeDataSource } from '../src/server/dataSourceConfig.js';

test('OMOP data-source aliases normalize to the DuckDB adapter', () => {
  assert.equal(normalizeDataSource('omop'), 'omop-duckdb');
  assert.equal(normalizeDataSource('OMOP_CDM'), 'omop-duckdb');
  assert.equal(normalizeDataSource('omop-duckdb'), 'omop-duckdb');
});

test('server config exposes the OMOP DuckDB path and environment override', async () => {
  const config = await loadServerConfig({
    CLINICAL_DATA_SOURCE: 'omop',
    OMOP_DUCKDB_PATH: 'temp/example.omop.duckdb'
  });

  assert.equal(config.clinicalDataSource, 'omop-duckdb');
  assert.equal(config.dataSource, 'omop-duckdb');
  assert.equal(config.omopDuckdb.path, 'temp/example.omop.duckdb');
});

test('feasibility service factory selects the OMOP repository from config', () => {
  const service = createFeasibilityService({
    root: '/project',
    config: {
      clinicalDataSource: 'omop-duckdb',
      omopDuckdb: { path: 'data/example.duckdb' }
    },
    loadDuckdb: async () => ({})
  });

  assert.equal(service.dataSource, 'omop-duckdb');
  assert.deepEqual(service.repository.config(), {
    dataSource: 'omop-duckdb',
    path: 'data/example.duckdb'
  });
});
