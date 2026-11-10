-- Peran runtime API `vms_api`: LOGIN, bukan superuser, NOBYPASSRLS, hak minimal. IDEMPOTEN (aman diulang).
-- Jalankan sebagai superuser/pemilik skema pada DB sasaran (lihat deploy/PERAN-RUNTIME.md):
--   VMS_API_PASSWORD='<sandi>' psql -v ON_ERROR_STOP=1 -d <db> -f deploy/peran-runtime.sql
-- Sandi TIDAK ada di repo: dibaca dari env VMS_API_PASSWORD (dipakai saat peran dibuat atau bila diisi).
-- Opsional: -v owners=vms_migrator,vms_app  (pemilik objek yang tabel barunya otomatis diberi hak ke vms_api).
-- Tanpa -v owners, hanya current_user. Butuh psql >= 15 (\getenv).
\getenv pw VMS_API_PASSWORD
\if :{?owners}
\else
  \set owners ''
\endif
SELECT set_config('vms.owners', :'owners', false) \gset

SELECT 'CREATE ROLE vms_api LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION'
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_api') \gexec
-- Selaraskan atribut bila peran sudah ada (sandi tidak disentuh).
ALTER ROLE vms_api LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
\if :{?pw}
  SELECT format('ALTER ROLE vms_api PASSWORD %L', :'pw') WHERE :'pw' <> '' \gexec
\endif

SELECT format('GRANT CONNECT ON DATABASE %I TO vms_api', current_database()) \gexec

DO $$
DECLARE s text; o text;
BEGIN
  FOREACH s IN ARRAY ARRAY['public', 'vms'] LOOP
    CONTINUE WHEN NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = s);
    EXECUTE format('GRANT USAGE ON SCHEMA %I TO vms_api', s);
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO vms_api', s);
    EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO vms_api', s);
    -- Tabel baru milik peran yang menjalankan skrip (tanpa ini tabel baru dari Alembic tak terbaca API).
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO vms_api', s);
    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO vms_api', s);
    FOR o IN SELECT btrim(x) FROM unnest(string_to_array(current_setting('vms.owners', true), ',')) x WHERE btrim(x) <> ''
    LOOP
      CONTINUE WHEN NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = o);
      EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO vms_api', o, s);
      EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO vms_api', o, s);
    END LOOP;
  END LOOP;
END $$;
