"""Peran runtime vms_api non-superuser, NOBYPASSRLS, hak minimal dan default privileges.

Revision ID: v2_0038
Revises: v2_0037
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v2_0038"
down_revision: str | None = "v2_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            db_name text := current_database();
            s text;
            o text;
            known_owners text[] := ARRAY['vms_migrator', 'vms_app', 'postgres'];
        BEGIN
            -- 1. Buat peran vms_api bila belum ada (NOLOGIN), atau selaraskan atributnya
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_api') THEN
                CREATE ROLE vms_api NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
            ELSE
                ALTER ROLE vms_api NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
            END IF;

            -- 2. Hak koneksi ke basis data saat ini
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO vms_api', db_name);

            -- 3. Hak skema, tabel, dan sequence untuk public dan vms (bila ada)
            FOREACH s IN ARRAY ARRAY['public', 'vms'] LOOP
                CONTINUE WHEN NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = s);

                EXECUTE format('GRANT USAGE ON SCHEMA %I TO vms_api', s);
                EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO vms_api', s);
                EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO vms_api', s);

                -- ALTER DEFAULT PRIVILEGES untuk current_user
                EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO vms_api', s);
                EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO vms_api', s);

                -- ALTER DEFAULT PRIVILEGES untuk role pemilik lain bila ada di pg_roles
                FOREACH o IN ARRAY known_owners LOOP
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = o) THEN
                        BEGIN
                            EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO vms_api', o, s);
                            EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO vms_api', o, s);
                        EXCEPTION
                            WHEN insufficient_privilege THEN
                                NULL;
                        END;
                    END IF;
                END LOOP;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            db_name text := current_database();
            s text;
            o text;
            known_owners text[] := ARRAY['vms_migrator', 'vms_app', 'postgres'];
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vms_api') THEN
                FOREACH s IN ARRAY ARRAY['public', 'vms'] LOOP
                    CONTINUE WHEN NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = s);

                    -- Cabut default privileges untuk current_user
                    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM vms_api', s);
                    EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I REVOKE USAGE, SELECT ON SEQUENCES FROM vms_api', s);

                    -- Cabut default privileges untuk role pemilik lain bila ada
                    FOREACH o IN ARRAY known_owners LOOP
                        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = o) THEN
                            BEGIN
                                EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM vms_api', o, s);
                                EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA %I REVOKE USAGE, SELECT ON SEQUENCES FROM vms_api', o, s);
                            EXCEPTION
                                WHEN insufficient_privilege THEN
                                    NULL;
                            END;
                        END IF;
                    END LOOP;

                    -- Cabut hak pada objek yang ada
                    EXECUTE format('REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA %I FROM vms_api', s);
                    EXECUTE format('REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA %I FROM vms_api', s);
                    EXECUTE format('REVOKE USAGE ON SCHEMA %I FROM vms_api', s);
                END LOOP;

                EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM vms_api', db_name);

                -- Lepaskan objek milik peran jika ada, lalu coba hapus peran secara aman
                BEGIN
                    EXECUTE 'DROP OWNED BY vms_api CASCADE';
                EXCEPTION
                    WHEN OTHERS THEN
                        NULL;
                END;

                BEGIN
                    DROP ROLE vms_api;
                EXCEPTION
                    WHEN dependent_objects_still_exist OR object_in_use THEN
                        NULL;
                END;
            END IF;
        END $$;
        """
    )
