import { Router } from 'express';

export function createFeasibilityRouter({ config, feasibilityService, cohortRequestDelivery, requireUser }) {
  const router = Router();

  router.get('/bootstrap', requireUser, async (request, response) => {
    try {
      const bootstrap = await feasibilityService.getBootstrap();
      return response.json({ ...bootstrap, appStorage: config.appStorage });
    } catch (error) {
      return response.status(500).json({ error: error.message || 'Unable to load bootstrap data.' });
    }
  });

  router.post('/feasibility/run', requireUser, async (request, response) => {
    try {
      const result = await feasibilityService.runFeasibility(request.body?.config || {});
      return response.json(result);
    } catch (error) {
      return response.status(500).json({ error: error.message || 'Unable to run feasibility query.' });
    }
  });

  router.post('/cohort-request', requireUser, async (request, response) => {
    const body = request.body || {};
    const email = String(body.email || '').trim().toLowerCase();
    const requesterName = String(body.name || '').trim();
    const requestReason = String(body.requestReason || '').trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || !requesterName || !requestReason) {
      return response.status(400).json({ error: 'Email, name-surname, and request reason are required.' });
    }

    try {
      const delivery = await cohortRequestDelivery.sendRequestEmail({
        to: email,
        requesterName,
        requestReason,
        question: String(body.question || '').trim(),
        dataSource: String(body.dataSource || config.clinicalDataSource || ''),
        indexEligibleCount: Number(body.indexEligibleCount || 0),
        finalCount: Number(body.finalCount || 0),
        excludedCount: Number(body.excludedCount || 0),
        sqlSummary: String(body.sqlSummary || '').trim(),
        attrition: Array.isArray(body.attrition) ? body.attrition : [],
        sql: String(body.sql || ''),
        workflowSvg: String(body.workflowSvg || '')
      });
      return response.json({
        ok: true,
        mode: delivery.mode,
        message: delivery.mode === 'email'
          ? `Request sent to ${email}.`
          : (delivery.warning || 'Request email was written to the server console.')
      });
    } catch (error) {
      return response.status(500).json({ error: error.message || 'Unable to send cohort request email.' });
    }
  });

  return router;
}
