import { createServer } from 'node:http';

import { createExpressApp } from '../../src/server/createExpressApp.js';

export const testUser = {
  id: 'user-1',
  email: 'researcher@example.com',
  name: 'Test Researcher',
  provider: 'credentials',
  role: 'researcher'
};

export function createTestDependencies(overrides = {}) {
  const appStorage = {
    async getSession(sessionId) {
      return sessionId === 'valid-session' ? { user: testUser } : null;
    },
    async listAuditSessions() {
      return [];
    },
    async listRunLogs() {
      return [];
    },
    async listSavedCohorts() {
      return [];
    },
    ...overrides.appStorage
  };

  return {
    root: process.cwd(),
    config: {
      server: {
        host: '127.0.0.1',
        port: 4173,
        cookieSecure: false
      },
      auth: {
        session: {
          cookieName: 'cohort_lens_session',
          maxAgeSeconds: 28_800
        },
        oauthState: {
          cookieName: 'cohort_lens_oauth_state',
          maxAgeSeconds: 600
        },
        otp: {
          ttlMinutes: 10,
          maxAttempts: 5
        },
        google: {
          clientId: '',
          clientSecret: '',
          redirectUri: 'http://127.0.0.1:4173/api/auth/google/callback',
          allowedEmails: []
        }
      },
      clinicalDataSource: 'json',
      appStorage: 'local'
    },
    appStorage,
    feasibilityService: {
      async getBootstrap() {
        return { concepts: [{ id: 'concept-1' }], defaults: { question: 'test' } };
      },
      async runFeasibility(config) {
        return { finalCount: 17, config };
      },
      ...overrides.feasibilityService
    },
    otpDelivery: {
      async sendOtpEmail() {
        return { mode: 'email' };
      },
      ...overrides.otpDelivery
    },
    cohortRequestDelivery: {
      async sendRequestEmail() {
        return { mode: 'email' };
      },
      ...overrides.cohortRequestDelivery
    },
    fetchImpl: async () => {
      throw new Error('Unexpected external fetch in an HTTP contract test.');
    },
    ...overrides,
    appStorage
  };
}

export async function withTestServer(overrides, callback) {
  const app = createExpressApp(createTestDependencies(overrides));
  const server = createServer(app);

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });

  const address = server.address();
  const baseUrl = `http://127.0.0.1:${address.port}`;

  try {
    await callback(baseUrl);
  } finally {
    await new Promise((resolve, reject) => {
      server.close((error) => error ? reject(error) : resolve());
    });
  }
}

export function authenticatedHeaders(extra = {}) {
  return {
    cookie: 'cohort_lens_session=valid-session',
    ...extra
  };
}
