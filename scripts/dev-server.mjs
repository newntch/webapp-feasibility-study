import { resolve } from 'node:path';
import { createExpressApp } from '../src/server/http/createExpressApp.js';
import { createFeasibilityService } from '../src/server/services/createFeasibilityService.js';
import { createAppStorageService } from '../src/server/services/createAppStorageService.js';
import { loadServerConfig } from '../src/server/config/config.js';
import { createCohortRequestDeliveryService } from '../src/server/services/cohortRequestDelivery.js';
import { createOtpDeliveryService } from '../src/server/services/otpDelivery.js';

const root = resolve(process.cwd());
const config = await loadServerConfig({ root });
const allowConsoleFallbackOnSmtpFailure = isLocalDevSmtpFallbackEnabled(config);

const app = createExpressApp({
  root,
  config,
  appStorage: createAppStorageService({ root, config }),
  feasibilityService: createFeasibilityService({ root, config }),
  otpDelivery: createOtpDeliveryService({
    smtp: config.smtp,
    allowConsoleFallbackOnSmtpFailure
  }),
  cohortRequestDelivery: createCohortRequestDeliveryService({
    smtp: config.smtp,
    allowConsoleFallbackOnSmtpFailure
  })
});

app.listen(config.server.port, config.server.host, () => {
  console.log(`Cohort feasibility app: http://${config.server.host}:${config.server.port}`);
});

function isLocalDevSmtpFallbackEnabled(appConfig) {
  return ['127.0.0.1', 'localhost', '::1'].includes(String(appConfig.server.host || '').toLowerCase())
    || appConfig.appStorage === 'local';
}
