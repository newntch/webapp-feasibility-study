import { isAbsolute, resolve } from 'node:path';
import { buildOmopFeasibilityCountSql } from '../omopSqlBuilder.js';

export const DEFAULT_OMOP_DUCKDB_PATH = 'data/omop/ehrshot_omop/ehrshot_omop.duckdb';

const CONCEPT_CATALOG_SQL = `
/* concept_catalog */
WITH used_concepts AS (
  SELECT 'diagnosis' AS domain, condition_concept_id AS concept_id, COUNT(*) AS event_count
  FROM condition_occurrence
  WHERE condition_concept_id IS NOT NULL AND condition_concept_id <> 0
  GROUP BY condition_concept_id
  UNION ALL
  SELECT 'lab' AS domain, measurement_concept_id AS concept_id, COUNT(*) AS event_count
  FROM measurement
  WHERE measurement_concept_id IS NOT NULL AND measurement_concept_id <> 0
  GROUP BY measurement_concept_id
  UNION ALL
  SELECT 'drug' AS domain, drug_concept_id AS concept_id, COUNT(*) AS event_count
  FROM drug_exposure
  WHERE drug_concept_id IS NOT NULL AND drug_concept_id <> 0
  GROUP BY drug_concept_id
)
SELECT
  uc.domain,
  CAST(c.concept_code AS VARCHAR) AS code,
  CAST(c.concept_name AS VARCHAR) AS name,
  COALESCE(CAST(c.concept_class_id AS VARCHAR), '') AS groupName,
  SUM(uc.event_count) AS count
FROM used_concepts uc
JOIN concept c ON c.concept_id = uc.concept_id
WHERE c.concept_code IS NOT NULL
  AND c.concept_name IS NOT NULL
GROUP BY uc.domain, c.concept_code, c.concept_name, c.concept_class_id
ORDER BY uc.domain, code, name
`;

export class OmopDuckdbRepository {
  constructor(options = {}) {
    const config = options.config || options;
    this.root = options.root || config.root || process.cwd();
    this.path = String(
      config.path || config.dbPath || config.databasePath || DEFAULT_OMOP_DUCKDB_PATH
    ).trim();
    this.loadDuckdb = options.loadDuckdb || config.loadDuckdb || (() => import('@duckdb/node-api'));
    this.connectionPromise = null;
    this.connection = null;
    this.instance = null;
    this.catalogPromise = null;
    this.getBootstrap = this.getBootstrap.bind(this);
    this.runFeasibility = this.runFeasibility.bind(this);
    this.getConceptCatalog = this.getConceptCatalog.bind(this);
    this.loadConceptCatalog = this.loadConceptCatalog.bind(this);
    this.config = this.config.bind(this);
    this.run = this.run.bind(this);
    this.close = this.close.bind(this);
  }

  async getBootstrap() {
    return {
      conceptCatalog: await this.getConceptCatalog()
    };
  }

  async runFeasibility(config) {
    const rows = await this.runQuery(buildOmopFeasibilityCountSql(config));
    return normalizeCountResult(rows[0] || {});
  }

  async getConceptCatalog() {
    if (!this.catalogPromise) {
      this.catalogPromise = this.runQuery(CONCEPT_CATALOG_SQL)
        .then((rows) => normalizeConceptCatalog(rows))
        .catch((error) => {
          this.catalogPromise = null;
          throw error;
        });
    }
    return this.catalogPromise;
  }

  async loadConceptCatalog() {
    return this.getConceptCatalog();
  }

  config() {
    return {
      dataSource: 'omop-duckdb',
      path: this.path
    };
  }

  async run(config) {
    return this.runFeasibility(config);
  }

  async close() {
    if (this.connectionPromise) {
      await this.connectionPromise;
    }
    if (this.connection?.closeSync) this.connection.closeSync();
    this.connection = null;
    this.connectionPromise = null;
    this.catalogPromise = null;
  }

  async runQuery(sql) {
    const connection = await this.getConnection();
    const result = await connection.run(sql);
    const rows = await result.getRowObjectsJson();
    return Array.isArray(rows) ? rows : [];
  }

  async getConnection() {
    if (!this.connectionPromise) {
      this.connectionPromise = this.connect().catch((error) => {
        this.connectionPromise = null;
        throw error;
      });
    }
    return this.connectionPromise;
  }

  async connect() {
    const module = await this.loadDuckdb();
    const DuckDBInstance = module.DuckDBInstance || module.default?.DuckDBInstance;
    if (!DuckDBInstance) {
      throw new Error('The @duckdb/node-api module did not expose DuckDBInstance.');
    }

    const instance = await DuckDBInstance.fromCache(this.resolvePath());
    const connection = await instance.connect();
    this.instance = instance;
    this.connection = connection;
    return connection;
  }

  resolvePath() {
    return isAbsolute(this.path) ? this.path : resolve(this.root, this.path);
  }
}

export function createOmopDuckdbRepository(options = {}) {
  return new OmopDuckdbRepository(options);
}

function normalizeConceptCatalog(rows) {
  const catalog = {
    diagnosis: [],
    lab: [],
    drug: []
  };

  for (const row of rows) {
    const domain = String(row.domain || '').toLowerCase();
    if (!catalog[domain]) continue;
    catalog[domain].push({
      code: row.code ?? '',
      name: row.name ?? '',
      groupName: row.groupName ?? '',
      count: Number(row.count || 0)
    });
  }

  return catalog;
}

function normalizeCountResult(row) {
  const indexEligibleCount = Number(row.indexEligibleCount || 0);
  const demographicCount = Number(row.demographicCount || 0);
  const inclusionCount = Number(row.inclusionCount || 0);
  const finalCount = Number(row.finalCount || 0);
  return {
    totalPatients: Number(row.totalPatients || 0),
    indexEligibleCount,
    excludedCount: Math.max(0, indexEligibleCount - finalCount),
    finalCount,
    included: [],
    rows: [],
    conceptSummary: { diagnosis: [], lab: [], drug: [] },
    attrition: [
      { label: 'Has index event (T0)', count: indexEligibleCount },
      { label: 'After demographic filters', count: demographicCount, removed: Math.max(0, indexEligibleCount - demographicCount) },
      { label: 'After inclusion condition logic', count: inclusionCount, removed: Math.max(0, demographicCount - inclusionCount) },
      { label: 'After exclusion condition logic', count: finalCount, removed: Math.max(0, inclusionCount - finalCount) }
    ]
  };
}
