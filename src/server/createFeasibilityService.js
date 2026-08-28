import { FeasibilityService } from './feasibilityService.js';
import { JsonFeasibilityRepository } from './jsonFeasibilityRepository.js';
import { OmopDuckdbRepository } from './omopDuckdbRepository.js';
import { SqlServerFeasibilityRepository } from './sqlServerFeasibilityRepository.js';
import { normalizeDataSource } from './dataSourceConfig.js';

export function createFeasibilityService(options = {}) {
  const runtimeConfig = normalizeRuntimeConfig(options);
  const repository = options.repository || createRepository(runtimeConfig, options);
  return new FeasibilityService({
    dataSource: runtimeConfig.dataSource,
    repository
  });
}

function createRepository(runtimeConfig, options) {
  if (runtimeConfig.dataSource === 'sqlserver') {
    return new SqlServerFeasibilityRepository({
      connectionConfig: runtimeConfig.sqlServer,
      loadMssql: options.loadMssql
    });
  }

  if (runtimeConfig.dataSource === 'omop-duckdb') {
    return new OmopDuckdbRepository({
      ...runtimeConfig.omopDuckdb,
      root: options.root,
      loadDuckdb: options.loadDuckdb
    });
  }

  return new JsonFeasibilityRepository({
    root: options.root
  });
}

function normalizeRuntimeConfig(options) {
  if (options.config) {
    return {
      dataSource: normalizeDataSource(options.config.clinicalDataSource || options.config.dataSource),
      sqlServer: options.config.sqlServer || {},
      omopDuckdb: options.config.omopDuckdb || options.config.omopDuckDB || {}
    };
  }

  return {
    dataSource: normalizeDataSource(options.dataSource || 'json'),
    sqlServer: options.sqlServer || {},
    omopDuckdb: options.omopDuckdb || options.omopDuckDB || {}
  };
}
