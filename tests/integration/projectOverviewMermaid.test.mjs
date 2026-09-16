import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const overviewUrl = new URL('../../docs/design/project-overview.md', import.meta.url);

test('Mermaid flowchart node labels do not contain raw object braces', async () => {
  const markdown = await readFile(overviewUrl, 'utf8');
  const flowcharts = [...markdown.matchAll(/```mermaid\s*\r?\n(flowchart\b[\s\S]*?)```/g)];

  assert.ok(flowcharts.length > 0, 'project overview must contain at least one Mermaid flowchart');

  for (const [, flowchart] of flowcharts) {
    assert.doesNotMatch(
      flowchart,
      /\[[^\]\r\n]*\{[^}\r\n]*\}[^\]\r\n]*\]/,
      'wrap or escape object-like text inside square-bracket node labels so GitHub Mermaid can parse it'
    );
  }
});
