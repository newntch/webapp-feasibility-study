import assert from 'node:assert/strict';
import test from 'node:test';
import bcrypt from 'bcryptjs';

import {
  authenticatedHeaders,
  testUser,
  withTestServer
} from './helpers/express-app-test-harness.mjs';

test('serves the public index and browser-required shared source modules without caching', async () => {
  await withTestServer({}, async (baseUrl) => {
    const indexResponse = await fetch(`${baseUrl}/`);
    assert.equal(indexResponse.status, 200);
    assert.match(indexResponse.headers.get('content-type'), /^text\/html\b/);
    assert.equal(indexResponse.headers.get('cache-control'), 'no-store');
    assert.match(await indexResponse.text(), /<!doctype html>/i);

    const sourceResponse = await fetch(`${baseUrl}/src/cohortEngine.js`);
    assert.equal(sourceResponse.status, 200);
    assert.match(sourceResponse.headers.get('content-type'), /javascript/);
    assert.equal(sourceResponse.headers.get('cache-control'), 'no-store');
    assert.match(await sourceResponse.text(), /export/);
  });
});

test('does not expose server code or other repository files as static assets', async () => {
  await withTestServer({}, async (baseUrl) => {
    const forbiddenPaths = [
      '/src/server/config.js',
      '/config/app.config.example.json',
      '/tests/serverConfig.test.mjs',
      '/docs/design-notes.md',
      '/package.json'
    ];

    for (const path of forbiddenPaths) {
      const response = await fetch(`${baseUrl}${path}`);
      assert.equal(response.status, 404, `${path} must not be publicly readable`);
    }
  });
});

test('requires authentication for protected APIs and returns the session user contract', async () => {
  await withTestServer({}, async (baseUrl) => {
    const anonymousResponse = await fetch(`${baseUrl}/api/auth/me`);
    assert.equal(anonymousResponse.status, 401);
    assert.deepEqual(await anonymousResponse.json(), { error: 'Not authenticated' });

    const authenticatedResponse = await fetch(`${baseUrl}/api/auth/me`, {
      headers: authenticatedHeaders()
    });
    assert.equal(authenticatedResponse.status, 200);
    assert.equal(authenticatedResponse.headers.get('cache-control'), 'no-store');
    assert.deepEqual(await authenticatedResponse.json(), { user: testUser });
  });
});

