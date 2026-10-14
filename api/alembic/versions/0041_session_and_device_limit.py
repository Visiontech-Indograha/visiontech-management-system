"""Batasi umur sesi 24 jam, pemisahan reuse detection, dan pembatasan maksimal 4 perangkat.

Revision ID: 0041_session_and_device_limit
Revises: 0040_drop_emp_emergency_contact
Create Date: 2026-10-14

Perubahan:
1. issue_session: default lifetime menjadi 1 hari (24 jam).
2. rotate_session:
   - Token reuse (pencurian sesi) HANYA dideteksi jika state = 'ROTATED'.
   - Jika token kedaluwarsa atau total usia family >= 24 jam, kembalikan reused = false dan sesi dicabut normal.
   - Rotasi dibatasi maksimal 24 jam sejak pertama kali family_id diterbitkan.
   - Mengembalikan kolom family_created_at agar server dapat menyertakan auth_time konsisten.
3. count_active_devices: menghitung jumlah rantai sesi unik (perangkat aktif) per akun.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0041_session_and_device_limit"
down_revision: str | None = "0040_drop_emp_emergency_contact"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Hapus fungsi rotate_session lama karena mengubah kolom return type (menambah family_created_at)
    op.execute("DROP FUNCTION IF EXISTS vms.rotate_session(text, inet, text);")

    # 2. Perbarui issue_session dengan default lifetime 1 hari
    op.execute(
        """
        CREATE OR REPLACE FUNCTION vms.issue_session(
          p_org uuid, p_user uuid, p_device text, p_fingerprint text,
          p_ip inet, p_agent text, p_lifetime interval DEFAULT interval '1 day'
        ) RETURNS TABLE (session_id uuid, family_id uuid, refresh_token text, expires_at timestamptz)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = vms, public AS $$
        DECLARE v_raw text; v_family uuid := new_id(); v_id uuid; v_exp timestamptz := now() + p_lifetime;
        BEGIN
          v_raw := encode(gen_random_bytes(32), 'base64');
          INSERT INTO vms.user_session (organization_id, user_id, family_id, refresh_sha256, device_label,
                                    device_fingerprint, ip_address, user_agent, expires_at)
          VALUES (p_org, p_user, v_family, digest(v_raw, 'sha256'), p_device, p_fingerprint, p_ip, p_agent, v_exp)
          RETURNING id INTO v_id;
          RETURN QUERY SELECT v_id, v_family, v_raw, v_exp;
        END $$;
        """
    )

    # 3. Buat rotate_session baru dengan pemisahan pencurian token vs kedaluwarsa normal & cap 24 jam
    op.execute(
        """
        CREATE OR REPLACE FUNCTION vms.rotate_session(
          p_raw_refresh text, p_ip inet DEFAULT NULL, p_agent text DEFAULT NULL
        ) RETURNS TABLE (
          session_id uuid,
          user_id uuid,
          refresh_token text,
          expires_at timestamptz,
          reused boolean,
          family_created_at timestamptz
        )
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = vms, public AS $$
        DECLARE
          v_old vms.user_session%ROWTYPE;
          v_raw text;
          v_id uuid;
          v_exp timestamptz;
          v_family_created_at timestamptz;
        BEGIN
          SELECT * INTO v_old FROM vms.user_session WHERE refresh_sha256 = digest(p_raw_refresh, 'sha256');

          IF NOT FOUND THEN
            RETURN QUERY SELECT NULL::uuid, NULL::uuid, NULL::text, NULL::timestamptz, false, NULL::timestamptz;
            RETURN;
          END IF;

          -- Cari waktu pertama kali rantai sesi (family_id) ini dibuat
          SELECT min(issued_at) INTO v_family_created_at
          FROM vms.user_session
          WHERE family_id = v_old.family_id;

          -- 1. Deteksi pencurian sesi (REUSE DETECTION):
          -- HANYA berlaku bila token yang SUDAH dirotasi dipakai lagi.
          IF v_old.state = 'ROTATED' THEN
            UPDATE vms.user_session
               SET state = 'REVOKED', revoked_at = now(), revoked_reason = 'Refresh token dipakai ulang'
             WHERE family_id = v_old.family_id AND state <> 'REVOKED';
            RETURN QUERY SELECT NULL::uuid, v_old.user_id, NULL::text, NULL::timestamptz, true, v_family_created_at;
            RETURN;
          END IF;

          -- 2. Bila token sudah dicabut (misal setelah logout normal)
          IF v_old.state = 'REVOKED' THEN
            RETURN QUERY SELECT NULL::uuid, v_old.user_id, NULL::text, NULL::timestamptz, false, v_family_created_at;
            RETURN;
          END IF;

          -- 3. Batas umur sesi: kedaluwarsa waktu normal atau sudah melebihi 24 jam sejak pertama kali login
          IF v_old.expires_at <= now()
             OR (v_family_created_at IS NOT NULL AND v_family_created_at <= now() - interval '1 day') THEN
            UPDATE vms.user_session
               SET state = 'REVOKED', revoked_at = now(), revoked_reason = 'Sesi kedaluwarsa 24 jam'
             WHERE id = v_old.id AND state = 'ACTIVE';
            RETURN QUERY SELECT NULL::uuid, v_old.user_id, NULL::text, NULL::timestamptz, false, v_family_created_at;
            RETURN;
          END IF;

          -- 4. Rotasi berhasil: terbitkan token baru, dibatasi maksimal 24 jam sejak awal sesi
          v_raw := encode(gen_random_bytes(32), 'base64');
          v_exp := LEAST(now() + (v_old.expires_at - v_old.issued_at), v_family_created_at + interval '1 day');

          INSERT INTO vms.user_session (organization_id, user_id, family_id, refresh_sha256, device_label,
                                    device_fingerprint, ip_address, user_agent, expires_at)
          VALUES (v_old.organization_id, v_old.user_id, v_old.family_id, digest(v_raw, 'sha256'),
                  v_old.device_label, v_old.device_fingerprint, COALESCE(p_ip, v_old.ip_address),
                  COALESCE(p_agent, v_old.user_agent), v_exp)
          RETURNING id INTO v_id;

          UPDATE vms.user_session SET state = 'ROTATED', rotated_to = v_id, last_used_at = now()
           WHERE id = v_old.id;

          RETURN QUERY SELECT v_id, v_old.user_id, v_raw, v_exp, false, v_family_created_at;
        END $$;
        """
    )

    # 4. Fungsi penghitung perangkat aktif (maksimal 4 perangkat per akun)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION vms.count_active_devices(p_user uuid)
        RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path = vms, public AS $$
          SELECT count(DISTINCT family_id)::integer
          FROM vms.user_session
          WHERE user_id = p_user AND state = 'ACTIVE' AND expires_at > now();
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS vms.count_active_devices(uuid);")
    op.execute("DROP FUNCTION IF EXISTS vms.rotate_session(text, inet, text);")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION vms.issue_session(
          p_org uuid, p_user uuid, p_device text, p_fingerprint text,
          p_ip inet, p_agent text, p_lifetime interval DEFAULT interval '14 days'
        ) RETURNS TABLE (session_id uuid, family_id uuid, refresh_token text, expires_at timestamptz)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = vms, public AS $$
        DECLARE v_raw text; v_family uuid := new_id(); v_id uuid; v_exp timestamptz := now() + p_lifetime;
        BEGIN
          v_raw := encode(gen_random_bytes(32), 'base64');
          INSERT INTO vms.user_session (organization_id, user_id, family_id, refresh_sha256, device_label,
                                    device_fingerprint, ip_address, user_agent, expires_at)
          VALUES (p_org, p_user, v_family, digest(v_raw, 'sha256'), p_device, p_fingerprint, p_ip, p_agent, v_exp)
          RETURNING id INTO v_id;
          RETURN QUERY SELECT v_id, v_family, v_raw, v_exp;
        END $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION vms.rotate_session(
          p_raw_refresh text, p_ip inet DEFAULT NULL, p_agent text DEFAULT NULL
        ) RETURNS TABLE (session_id uuid, user_id uuid, refresh_token text, expires_at timestamptz, reused boolean)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = vms, public AS $$
        DECLARE v_old vms.user_session%ROWTYPE; v_raw text; v_id uuid; v_exp timestamptz;
        BEGIN
          SELECT * INTO v_old FROM vms.user_session WHERE refresh_sha256 = digest(p_raw_refresh, 'sha256');

          IF NOT FOUND THEN
            RETURN QUERY SELECT NULL::uuid, NULL::uuid, NULL::text, NULL::timestamptz, false;
            RETURN;
          END IF;

          IF v_old.state <> 'ACTIVE' OR v_old.expires_at < now() THEN
            UPDATE vms.user_session
               SET state = 'REVOKED', revoked_at = now(), revoked_reason = 'Refresh token dipakai ulang'
             WHERE family_id = v_old.family_id AND state <> 'REVOKED';
            RETURN QUERY SELECT NULL::uuid, v_old.user_id, NULL::text, NULL::timestamptz, true;
            RETURN;
          END IF;

          v_raw := encode(gen_random_bytes(32), 'base64');
          v_exp := now() + (v_old.expires_at - v_old.issued_at);
          INSERT INTO vms.user_session (organization_id, user_id, family_id, refresh_sha256, device_label,
                                    device_fingerprint, ip_address, user_agent, expires_at)
          VALUES (v_old.organization_id, v_old.user_id, v_old.family_id, digest(v_raw, 'sha256'),
                  v_old.device_label, v_old.device_fingerprint, COALESCE(p_ip, v_old.ip_address),
                  COALESCE(p_agent, v_old.user_agent), v_exp)
          RETURNING id INTO v_id;

          UPDATE vms.user_session SET state = 'ROTATED', rotated_to = v_id, last_used_at = now()
           WHERE id = v_old.id;

          RETURN QUERY SELECT v_id, v_old.user_id, v_raw, v_exp, false;
        END $$;
        """
    )
