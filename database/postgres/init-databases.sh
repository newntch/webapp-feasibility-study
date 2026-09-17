#!/bin/sh
set -eu

psql -v ON_ERROR_STOP=1 --username postgres \
  --set=app_password="$APP_DB_PASSWORD" \
  --set=clinical_password="$CLINICAL_DB_PASSWORD" \
  --set=import_password="$CLINICAL_IMPORT_DB_PASSWORD" <<'SQL'
CREATE ROLE app_writer LOGIN PASSWORD :'app_password';
CREATE ROLE clinical_reader LOGIN PASSWORD :'clinical_password';
CREATE ROLE clinical_importer LOGIN PASSWORD :'import_password';
CREATE DATABASE application_db OWNER app_writer;
CREATE DATABASE clinical_db OWNER clinical_importer;
GRANT CONNECT ON DATABASE clinical_db TO clinical_reader;
SQL

psql -v ON_ERROR_STOP=1 --username postgres --dbname clinical_db <<'SQL'
GRANT USAGE ON SCHEMA public TO clinical_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE clinical_importer IN SCHEMA public
  GRANT SELECT ON TABLES TO clinical_reader;
SQL