test('preserves credential login and logout status and cookie contracts', async () => {
  const passwordHash = await bcrypt.hash('correct-password', 4);
  const createdSessions = [];
  const deletedSessions = [];

  await withTestServer({
    appStorage: {
      async getUserByEmail(email) {
        assert.equal(email, 'researcher@example.com');
        return {
          ...testUser,
          passwordHash,
          lastLoginAt: null
        };
      },
      async updateUser(user) {
        return user;
      },
      async createSession(session) {
        createdSessions.push(session);
        return session;
      },
      async deleteSession(sessionId) {
        deletedSessions.push(sessionId);
      }
    }
  }, async (baseUrl) => {
    const loginResponse = await fetch(`${baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        email: ' Researcher@Example.com ',
        password: 'correct-password'
      })
    });

    assert.equal(loginResponse.status, 200);
    assert.deepEqual(await loginResponse.json(), { user: testUser });
    const sessionCookie = loginResponse.headers.get('set-cookie');
    assert.match(sessionCookie, /^cohort_lens_session=[^;]+/);
    assert.match(sessionCookie, /Path=\//);
    assert.match(sessionCookie, /HttpOnly/);
    assert.match(sessionCookie, /SameSite=Lax/);
    assert.match(sessionCookie, /Max-Age=28800/);
    assert.equal(createdSessions.length, 1);
    assert.equal(createdSessions[0].userId, 'user-1');

    const logoutResponse = await fetch(`${baseUrl}/api/auth/logout`, {
      method: 'POST',
      headers: { cookie: 'cohort_lens_session=session-to-delete' }
    });

    assert.equal(logoutResponse.status, 204);
    assert.equal(await logoutResponse.text(), '');
    assert.match(logoutResponse.headers.get('set-cookie'), /^cohort_lens_session=;/);
    assert.match(logoutResponse.headers.get('set-cookie'), /Max-Age=0/);
    assert.deepEqual(deletedSessions, ['session-to-delete']);
  });
});

test('uses injected feasibility services while preserving bootstrap and run response shapes', async () => {
  const calls = [];
  await withTestServer({
    feasibilityService: {
      async getBootstrap() {
        calls.push(['bootstrap']);
        return { concepts: [{ id: 'hypertension' }] };
      },
      async runFeasibility(config) {
        calls.push(['run', config]);
        return { indexEligibleCount: 25, finalCount: 9 };
      }
    }
  }, async (baseUrl) => {
    const bootstrapResponse = await fetch(`${baseUrl}/api/bootstrap`, {
      headers: authenticatedHeaders()
    });
    assert.equal(bootstrapResponse.status, 200);
    assert.deepEqual(await bootstrapResponse.json(), {
      concepts: [{ id: 'hypertension' }],
      appStorage: 'local'
    });

    const runResponse = await fetch(`${baseUrl}/api/feasibility/run`, {
      method: 'POST',
      headers: authenticatedHeaders({ 'content-type': 'application/json' }),
      body: JSON.stringify({ config: { minimumAge: 18 } })
    });
    assert.equal(runResponse.status, 200);
    assert.deepEqual(await runResponse.json(), { indexEligibleCount: 25, finalCount: 9 });
    assert.deepEqual(calls, [['bootstrap'], ['run', { minimumAge: 18 }]]);
  });
});

test('uses injected storage for cohort listing and keeps the cohort response contract', async () => {
  const cohort = { id: 'cohort-1', name: 'Adults with hypertension' };
  const seenUserIds = [];

  await withTestServer({
    appStorage: {
      async listSavedCohorts(userId) {
        seenUserIds.push(userId);
        return [cohort];
      }
    }
  }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/cohorts`, {
      headers: authenticatedHeaders()
    });
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { cohorts: [cohort] });
    assert.deepEqual(seenUserIds, ['user-1']);
  });
});

test('returns JSON errors for unknown API routes and malformed JSON', async () => {
  await withTestServer({}, async (baseUrl) => {
    const missingResponse = await fetch(`${baseUrl}/api/not-a-route`);
    assert.equal(missingResponse.status, 404);
    assert.match(missingResponse.headers.get('content-type'), /^application\/json\b/);
    assert.deepEqual(await missingResponse.json(), { error: 'API route not found' });

    const malformedResponse = await fetch(`${baseUrl}/api/feasibility/run`, {
      method: 'POST',
      headers: authenticatedHeaders({ 'content-type': 'application/json' }),
      body: '{"config":'
    });
    assert.equal(malformedResponse.status, 400);
    assert.match(malformedResponse.headers.get('content-type'), /^application\/json\b/);
    assert.equal(typeof (await malformedResponse.json()).error, 'string');
  });
});

test('enforces the one megabyte JSON limit', async () => {
  await withTestServer({}, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/feasibility/run`, {
      method: 'POST',
      headers: authenticatedHeaders({ 'content-type': 'application/json' }),
      body: JSON.stringify({ config: { value: 'x'.repeat(1_000_001) } })
    });

    assert.equal(response.status, 413);
    assert.match(response.headers.get('content-type'), /^application\/json\b/);
    assert.equal(typeof (await response.json()).error, 'string');
  });
});

test('converts unexpected route failures into a no-store JSON 500 response', async () => {
  await withTestServer({
    appStorage: {
      async listSavedCohorts() {
        throw new Error('storage unavailable');
      }
    }
  }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/api/cohorts`, {
      headers: authenticatedHeaders()
    });

    assert.equal(response.status, 500);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.match(response.headers.get('content-type'), /^application\/json\b/);
    assert.equal(typeof (await response.json()).error, 'string');
  });
});
