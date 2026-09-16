import { LocalAppStorage } from '../repositories/localAppStorage.js';
import { SqlServerAppStorage } from '../repositories/sqlServerAppStorage.js';

export function createAppStorageService(options = {}) {
  const config = options.config || {};
  const appStorage = config.appStorage || options.appStorage || 'local';

  if (appStorage === 'sqlserver') {
    return new SqlServerAppStorage({
      connectionConfig: config.sqlServer || options.sqlServer || {},
      loadMssql: options.loadMssql
    });
  }

  return new LocalAppStorage({
    root: options.root
  });
}
