import {
  FILTER_FIELDS,
  FILTER_FIELDSETS,
  conditionValuesFromTree,
  isConditionGroupActive,
  normalizeRule,
  validateConditionGroup
} from './advancedConditions.js';

const OMOP_EVENT_META = Object.freeze({
  diagnosis: {
    table: 'condition_occurrence',
    alias: 'co',
    conceptId: 'condition_concept_id',
    eventDate: 'condition_start_date',
    sourceValue: 'condition_source_value',
    numericValue: 'CAST(NULL AS DOUBLE)'
  },
  lab: {
    table: 'measurement',
    alias: 'me',
    conceptId: 'measurement_concept_id',
    eventDate: 'measurement_date',
    sourceValue: 'measurement_source_value',
    numericValue: 'TRY_CAST(me.value_as_number AS DOUBLE)'
  },
  drug: {
    table: 'drug_exposure',
    alias: 'de',
    conceptId: 'drug_concept_id',
    eventDate: 'drug_exposure_start_date',
    sourceValue: 'drug_source_value',
    numericValue: 'TRY_CAST(de.quantity AS DOUBLE)'
  }
});

const FIELD_SQL = Object.freeze({
  domain: ({ eventAlias }) => `${eventAlias}.DOMAIN`,
  code: ({ eventAlias }) => `${eventAlias}.CODE`,
  name: ({ eventAlias }) => `${eventAlias}.NAME`,
  groupName: ({ eventAlias }) => `${eventAlias}.GROUP_NAME`,
  eventDate: ({ eventAlias }) => `${eventAlias}.EVENT_DATE`,
  numericValue: ({ eventAlias }) => `${eventAlias}.NUMERIC_VALUE`,
  rawValue: ({ eventAlias }) => `${eventAlias}.RAW_VALUE`,
  patientCategory: ({ eventAlias }) => `${eventAlias}.PATIENT_CATEGORY`,
  ageAtEvent: ({ eventAlias }) => `${eventAlias}.AGE_AT_EVENT`,
  daysFromT0: ({ eventAlias, patientAlias }) => `DATE_DIFF('day', ${patientAlias}.T0_DATE, ${eventAlias}.EVENT_DATE)`
});

export function buildOmopPreviewSql(config = {}) {
  const { ctes, criterionRefs, indexRefs, normalized } = buildSqlArtifacts(config);
  const whereClauses = indexRefs.length > 0 ? buildFinalWhere(criterionRefs) : ['1 = 0'];
  const sql = [
    `WITH ${ctes.join(',\n')}`,
    'SELECT',
    '  p.PERSON_ID AS personId,',
    '  p.GENDER AS gender,',
    '  p.BIRTH_DATE AS birthDate,',
    '  p.T0_DATE AS t0Date',
    'FROM BasePatients p',
    whereClauses.length ? `WHERE ${joinWhereClauses(whereClauses)}` : ''
  ].filter(Boolean).join('\n');

  return {
    sql,
    summary: buildSummary(normalized)
  };
}

export const buildOmopSql = buildOmopPreviewSql;

export function buildOmopFeasibilityCountSql(config = {}) {
  const { ctes, indexRefs, criterionRefs } = buildSqlArtifacts(config);
  if (indexRefs.length === 0) {
    return [
      `WITH ${ctes[0]}`,
      'SELECT',
      '  (SELECT COUNT(*) FROM PersonBase) AS totalPatients,',
      '  CAST(0 AS BIGINT) AS indexEligibleCount,',
      '  CAST(0 AS BIGINT) AS demographicCount,',
      '  CAST(0 AS BIGINT) AS inclusionCount,',
      '  CAST(0 AS BIGINT) AS finalCount'
    ].join('\n');
  }
  const inclusionWhere = buildFinalWhere(criterionRefs.filter((ref) => !ref.isExclusion));
  const finalWhere = buildFinalWhere(criterionRefs);

  return [
    `WITH ${ctes.join(',\n')}`,
    'SELECT',
    '  (SELECT COUNT(*) FROM PersonBase) AS totalPatients,',
    `  (SELECT COUNT(*) FROM ${indexRefs.length ? 'IndexCohort' : 'PersonBase'}) AS indexEligibleCount,`,
    `  (SELECT COUNT(*) FROM BasePatients) AS demographicCount,`,
    `  (SELECT COUNT(*) FROM BasePatients p${inclusionWhere.length ? ` WHERE ${joinWhereClauses(inclusionWhere)}` : ''}) AS inclusionCount,`,
    `  (SELECT COUNT(*) FROM BasePatients p${finalWhere.length ? ` WHERE ${joinWhereClauses(finalWhere)}` : ''}) AS finalCount`
  ].join('\n');
}

