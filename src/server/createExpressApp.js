import { join } from 'node:path';
import express from 'express';
import { createAuthRouter } from './authRoutes.js';
import { createFeasibilityRouter } from './feasibilityRoutes.js';
import { createSessionHelpers } from './sessionMiddleware.js';
import { createStorageRouter } from './storageRoutes.js';

const BROWSER_SOURCE_MODULES = new Set([
  'advancedConditions.js',
  'cohortEngine.js',
  'filterBuilderBehavior.js',
  'filterBuilderDefaults.js',
  'masterDictionary.js',
  'omopSqlBuilder.js',
  'sqlBuilder.js'
]);

export function createExpressApp({
  root,
  config,
  appStorage,
  feasibilityService,
  otpDelivery,
  cohortRequestDelivery,
  fetchImpl = fetch
}) {
  const app = express();
  const sessions = createSessionHelpers({ config, appStorage });

  app.disable('x-powered-by');
  app.use((request, response, next) => {
    response.set('cache-control', 'no-store');
    next();
  });
  app.use(express.json({ limit: 1_000_000 }));

  app.use('/api/auth', createAuthRouter({
    config,
    appStorage,
    otpDelivery,
    fetchImpl,
    sessions
  }));
  app.use('/api', createFeasibilityRouter({
    config,
    feasibilityService,
    cohortRequestDelivery,
    requireUser: sessions.requireUser
  }));
  app.use('/api', createStorageRouter({
    config,
    appStorage,
    requireUser: sessions.requireUser,
    sessionCookieName: sessions.cookieName
  }));
  app.use('/api', (request, response) => {
    response.status(404).json({ error: 'API route not found' });
  });

  app.get('/src/:moduleName', (request, response, next) => {
    const { moduleName } = request.params;
    if (!BROWSER_SOURCE_MODULES.has(moduleName)) return next();
    return response.sendFile(join(root, 'src', moduleName), (error) => {
      if (error) next(error);
    });
  });
  app.use(express.static(join(root, 'public'), {
    dotfiles: 'deny',
    etag: false,
    fallthrough: true,
    index: 'index.html',
    lastModified: false
  }));

  app.use((request, response) => {
    response.status(404).type('text').send('Not found');
  });

  app.use((error, request, response, next) => {
    if (response.headersSent) return next(error);
    if (error?.type === 'entity.too.large') {
      return response.status(413).json({ error: 'JSON request body exceeds the 1 MB limit.' });
    }
    if (error instanceof SyntaxError && error?.type === 'entity.parse.failed') {
      return response.status(400).json({ error: 'Malformed JSON request body.' });
    }
    console.error(error);
    return response.status(500).json({ error: 'Internal server error.' });
  });

  return app;
}
