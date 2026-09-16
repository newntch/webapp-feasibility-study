# Diagnosis Feasibility Study Webapp

Node.js/Express prototype for estimating clinical cohort feasibility. The local
development dataset is synthetic.

Repository: <https://github.com/Burinboo256/webapp-feasibility-study>

## Requirements

- Node.js 20 or newer
- pnpm

## Run locally

```bash
pnpm install
cp config/app.config.example.json config/app.config.json
cp data/users.example.json data/users.json
cp public/data/synthetic-clinical-data_example.json public/data/synthetic-clinical-data.json
pnpm dev
```

Open <http://127.0.0.1:4173>. The local demo account is
`researcher@example.com` / `ChangeMe123!`; replace it before using non-demo
data.

The server creates local session, OTP, saved-cohort, and audit-log files under
`data/` as needed. The config and working data files are ignored by Git.

## Commands

- `pnpm dev` — start the server at `http://localhost:4173`.
- `pnpm test` — run unit and integration tests.
- `pnpm sync-dictionary` — refresh the local master-dictionary snapshot.
- `node scripts/hash-password.mjs "new-password"` — generate a bcrypt hash.

## Documentation

- [Setup and configuration](docs/setup-and-configuration.md)
- [Deployment and storage](docs/deployment-and-storage.md)
- [Product and usage](docs/product-and-usage.md)
- [Design notes](docs/design/design-notes.md)
- [OMOP CDM adapter](docs/design/omop-cdm-adapter.md)
- [Data dictionary and references](docs/references/data-dictionary.md)