export const buildOmopCountSql = buildOmopFeasibilityCountSql;

function normalizeConfig(config) {
  return {
    indexEvents: normalizeRules(
      config.indexEvents || (config.indexEvent ? [config.indexEvent] : []),
      FILTER_FIELDSETS.index,
      'index',
      'AND'
    ),
    indexWindow: config.indexWindow || {},
    demographics: config.demographics || {},
    inclusionCriteria: normalizeRules(config.inclusionCriteria || [], FILTER_FIELDSETS.criteria, 'criteria', 'AND'),
    exclusionCriteria: normalizeRules(config.exclusionCriteria || [], FILTER_FIELDSETS.criteria, 'criteria', 'OR')
  };
}

function normalizeRules(rules, allowedFields, legacyMode, defaultJoiner) {
  return rules
    .map((rule) => normalizeRule(rule, { allowedFields, legacyMode, defaultJoiner }))
    .filter((rule) => {
      const errors = validateConditionGroup(rule.filter, { allowedFields });
      if (errors.length > 0) throw new Error(errors[0]);
      return isConditionGroupActive(rule.filter);
    });
}

function buildSqlArtifacts(config) {
  const normalized = normalizeConfig(config || {});
  const criterionRefs = [
    ...normalized.inclusionCriteria.map((criterion) => ({ criterion, isExclusion: false })),
    ...normalized.exclusionCriteria.map((criterion) => ({ criterion, isExclusion: true }))
  ];
  const indexRefs = [];
  const ctes = [buildPersonBaseCte()];
  const hasRules = normalized.indexEvents.length > 0 || criterionRefs.length > 0;

  if (hasRules) ctes.push(buildAllEventsCte());

  for (const [index, condition] of normalized.indexEvents.entries()) {
    const cteName = `IndexRule${index + 1}`;
    ctes.push(buildIndexRuleCte(cteName, condition, normalized.indexWindow));
    indexRefs.push({ cteName, joiner: condition.joiner || 'AND' });
  }

  if (indexRefs.length > 0) ctes.push(buildIndexCohortCte(indexRefs));
  ctes.push(buildBasePatientsCte(normalized.demographics, indexRefs.length > 0));

  return { ctes, criterionRefs, indexRefs, normalized };
}

function buildPersonBaseCte() {
  return `PersonBase AS (
    SELECT
      p.person_id AS PERSON_ID,
      CASE
        WHEN p.birth_datetime IS NOT NULL THEN CAST(p.birth_datetime AS DATE)
        WHEN p.year_of_birth IS NOT NULL
          AND p.month_of_birth IS NOT NULL
          AND p.day_of_birth IS NOT NULL
        THEN MAKE_DATE(
          CAST(p.year_of_birth AS INTEGER),
          CAST(p.month_of_birth AS INTEGER),
          CAST(p.day_of_birth AS INTEGER)
        )
        ELSE NULL
      END AS BIRTH_DATE,
      COALESCE(
        NULLIF(gc.concept_name, 'No matching concept'),
        NULLIF(CAST(p.gender_source_value AS VARCHAR), ''),
        ''
      ) AS GENDER
    FROM person p
    LEFT JOIN concept gc ON gc.concept_id = p.gender_concept_id
  )`;
}

function buildAllEventsCte() {
  const unions = Object.entries(OMOP_EVENT_META)
    .map(([domain, meta]) => buildDomainEventSelect(domain, meta))
    .join('\n    UNION ALL\n');

  return `AllEvents AS (
    ${unions}
)`;
}

function buildDomainEventSelect(domain, meta) {
  const source = `CAST(${meta.alias}.${meta.sourceValue} AS VARCHAR)`;
  const eventDate = `CAST(${meta.alias}.${meta.eventDate} AS DATE)`;
  const concept = 'c';

  return `SELECT
      ${meta.alias}.person_id AS PERSON_ID,
      '${domain}' AS DOMAIN,
      ${eventDate} AS EVENT_DATE,
      ${omopCodeSql(concept, source)} AS CODE,
      ${omopNameSql(concept, source)} AS NAME,
      COALESCE(CAST(${concept}.concept_class_id AS VARCHAR), '') AS GROUP_NAME,
      ${meta.numericValue} AS NUMERIC_VALUE,
      COALESCE(NULLIF(${source}, ''), '') AS RAW_VALUE,
      ${visitCategorySql('vc')} AS PATIENT_CATEGORY,
      CAST(DATE_DIFF('year', p.BIRTH_DATE, ${eventDate}) AS DOUBLE) AS AGE_AT_EVENT
    FROM ${meta.table} ${meta.alias}
    JOIN PersonBase p ON p.PERSON_ID = ${meta.alias}.person_id
    LEFT JOIN concept ${concept} ON ${concept}.concept_id = ${meta.alias}.${meta.conceptId}
    LEFT JOIN visit_occurrence v ON v.visit_occurrence_id = ${meta.alias}.visit_occurrence_id
    LEFT JOIN concept vc ON vc.concept_id = v.visit_concept_id
    WHERE ${meta.alias}.${meta.eventDate} IS NOT NULL`.trim();
}

