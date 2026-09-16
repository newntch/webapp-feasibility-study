# Deployment and storage

## Server deployment

Login, OTP, Google OAuth, and protected audit pages require the Express server
started by `scripts/dev-server.mjs`; do not deploy the project as static files
only.

The app can run on a Node-capable host such as Render, Railway, Fly.io, Azure
App Service, AWS Elastic Beanstalk, a VM, or an internal hospital server.

Typical deployment steps:

1. Deploy the repository to a Node-capable host.
2. Run `pnpm install` during the build.
3. Start with `pnpm dev` or `node scripts/dev-server.mjs`.
4. Create `config/app.config.json` from
   `config/app.config.example.json`, or provide equivalent environment
   variables.
5. Set `HOST` or `PORT` when the platform supplies them dynamically.
6. Configure the Google OAuth redirect URL to match the public app URL.
7. Configure SMTP so OTP emails are delivered.
8. Replace demo users and passwords before exposing the app.

Example cloud start command:

```bash
HOST=0.0.0.0 PORT=4173 pnpm dev
```

Example production-oriented settings in `config/app.config.json`:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 4173,
    "cookieSecure": true
  },
  "auth": {
    "google": {
      "redirectUri": "https://your-domain.example/api/auth/google/callback",
      "allowedEmails": [
        "researcher1@example.com",
        "researcher2@example.com"
      ]
    }
  },
  "smtp": {
    "host": "smtp.example.com",
    "port": 587,
    "secure": false,
    "user": "cohort-lens@example.com",
    "pass": "your-smtp-password",
    "from": "Cohort Lens <cohort-lens@example.com>"
  }
}
```

Keep secrets out of Git. See [Setup and configuration](setup-and-configuration.md)
for the full configuration and environment-variable reference.

## Data source and application storage

Clinical feasibility data and application persistence use independent switches.

### Local JSON mode

```json
{
  "clinicalDataSource": "json",
  "appStorage": "local"
}
```

This is the checked-in default. Feasibility runs use the synthetic JSON data,
while users, sessions, pending OTPs, saved cohorts, and audit logs use files
under `data/`.

### SQL Server mode

```json
{
  "clinicalDataSource": "sqlserver",
  "appStorage": "sqlserver",
  "sqlServer": {
    "server": "db.example.com",
    "port": 1433,
    "database": "cohort_lens",
    "user": "cohort_lens_app",
    "password": "replace-me",
    "options": {
      "encrypt": true,
      "trustServerCertificate": false
    }
  }
}
```

The `mssql` driver is required for SQL Server mode. Run the SQL initialization
artifact in `database/sql/initial-setup.sql` against the target database.
Review all table and column mappings before using real clinical data.

### OMOP DuckDB mode

```json
{
  "clinicalDataSource": "omop-duckdb",
  "omopDuckdb": {
    "path": "data/omop/ehrshot_omop/ehrshot_omop.duckdb"
  }
}
```

The OMOP adapter maps the cohort-builder fields to `person`,
`condition_occurrence`, `measurement`, and `drug_exposure`, resolving standard
codes and names through `concept`. It derives T0 from the earliest matching
index event, applies demographic filters at T0, and evaluates inclusion and
exclusion rules with correlated `EXISTS` predicates. `daysFromT0` uses
DuckDB's `DATE_DIFF('day', ...)`.

Visit concepts are mapped to OPD, IPD, or ED when their concept names indicate
outpatient, inpatient, or emergency care. Other visit concept names are
retained. See the [OMOP CDM adapter notes](design/omop-cdm-adapter.md) for
field mappings and query behavior.

The checked-in EHRShot OMOP file is synthetic/de-identified research data for
local validation. Do not place identifiable clinical data in this repository.

### Scaling notes

- Local session records are stored in `data/user-sessions.json`; SQL mode uses
  shared SQL Server session tables.
- Local saved cohorts and audit logs are server-local JSON files.
- SQL mode stores saved cohorts and audit logs in shared SQL Server tables.
- Multi-instance deployments need shared session storage and shared SQL-backed
  application storage.
- JSON user storage is suitable for a local prototype, but not for concurrent
  multi-instance cloud deployments.

## Stop the development server

Find the process listening on the default port:

```bash
lsof -nP -iTCP:4173 -sTCP:LISTEN
```

Stop it with the PID from the output:

```bash
kill <PID>
```

Use `kill -9 <PID>` only if the process does not stop normally.
