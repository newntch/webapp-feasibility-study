import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const publicUrl = new URL('../public/', import.meta.url);

async function readPublic(path) {
  return readFile(new URL(path, publicUrl), 'utf8');
}

const pageContracts = {
  'index.html': {
    ids: [
      'authStatus',
      'cohortForm',
      'indexConditionList',
      'inclusionList',
      'exclusionList',
      'finalCount',
      'workflowDiagram',
      'generatedSql',
      'requestCohortForm',
      'savedCohortSelect'
    ],
    script: '/app.js'
  },
  'dictionary.html': {
    ids: ['authStatus', 'domainTabs', 'dictionarySearch', 'dictionaryWarning', 'dictionaryResults'],
    script: '/dictionary.js'
  },
  'logs.html': {
    ids: ['authStatus', 'exportLogs', 'clearLogs', 'logSearch', 'runLogList', 'sessionLogRows'],
    script: '/logs.js'
  },
  'login.html': {
    ids: ['loginForm', 'loginStatus', 'signupForm', 'signupStatus', 'forgotForm', 'forgotStatus'],
    script: '/login.js'
  }
};

test('all product pages share the theme and preserve their browser contracts', async () => {
  for (const [file, contract] of Object.entries(pageContracts)) {
    const html = await readPublic(file);

    assert.match(html, /<link\b[^>]*href=["']\/styles\.css["'][^>]*>/i, `${file} must use the shared theme`);
    assert.match(html, new RegExp(`<script\\b[^>]*src=["']${contract.script.replace('.', '\\.')}["'][^>]*>`, 'i'), `${file} must keep its entrypoint`);

    for (const id of contract.ids) {
      assert.match(html, new RegExp(`\\bid=["']${id}["']`), `${file} must retain #${id}`);
    }
  }
});

test('application navigation preserves routes and identifies the current page', async () => {
  const routeContracts = {
    'index.html': '/',
    'dictionary.html': '/dictionary.html',
    'logs.html': '/logs.html'
  };

  for (const [file, currentRoute] of Object.entries(routeContracts)) {
    const html = await readPublic(file);
    for (const route of ['/', '/dictionary.html', '/logs.html']) {
      assert.match(html, new RegExp(`href=["']${route.replace('.', '\\.')}["']`), `${file} must link to ${route}`);
    }
    assert.match(
      html,
      new RegExp(`<a\\b(?=[^>]*href=["']${currentRoute.replace('.', '\\.')}["'])(?=[^>]*aria-current=["']page["'])[^>]*>`, 'i'),
      `${file} must identify its current navigation link`
    );
  }

  const login = await readPublic('login.html');
  assert.match(login, /href=["']\/api\/auth\/google["']/, 'the Google authentication route must remain available');
});

test('each page exposes runtime updates to assistive technology', async () => {
  for (const file of Object.keys(pageContracts)) {
    const html = await readPublic(file);
    assert.match(html, /\baria-live=["'](?:polite|assertive)["']/, `${file} needs a live status region`);
  }
});

test('shared CSS defines the clinical-neutral semantic theme', async () => {
  const css = await readPublic('styles.css');
  const tokens = {
    '--color-bg': '#f4f7f7',
    '--color-surface': '#ffffff',
    '--color-surface-subtle': '#edf3f2',
    '--color-text': '#172423',
    '--color-muted': '#5c6c6a',
    '--color-border': '#d4dfdd',
    '--color-accent': '#176b67'
  };

  assert.match(css, /@layer\s+reset\s*,\s*tokens\s*,\s*base\s*,\s*components\s*,\s*utilities\s*;/, 'CSS must declare a small, predictable layer model');
  for (const [name, value] of Object.entries(tokens)) {
    assert.match(css, new RegExp(`${name}\\s*:\\s*${value}`, 'i'), `${name} must be ${value}`);
  }
  assert.match(css, /:focus-visible\s*\{[^}]*\boutline\s*:/s, 'keyboard focus must remain visible');
  assert.match(css, /@media\s*\(prefers-reduced-motion\s*:\s*reduce\)/, 'non-essential motion must respect user preferences');
});

test('cohort workspace uses a responsive two-column layout', async () => {
  const css = await readPublic('styles.css');

  assert.match(
    css,
    /\.layout\s*\{[^}]*grid-template-columns\s*:\s*minmax\([^;]+\)\s+minmax\(/s,
    'desktop should place the builder and output stack side by side'
  );
  assert.match(
    css,
    /@media\s*\([^)]*max-width[^)]*\)\s*\{[\s\S]*?\.layout\s*\{[^}]*grid-template-columns\s*:\s*1fr/s,
    'the workspace should collapse to one column on narrower screens'
  );
});

test('theme retires decorative legacy styling and oversized general buttons', async () => {
  const css = await readPublic('styles.css');

  assert.doesNotMatch(css, /\b(?:Georgia|Times New Roman)\b/i);
  assert.doesNotMatch(css, /radial-gradient\s*\(/i);

  const generalButtonSelectors = /(?:\bbutton\b|\.primary\b|\.small\b|\.ghost\b|\.google-login\b)/;
  for (const match of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const [, selector, declarations] = match;
    if (generalButtonSelectors.test(selector)) {
      assert.doesNotMatch(declarations, /border-radius\s*:\s*(?:999(?:\.0)?px|50rem|100vmax)/i, `${selector.trim()} must not use an oversized pill radius`);
    }
  }
});

test('workflow SVG and PNG exports use the neutral teal palette', async () => {
  const app = await readPublic('app.js');

  assert.match(app, /#f4f7f7/i, 'workflow exports should use the neutral canvas background');
  assert.match(app, /#176b67/i, 'workflow exports should use the product teal accent');
  assert.doesNotMatch(app, /#fffaf0/i, 'workflow exports must not keep the legacy cream background');
});
