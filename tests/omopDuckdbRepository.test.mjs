import assert from 'node:assert/strict';
import test from 'node:test';
import { OmopDuckdbRepository } from '../src/server/omopDuckdbRepository.js';

function makeRepository() {
  const calls = [];
  let closed = false;
  const connection = {
    async run(sql) {
      calls.push(sql);
      if (/concept_catalog/i.test(sql)) {
        return {
          async getRowObjectsJson() {
            return [
              { domain: 'diagnosis', code: '59621000', name: 'Essential hypertension', groupName: 'Clinical Finding', count: '4' },
              { domain: 'lab', code: '8480-6', name: 'Systolic blood pressure', groupName: 'Observable Entity', count: '2' }
            ];
          }
        };
      }
      return {
        async getRowObjectsJson() {
          return [{
            totalPatients: '6731',
            indexEligibleCount: '10',
            demographicCount: '8',
            inclusionCount: '6',
            finalCount: '5'
          }];
        }
      };
    },
    closeSync() {
      closed = true;
    }
  };
  const instance = {
    async connect() {
      return connection;
    }
  };

  return {
    repository: new OmopDuckdbRepository({
      path: 'data/test.omop.duckdb',
      loadDuckdb: async () => ({
        DuckDBInstance: {
          async fromCache() {
            return instance;
          }
        }
      })
    }),
    calls,
    isClosed: () => closed
  };
}

test('OMOP DuckDB repository executes counts, normalizes bootstrap concepts, and closes', async () => {
  const { repository, calls, isClosed } = makeRepository();

  const result = await repository.runFeasibility({ indexEvents: [] });
  assert.equal(result.totalPatients, 6731);
  assert.equal(result.indexEligibleCount, 10);
  assert.equal(result.finalCount, 5);
  assert.equal(result.excludedCount, 5);
  assert.match(calls[0], /FROM person/i);

  const catalog = await repository.getConceptCatalog();
  assert.deepEqual(catalog, {
    diagnosis: [{ code: '59621000', name: 'Essential hypertension', groupName: 'Clinical Finding', count: 4 }],
    lab: [{ code: '8480-6', name: 'Systolic blood pressure', groupName: 'Observable Entity', count: 2 }],
    drug: []
  });
  assert.match(calls[1], /concept_catalog/i);

  assert.deepEqual(repository.config(), {
    dataSource: 'omop-duckdb',
    path: 'data/test.omop.duckdb'
  });

  await repository.close();
  assert.equal(isClosed(), true);
});
