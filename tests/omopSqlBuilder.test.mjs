import assert from 'node:assert/strict';
import test from 'node:test';
import { createCondition, createConditionGroup } from '../src/advancedConditions.js';
import { buildOmopFeasibilityCountSql, buildOmopPreviewSql } from '../src/omopSqlBuilder.js';

function rule(children, joiner = 'AND') {
  return {
    joiner,
    filter: createConditionGroup({ logic: 'AND', children })
  };
}

function condition(field, operator, value) {
  return createCondition({ field, operator, value });
}

test('OMOP SQL maps the three clinical domains and preserves cohort CTE stages', () => {
  const sql = buildOmopFeasibilityCountSql({
    indexEvents: [rule([
      condition('domain', 'is', 'diagnosis'),
      createConditionGroup({
        logic: 'OR',
        children: [
          condition('code', 'is', '59621000'),
          condition('code', 'is', '55822004')
        ]
      })
    ])],
    indexWindow: { type: 'calendar', from: '2020-01-01', to: '2023-12-31' },
    demographics: { minAge: 18, maxAge: 75, sex: 'Female' },
    inclusionCriteria: [rule([
      condition('domain', 'is', 'lab'),
      condition('code', 'is', '4548-4'),
      condition('numericValue', 'greater_than_or_equal', '7'),
      condition('daysFromT0', 'between', { from: '0', to: '180' })
    ])],
    exclusionCriteria: [rule([
      condition('domain', 'is', 'drug'),
      condition('name', 'contains', "O'Brien")
    ])]
  });

  assert.match(sql, /^WITH PersonBase AS \(/);
  assert.match(sql, /FROM condition_occurrence/);
  assert.match(sql, /FROM measurement/);
  assert.match(sql, /FROM drug_exposure/);
  assert.match(sql, /JOIN concept/);
  assert.match(sql, /IndexRule1 AS \(/);
  assert.match(sql, /IndexCohort AS \(/);
  assert.match(sql, /BasePatients AS \(/);
  assert.match(sql, /person_id AS PERSON_ID/i);
  assert.match(sql, /DATE_DIFF\('day'/i);
  assert.match(sql, /EVENT_DATE BETWEEN/);
  assert.match(sql, /2020-01-01/);
  assert.match(sql, /NUMERIC_VALUE >= 7/);
  assert.match(sql, /EXISTS \(/);
  assert.match(sql, /NOT\s+\(?EXISTS \(/);
  assert.match(sql, /O''Brien/);
  assert.match(sql, /AS totalPatients/);
  assert.match(sql, /AS indexEligibleCount/);
  assert.match(sql, /AS demographicCount/);
  assert.match(sql, /AS inclusionCount/);
  assert.match(sql, /AS finalCount/);
});

test('OMOP preview SQL applies relative timing and demographic filters at T0', () => {
  const { sql, summary } = buildOmopPreviewSql({
    indexEvents: [rule([
      condition('domain', 'is', 'lab'),
      condition('code', 'is', '8480-6')
    ])],
    indexWindow: { from: '2022-01-01', to: '2022-12-31' },
    demographics: { minAge: 40, maxAge: '', sex: 'Male' },
    inclusionCriteria: [rule([
      condition('domain', 'is', 'diagnosis'),
      condition('daysFromT0', 'between', { from: '0', to: '30' })
    ])],
    exclusionCriteria: []
  });

  assert.match(sql, /DATE_DIFF\('day', p\.T0_DATE, e\.EVENT_DATE\)/i);
  assert.match(sql, /DATE_DIFF\('year', p\.BIRTH_DATE, i\.T0_DATE\) >= 40/i);
  assert.match(sql, /GENDER/i);
  assert.match(sql, /PERSON_ID/i);
  assert.match(summary, /1 T0 rule/);
  assert.match(summary, /1 inclusion rule/);
});

test('OMOP SQL supports calendar date operators and empty values', () => {
  const sql = buildOmopFeasibilityCountSql({
    indexEvents: [rule([
      condition('domain', 'is', 'diagnosis'),
      condition('eventDate', 'on_or_after', '2021-05-01'),
      condition('rawValue', 'is_empty', null)
    ])],
    indexWindow: {},
    demographics: {},
    inclusionCriteria: [],
    exclusionCriteria: []
  });

  assert.match(sql, /CAST\(e\.EVENT_DATE AS DATE\) >=/i);
  assert.match(sql, /TRIM\(/i);
  assert.doesNotMatch(sql, /GETDATE\(\)|DATEDIFF\(YEAR/i);
});