function omopCodeSql(conceptAlias, sourceExpression) {
  return `CASE
        WHEN ${conceptAlias}.concept_id IS NULL
          OR ${conceptAlias}.concept_id = 0
          OR LOWER(COALESCE(${conceptAlias}.concept_name, '')) = 'no matching concept'
        THEN COALESCE(NULLIF(${sourceExpression}, ''), '')
        ELSE COALESCE(NULLIF(CAST(${conceptAlias}.concept_code AS VARCHAR), ''), NULLIF(${sourceExpression}, ''), '')
      END`;
}

function omopNameSql(conceptAlias, sourceExpression) {
  return `CASE
        WHEN ${conceptAlias}.concept_id IS NULL
          OR ${conceptAlias}.concept_id = 0
          OR LOWER(COALESCE(${conceptAlias}.concept_name, '')) = 'no matching concept'
        THEN COALESCE(NULLIF(${sourceExpression}, ''), '')
        ELSE COALESCE(NULLIF(CAST(${conceptAlias}.concept_name AS VARCHAR), ''), NULLIF(${sourceExpression}, ''), '')
      END`;
}

function visitCategorySql(conceptAlias) {
  const name = `LOWER(COALESCE(CAST(${conceptAlias}.concept_name AS VARCHAR), ''))`;
  return `CASE
        WHEN ${name} LIKE '%emergency%' THEN 'ED'
        WHEN ${name} LIKE '%inpatient%' THEN 'IPD'
        WHEN ${name} LIKE '%outpatient%' OR ${name} LIKE '%office visit%' THEN 'OPD'
        ELSE COALESCE(CAST(${conceptAlias}.concept_name AS VARCHAR), '')
      END`;
}

function buildIndexRuleCte(cteName, condition, indexWindow = {}) {
  const clauses = [buildGroupSql(condition.filter, { allowedFields: FILTER_FIELDSETS.index })];
  const from = indexWindow.from ?? indexWindow.start;
  const to = indexWindow.to ?? indexWindow.end;

  if (from && to) clauses.push(`e.EVENT_DATE BETWEEN ${dateLiteral(from)} AND ${dateLiteral(to)}`);
  else if (from) clauses.push(`e.EVENT_DATE >= ${dateLiteral(from)}`);
  else if (to) clauses.push(`e.EVENT_DATE <= ${dateLiteral(to)}`);

  return `${cteName} AS (
    SELECT DISTINCT e.PERSON_ID, e.EVENT_DATE
    FROM AllEvents e
    WHERE ${clauses.join('\n      AND ')}
)`;
}

function buildIndexCohortCte(indexRefs) {
  const union = indexRefs
    .map((ref) => `SELECT PERSON_ID, EVENT_DATE FROM ${ref.cteName}`)
    .join('\n        UNION ALL\n        ');
  const logic = indexRefs.map((ref, index) => {
    const exists = `EXISTS (SELECT 1 FROM ${ref.cteName} x WHERE x.PERSON_ID = p.PERSON_ID)`;
    return index === 0 ? exists : `${ref.joiner || 'AND'} ${exists}`;
  }).join('\n      ');

  return `IndexCohort AS (
    SELECT p.PERSON_ID, MIN(i.EVENT_DATE) AS T0_DATE
    FROM PersonBase p
    JOIN (
        ${union}
    ) i ON i.PERSON_ID = p.PERSON_ID
    WHERE ${logic}
    GROUP BY p.PERSON_ID
)`;
}

