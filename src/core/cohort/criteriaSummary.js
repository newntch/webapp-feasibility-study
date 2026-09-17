import { conditionValuesFromTree } from './advancedConditions.js';

export function criteriaSummary(config) {
  const parts = [];
  const indexEvents = config.indexEvents || [];
  const inclusionCriteria = config.inclusionCriteria || [];
  const exclusionCriteria = config.exclusionCriteria || [];
  if (indexEvents.length) parts.push(`${indexEvents.length} T0 rule${indexEvents.length === 1 ? '' : 's'}`);
  if (inclusionCriteria.length) parts.push(`${inclusionCriteria.length} inclusion rule${inclusionCriteria.length === 1 ? '' : 's'}`);
  if (exclusionCriteria.length) parts.push(`${exclusionCriteria.length} exclusion rule${exclusionCriteria.length === 1 ? '' : 's'}`);
  const values = [...indexEvents, ...inclusionCriteria, ...exclusionCriteria]
    .flatMap((rule) => conditionValuesFromTree(rule.filter))
    .map((item) => item.value);
  if (values.length) parts.push(values.slice(0, 4).join(', '));
  const demographics = config.demographics || {};
  if (hasValue(demographics.minAge ?? demographics.ageMin)) parts.push(`Age >= ${demographics.minAge ?? demographics.ageMin}`);
  if (hasValue(demographics.maxAge ?? demographics.ageMax)) parts.push(`Age <= ${demographics.maxAge ?? demographics.ageMax}`);
  if (demographics.sex && demographics.sex !== 'Any') parts.push(`Sex = ${demographics.sex}`);
  return `Criteria: ${parts.length ? parts.join(' · ') : 'no selected criteria'}`;
}

function hasValue(value) {
  return value !== '' && value !== null && value !== undefined;
}
