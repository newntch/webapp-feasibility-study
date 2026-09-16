# Setup and configuration

This document contains the configuration and authentication details that are
not needed for the first local run.

## Local files

Start from the checked-in templates:

```bash
cp config/app.config.example.json config/app.config.json
cp data/users.example.json data/users.json
cp data/user-sessions.example.json data/user-sessions.json
cp data/pending-otps.example.json data/pending-otps.json
cp data/saved-cohorts.example.json data/saved-cohorts.json
cp data/feasibility-run-logs.example.json data/feasibility-run-logs.json
cp data/audit-session-logs.example.json data/audit-session-logs.json
cp public/data/synthetic-clinical-data_example.json public/data/synthetic-clinical-data.json
```

Only `config/app.config.json`, `data/users.json`, and the working synthetic
data file are needed to customize a local run. The remaining local JSON files
are created or updated by the server when local storage is used.

If `config/app.config.json` is absent, the server falls back to
`config/app.config.example.json`. If the working synthetic dataset is absent,
the feasibility service uses
`public/data/synthetic-clinical-data_example.json`. If `data/users.json` is
absent, local authentication uses `data/users.example.json`.

## Repository layout

```text
public/              Static HTML, browser assets, and synthetic browser data
src/core/            Cohort, dictionary, filter, and SQL domain logic
src/server/          Express config, HTTP setup, routes, services, and repositories
database/sql/        SQL Server initialization artifacts
tests/unit/          Core and server unit tests
tests/integration/   HTTP, UI, and database artifact contract tests
docs/design/         Current architecture and adapter notes
docs/references/     Data dictionaries and supporting reference documents
scripts/             Development and maintenance entrypoints
config/              Checked-in configuration templates
data/                Local runtime state and OMOP research datasets
temp/                Temporary working files
```

Only explicitly allowlisted domain modules are exposed under `/modules/` for
browser imports. Server implementation and configuration files are not served
as static assets.

## Configuration file

The local file is `config/app.config.json`; keep secrets and environment-specific
values there only on the local machine. Its checked-in template is
`config/app.config.example.json`.

The main settings are:

- `server.host`, `server.port`, and `server.cookieSecure`
- `auth.session`, `auth.oauthState`, and `auth.otp`
- `auth.google.clientId`, `auth.google.clientSecret`,
  `auth.google.redirectUri`, and `auth.google.allowedEmails`
- `smtp.host`, `smtp.port`, `smtp.secure`, `smtp.user`, `smtp.pass`, and
  `smtp.from`
- `clinicalDataSource` and `appStorage`
- `omopDuckdb.path`
- `sqlServer.server`, `sqlServer.port`, `sqlServer.database`,
  `sqlServer.user`, `sqlServer.password`, and `sqlServer.options`

The default local values use JSON clinical data and local JSON application
storage:

```json
{
  "clinicalDataSource": "json",
  "appStorage": "local"
}
```

## Environment variable overrides

Environment variables override the corresponding values in the config file:

| Variable | Purpose |
| --- | --- |
| `PORT` | HTTP server port |
| `HOST` | HTTP server host |
| `COOKIE_SECURE` | Enable secure session cookies |
| `CLINICAL_DATA_SOURCE` | `json`, `sqlserver`, or `omop-duckdb` |
| `APP_STORAGE` | `local` or `sqlserver` |
| `DATA_SOURCE` | Legacy alias for `CLINICAL_DATA_SOURCE` |
| `OMOP_DUCKDB_PATH` | OMOP DuckDB file path |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | Google OAuth callback URL |
| `GOOGLE_ALLOWED_EMAILS` | Comma-separated allowed email addresses |
| `SMTP_HOST` | SMTP host |
| `SMTP_PORT` | SMTP port |
| `SMTP_SECURE` | Enable TLS/secure SMTP |
| `SMTP_USER` | SMTP username |
| `SMTP_PASS` | SMTP password |
| `SMTP_FROM` | Sender address |
| `SQLSERVER_HOST` | SQL Server host |
| `SQLSERVER_PORT` | SQL Server port |
| `SQLSERVER_DATABASE` | Database name |
| `SQLSERVER_USER` | Database username |
| `SQLSERVER_PASSWORD` | Database password |
| `SQLSERVER_ENCRYPT` | Enable SQL Server encryption |
| `SQLSERVER_TRUST_SERVER_CERTIFICATE` | Trust the SQL Server certificate |

## Authentication

The cohort builder, master dictionary, and logs page require login.

### Credentials

Users are loaded from `data/users.json`, with
`data/users.example.json` as the checked-in fallback template. Passwords are
stored as bcrypt hashes in `passwordHash`.

The example user is:

```text
researcher@example.com / ChangeMe123!
```

Replace the demo account before using the app with non-demo data. Generate a
new password hash with:

```bash
node scripts/hash-password.mjs "strong-password"
```

An example credential record looks like this:

```json
{
  "id": "user-researcher-001",
  "email": "researcher@example.com",
  "name": "Demo Researcher",
  "role": "researcher",
  "passwordHash": "$2b$...",
  "active": true
}
```

The create-user flow sends an email OTP and creates the JSON user after OTP
confirmation. The forgot-password flow sends an email OTP and updates the
bcrypt password after OTP confirmation.

### Email OTP

- Configure the `smtp` values in `config/app.config.json` to send real email.
- When `smtp.host` is blank, OTPs are printed to the development server
  console for local testing.
- In local mode, SMTP delivery failures fall back to the server console and
  return a warning so development sign-up is not blocked.
- Configure SMTP before enabling self-service accounts in a cloud deployment.

### Google OAuth

Set the Google OAuth values in `config/app.config.json`. When
`auth.google.redirectUri` is blank, the server derives
`http://<host>:<port>/api/auth/google/callback` from the server settings.
Restrict prototype access with `auth.google.allowedEmails` or
`GOOGLE_ALLOWED_EMAILS`.

In Google Cloud Console:

1. Create an OAuth client for a web application.
2. Add the application origin, such as `https://your-domain.example`.
3. Add the callback, such as
   `https://your-domain.example/api/auth/google/callback`.
4. Put the client ID and secret in the config file or environment variables.

## Session behavior

Session records use the active application storage backend. Local mode stores
them in `data/user-sessions.json`; SQL Server mode stores them in the shared
application tables. Sessions remain valid until they expire or are revoked.
