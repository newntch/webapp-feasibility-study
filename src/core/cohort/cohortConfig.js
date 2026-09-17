import {
  FILTER_FIELDSETS,
  createConditionGroup,
  isConditionGroupActive,
  normalizeRule
} from './advancedConditions.js';

export function defaultConfig() {
  return {
    question: '',
    indexEvents: [{ id: 'idx-blank', label: '', joiner: 'AND', filter: createConditionGroup() }],
    indexWindow: { from: '', to: '' },
    demographics: { minAge: '', maxAge: '', sex: 'Any' },
    inclusionCriteria: [],
    exclusionCriteria: []
  };
}

export function normalizeCohortConfig(config = {}) {
  return {
    question: config.question || '',
    indexEvents: normalizeRules(
      config.indexEvents || (config.indexEvent ? [config.indexEvent] : []),
      FILTER_FIELDSETS.index,
      'index',
      'AND'
    ),
    indexWindow: config.indexWindow || {},
    demographics: config.demographics || {},
    inclusionCriteria: normalizeRules(
      config.inclusionCriteria || [],
      FILTER_FIELDSETS.criteria,
      'criteria',
      'AND'
    ),
    exclusionCriteria: normalizeRules(
      config.exclusionCriteria || [],
      FILTER_FIELDSETS.criteria,
      'criteria',
      'OR'
    )
  };
}

function normalizeRules(rules, allowedFields, legacyMode, defaultJoiner) {
  return rules
    .map((rule) => normalizeRule(rule, { allowedFields, legacyMode, defaultJoiner }))
    .filter((rule) => isConditionGroupActive(rule.filter));
}
