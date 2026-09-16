import assert from 'node:assert/strict';
import test from 'node:test';
import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const databaseSqlDir = fileURLToPath(new URL('../../database/sql/', import.meta.url));
const initialSetupPath = join(databaseSqlDir, 'initial-setup.sql');

test('database/sql exposes the single named SQL initialization artifact', async () => {
  const sqlFiles = (await readdir(databaseSqlDir))
    .filter((file) => file.toLowerCase().endsWith('.sql'))
    .sort();

  assert.deepEqual(sqlFiles, ['initial-setup.sql']);
});

test('the SQL init file is documented with schema comments', async () => {
  const sqlPath = await getSingleSqlPath();
  const sql = await readFile(sqlPath, 'utf8');

  assert.match(sql, /^\s*(?:--|\/\*)/m, 'SQL file should start with a comment header');
  assert.match(sql, /initial\s+setup|bootstrap|schema/i, 'SQL file should describe its purpose');
  assert.match(sql, /clinical/i, 'SQL file should document the clinical section');
  assert.match(sql, /support|application/i, 'SQL file should document the support section');
  assert.match(sql, /saved\s+cohort/i, 'SQL file should document the saved cohort section');
  assert.match(sql, /audit|run\s+log|logging/i, 'SQL file should document the audit/run log section');
});

test('the SQL init file creates the expected clinical and backend tables', async () => {
  const sqlPath = await getSingleSqlPath();
  const sql = await readFile(sqlPath, 'utf8');

  const expectations = [
    {
      label: 'Patient_Info core patient table',
      pattern: /CREATE\s+TABLE[\s\S]*?\bPatient_Info\b[\s\S]*?\bOH_PID\b[\s\S]*?\bBIRTH_DATE\b[\s\S]*?\bSEX\b/i
    },
    {
      label: 'Diagnosis table',
      pattern: /CREATE\s+TABLE[\s\S]*?\bDiagnosis\b[\s\S]*?\bOH_PID\b[\s\S]*?\bICD_CODE\b[\s\S]*?\bVISIT_DATE\b[\s\S]*?\bDISEASE_NAME\b/i
    },
    {
      label: 'Laboratory table',
      pattern: /CREATE\s+TABLE[\s\S]*?\bLaboratory\b[\s\S]*?\bOH_PID\b[\s\S]*?\bLAB_CODE\b[\s\S]*?\bRESULT_DATE\b[\s\S]*?\bLAB_VALUE\b[\s\S]*?\bLAB_NAME\b/i
    },
    {
      label: 'Medication table',
      pattern: /CREATE\s+TABLE[\s\S]*?\bMedication\b[\s\S]*?\bOH_PID\b[\s\S]*?\bDRUG_CODE\b[\s\S]*?\bORDER_DATE\b[\s\S]*?\bDRUG_NAME\b/i
    },
    {
      label: 'Users table',
      pattern: /CREATE\s+TABLE[\s\S]*?\b(?:Users|User_Accounts|App_Users)\b[\s\S]*?\b(?:USER_ID|ID)\b[\s\S]*?\bEMAIL\b[\s\S]*?\bPASSWORD(?:_HASH)?\b[\s\S]*?\bNAME\b[\s\S]*?\bPROVIDER\b[\s\S]*?\bROLE\b/i
    },
    {
      label: 'Login/session table',
      pattern: /CREATE\s+TABLE[\s\S]*?\b(?:Login_Sessions|Sessions|Auth_Sessions|User_Sessions)\b[\s\S]*?\bSESSION_ID\b[\s\S]*?\bUSER_ID\b[\s\S]*?\bSTARTED_AT\b[\s\S]*?\bLAST_SEEN_AT\b[\s\S]*?\bPAGE_VIEWS\b[\s\S]*?\bRUN_COUNT\b[\s\S]*?\bUSER_AGENT\b/i
    },
    {
      label: 'Saved cohorts table',
      pattern: /CREATE\s+TABLE[\s\S]*?\b(?:Saved_Cohorts|Cohorts|Saved_Definitions)\b[\s\S]*?\b(?:COHORT_ID|ID)\b[\s\S]*?\bUSER_ID\b[\s\S]*?\bNAME\b[\s\S]*?\b(?:CONFIG|CONFIG_JSON)\b[\s\S]*?\bQUESTION\b[\s\S]*?\bCREATED_AT\b/i
    },
    {
      label: 'Audit/run log table',
      pattern: /CREATE\s+TABLE[\s\S]*?\b(?:Feasibility_Run_Logs|Run_Logs|Audit_Logs)\b[\s\S]*?\b(?:RUN_ID|ID)\b[\s\S]*?\bSESSION_ID\b[\s\S]*?\bUSER_ID\b[\s\S]*?\bCREATED_AT\b[\s\S]*?\bQUESTION\b[\s\S]*?\bINDEX_ELIGIBLE_COUNT\b[\s\S]*?\bFINAL_COUNT\b[\s\S]*?\bEXCLUDED_COUNT\b[\s\S]*?\bATTRITION\b[\s\S]*?\bSELECTED_CONCEPTS\b[\s\S]*?\bCONFIG\b[\s\S]*?\bSQL\b/i
    }
  ];

  for (const { label, pattern } of expectations) {
    assert.match(sql, pattern, label);
  }
});

async function getSingleSqlPath() {
  return initialSetupPath;
}