function buildBasePatientsCte(demographics, hasIndexCohort) {
  const joins = hasIndexCohort ? 'JOIN IndexCohort i ON i.PERSON_ID = p.PERSON_ID' : '';
  const selectedT0 = hasIndexCohort ? ', i.T0_DATE' : ', CAST(NULL AS DATE) AS T0_DATE';
  const ageExpression = hasIndexCohort
    ? "DATE_DIFF('year', p.BIRTH_DATE, i.T0_DATE)"
    : "DATE_DIFF('year', p.BIRTH_DATE, CURRENT_DATE)";
  const clauses = [];
  const minAge = demographics.minAge ?? demographics.ageMin;
  const maxAge = demographics.maxAge ?? demographics.ageMax;

  if (hasValue(minAge)) {
    const numeric = finiteNumber(minAge);
    clauses.push(numeric === null ? '1 = 0' : `${ageExpression} >= ${numeric}`);
  }
  if (hasValue(maxAge)) {
    const numeric = finiteNumber(maxAge);
    clauses.push(numeric === null ? '1 = 0' : `${ageExpression} <= ${numeric}`);
  }
  if (demographics.sex && demographics.sex !== 'Any') {
    clauses.push(`LOWER(COALESCE(p.GENDER, '')) = LOWER(${quote(demographics.sex)})`);
  }

  return `BasePatients AS (
    SELECT p.PERSON_ID, p.BIRTH_DATE, p.GENDER${selectedT0}
    FROM PersonBase p
    ${joins}
    ${clauses.length ? `WHERE ${clauses.join('\n      AND ')}` : ''}
)`;
}

function buildFinalWhere(criterionRefs) {
  const inclusions = criterionRefs.filter((ref) => !ref.isExclusion);
  const exclusions = criterionRefs.filter((ref) => ref.isExclusion);
  const clauses = [];

  if (inclusions.length > 0) clauses.push(buildExistsExpression(inclusions));
  if (exclusions.length > 0) clauses.push(`NOT ${buildExistsExpression(exclusions)}`);
  return clauses;
}

function buildExistsExpression(refs) {
  const combined = refs.map((ref, index) => {
    const joiner = index === 0 ? '' : ` ${(ref.criterion.joiner || 'AND').toUpperCase()} `;
    return `${joiner}EXISTS (
      SELECT 1 FROM AllEvents e
      WHERE e.PERSON_ID = p.PERSON_ID
        AND ${buildGroupSql(ref.criterion.filter, { allowedFields: FILTER_FIELDSETS.criteria, patientAlias: 'p' })}
    )`;
  }).join('');

  return `(${combined})`;
}

function buildGroupSql(group, options = {}) {
  if (!group.children?.length) return '1 = 1';
  const joiner = group.logic === 'OR' ? ' OR ' : ' AND ';
  return `(${group.children.map((child) => (
    child.type === 'group'
      ? buildGroupSql(child, options)
      : buildConditionSql(child, options)
  )).join(joiner)})`;
}

function buildConditionSql(condition, options = {}) {
  const field = FILTER_FIELDS[condition.field];
  const expression = FIELD_SQL[condition.field]({
    eventAlias: options.eventAlias || 'e',
    patientAlias: options.patientAlias || 'p'
  });

  if (field.type === 'text') return textConditionSql(expression, condition.operator, condition.value);
  if (field.type === 'number') return numberConditionSql(expression, condition.operator, condition.value);
  if (field.type === 'date') return dateConditionSql(expression, condition.operator, condition.value);
  return selectConditionSql(expression, condition.operator, condition.value);
}

function textConditionSql(expression, operator, value) {
  const cast = `LOWER(COALESCE(CAST(${expression} AS VARCHAR), ''))`;
  const text = `LOWER(${quote(value)})`;

  if (operator === 'contains') return `STRPOS(${cast}, ${text}) > 0`;
  if (operator === 'does_not_contain') return `STRPOS(${cast}, ${text}) = 0`;
  if (operator === 'is') return `${cast} = ${text}`;
  if (operator === 'is_not') return `${cast} <> ${text}`;
  if (operator === 'is_empty') return `TRIM(${cast}) = ''`;
  if (operator === 'is_not_empty') return `TRIM(${cast}) <> ''`;
  if (operator === 'starts_with') return `STARTS_WITH(${cast}, ${text})`;
  if (operator === 'ends_with') return `ENDS_WITH(${cast}, ${text})`;
  return '1 = 0';
}

