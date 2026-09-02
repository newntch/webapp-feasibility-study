import { Router } from 'express';
import { randomUUID } from 'node:crypto';
import { getCookie } from './httpHelpers.js';

export function createStorageRouter({ config, appStorage, requireUser, sessionCookieName }) {
  const router = Router();

  router.post('/audit/session', requireUser, async (request, response) => {
    const session = await appStorage.touchAuditSession({
      id: getCookie(request, sessionCookieName),
      user: request.user,
      userAgent: request.headers['user-agent'] || ''
    });
    return response.json({ session });
  });

  router.post('/audit/run', requireUser, async (request, response) => {
    const body = request.body || {};
    const run = await appStorage.createRunLog({
      id: body.id || randomUUID(),
      sessionId: getCookie(request, sessionCookieName),
      user: request.user,
      createdAt: new Date().toISOString(),
      question: body.question || '',
      indexEligibleCount: Number(body.indexEligibleCount || 0),
      finalCount: Number(body.finalCount || 0),
      excludedCount: Number(body.excludedCount || 0),
      attrition: body.attrition || [],
      selectedConcepts: body.selectedConcepts || {},
      config: body.config || {},
      sql: body.sql || '',
      dataSource: config.clinicalDataSource
    });
    return response.status(201).json({ run });
  });

  router.get('/logs', requireUser, async (request, response) => {
    const [sessions, runs] = await Promise.all([
      appStorage.listAuditSessions(request.user.id),
      appStorage.listRunLogs(request.user.id)
    ]);
    return response.json({ sessions, runs, appStorage: config.appStorage });
  });

  router.delete('/logs', requireUser, async (request, response) => {
    await appStorage.clearAuditLogs(request.user.id);
    return response.json({ ok: true });
  });

  router.get('/cohorts', requireUser, async (request, response) => {
    const cohorts = await appStorage.listSavedCohorts(request.user.id);
    return response.json({ cohorts });
  });

  router.post('/cohorts', requireUser, async (request, response) => {
    const body = request.body || {};
    const cohort = await appStorage.createSavedCohort({
      id: body.id,
      userId: request.user.id,
      name: body.name,
      config: body.config
    });
    return response.status(201).json({ cohort });
  });

  router.delete('/cohorts/:cohortId', requireUser, async (request, response) => {
    await appStorage.deleteSavedCohort(request.user.id, request.params.cohortId);
    return response.status(204).end();
  });

  return router;
}