function numberConditionSql(expression, operator, value) {
  if (operator === 'is_empty') return `${expression} IS NULL`;
  if (operator === 'between') {
    const clauses = [];
    if (value?.from !== '' && value?.from !== undefined && value?.from !== null) {
      const from = finiteNumber(value.from);
      if (from === null) return '1 = 0';
      clauses.push(`${expression} >= ${from}`);
    }
    if (value?.to !== '' && value?.to !== undefined && value?.to !== null) {
      const to = finiteNumber(value.to);
      if (to === null) return '1 = 0';
      clauses.push(`${expression} <= ${to}`);
    }
    return clauses.length > 0 ? `(${clauses.join(' AND ')})` : '1 = 0';
  }

  const numeric = finiteNumber(value);
  if (numeric === null) return '1 = 0';
  if (operator === 'is') return `${expression} = ${numeric}`;
  if (operator === 'is_not') return `${expression} <> ${numeric}`;
  if (operator === 'greater_than') return `${expression} > ${numeric}`;
  if (operator === 'less_than') return `${expression} < ${numeric}`;
  if (operator === 'greater_than_or_equal') return `${expression} >= ${numeric}`;
  if (operator === 'less_than_or_equal') return `${expression} <= ${numeric}`;
  return '1 = 0';
}

function dateConditionSql(expression, operator, value) {
  const cast = `CAST(${expression} AS DATE)`;
  if (operator === 'today') return `${cast} = CURRENT_DATE`;
  if (operator === 'this_month') return `DATE_TRUNC('month', ${cast}) = DATE_TRUNC('month', CURRENT_DATE)`;
  if (operator === 'between') {
    const clauses = [];
    if (value?.from) clauses.push(`${cast} >= ${dateLiteral(value.from)}`);
    if (value?.to) clauses.push(`${cast} <= ${dateLiteral(value.to)}`);
    return clauses.length > 0 ? `(${clauses.join(' AND ')})` : '1 = 0';
  }
  if (!value) return '1 = 0';
  if (operator === 'exact_date') return `${cast} = ${dateLiteral(value)}`;
  if (operator === 'before') return `${cast} < ${dateLiteral(value)}`;
  if (operator === 'after') return `${cast} > ${dateLiteral(value)}`;
  if (operator === 'on_or_before') return `${cast} <= ${dateLiteral(value)}`;
  if (operator === 'on_or_after') return `${cast} >= ${dateLiteral(value)}`;
  return '1 = 0';
}

function selectConditionSql(expression, operator, value) {
  const cast = `LOWER(COALESCE(CAST(${expression} AS VARCHAR), ''))`;
  if (operator === 'is_empty') return `TRIM(${cast}) = ''`;
  if (operator === 'is') return `${cast} = LOWER(${quote(value)})`;
  if (operator === 'is_not') return `${cast} <> LOWER(${quote(value)})`;
  if (operator === 'is_any_of') return `${cast} IN (${sqlList(value || [])})`;
  if (operator === 'is_none_of') return `${cast} NOT IN (${sqlList(value || [])})`;
  return '1 = 0';
}

function buildSummary(config) {
  const parts = [];
  if (config.indexEvents.length) parts.push(`${config.indexEvents.length} T0 rule${config.indexEvents.length === 1 ? '' : 's'}`);
  if (config.inclusionCriteria.length) parts.push(`${config.inclusionCriteria.length} inclusion rule${config.inclusionCriteria.length === 1 ? '' : 's'}`);
  if (config.exclusionCriteria.length) parts.push(`${config.exclusionCriteria.length} exclusion rule${config.exclusionCriteria.length === 1 ? '' : 's'}`);

  const highlighted = [
    ...config.indexEvents.flatMap((rule) => conditionValuesFromTree(rule.filter)),
    ...config.inclusionCriteria.flatMap((rule) => conditionValuesFromTree(rule.filter)),
    ...config.exclusionCriteria.flatMap((rule) => conditionValuesFromTree(rule.filter))
  ].map((item) => item.value);
  if (highlighted.length > 0) parts.push(highlighted.slice(0, 4).join(', '));

  const minAge = config.demographics.minAge ?? config.demographics.ageMin;
  const maxAge = config.demographics.maxAge ?? config.demographics.ageMax;
  if (hasValue(minAge)) parts.push(`Age >= ${minAge}`);
  if (hasValue(maxAge)) parts.push(`Age <= ${maxAge}`);
  if (config.demographics.sex && config.demographics.sex !== 'Any') parts.push(`Sex = ${config.demographics.sex}`);

  return `Criteria: ${parts.length ? parts.join(' · ') : 'no selected criteria'}`;
}

function finiteNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function hasValue(value) {
  return value !== '' && value !== undefined && value !== null;
}

function quote(value) {
  return `'${String(value ?? '').replaceAll("'", "''")}'`;
}

function dateLiteral(value) {
  return `CAST(${quote(value)} AS DATE)`;
}

function sqlList(values) {
  return values.map((value) => `LOWER(${quote(value)})`).join(', ');
}

function joinWhereClauses(clauses) {
  return clauses.join('\nAND ');
}
