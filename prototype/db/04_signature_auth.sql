-- =============================================================================
-- Visiontech VMS · Berkas 4 dari 5: tanda tangan digital ber-QR dan sesi JWT
--
-- Dua hal yang dijaga ketat di sini:
--   1. Kunci privat TIDAK PERNAH masuk basis data. Penandatanganan dilakukan di
--      KMS/HSM; basis data hanya menyimpan kunci publik, tanda tangan, dan bukti.
--   2. Token (QR maupun refresh) hanya disimpan sebagai hash. Nilai mentahnya
--      hanya ada pada kode QR atau pada perangkat pengguna.
-- =============================================================================
SET search_path = vms, public;

CREATE TYPE key_purpose AS ENUM ('DOCUMENT_SIGNATURE','JWT_ACCESS');
CREATE TYPE signature_role AS ENUM ('ISSUER','ACCEPTOR','WITNESS','APPROVER');
CREATE TYPE signature_state AS ENUM ('VALID','REVOKED','KEY_EXPIRED','DOCUMENT_CHANGED','UNKNOWN');
CREATE TYPE session_state AS ENUM ('ACTIVE','ROTATED','REVOKED','EXPIRED');

-- -----------------------------------------------------------------------------
-- Kunci kriptografi. Satu baris = satu pasangan kunci; yang disimpan hanya
-- bagian publik dan rujukan ke KMS. Rotasi dilakukan dengan menambah baris baru.
-- -----------------------------------------------------------------------------
CREATE TABLE signing_key (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  kid             text NOT NULL UNIQUE,        -- dicantumkan pada JWT header / berkas verifikasi
  purpose         key_purpose NOT NULL,
  algorithm       text NOT NULL DEFAULT 'Ed25519' CHECK (algorithm IN ('Ed25519','ES256','RS256')),
  public_key      bytea NOT NULL,
  kms_key_ref     text NOT NULL,               -- mis. arn:aws:kms:...  atau URI Vault
  valid_from      timestamptz NOT NULL DEFAULT now(),
  valid_to        timestamptz,                 -- rotasi terjadwal (disarankan 90 hari)
  revoked_at      timestamptz,
  revoked_reason  text,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX signing_key_live_idx ON signing_key (organization_id, purpose)
  WHERE revoked_at IS NULL;
COMMENT ON TABLE signing_key IS 'Hanya kunci publik. Kunci privat berada di KMS/HSM dan tidak pernah disalin ke basis data.';

-- -----------------------------------------------------------------------------
-- Nomor seri tanda tangan: berurutan per organisasi per tahun, dialokasikan
-- secara atomik supaya tidak pernah ada nomor kembar atau nomor bolong.
-- -----------------------------------------------------------------------------
CREATE TABLE signature_serial_counter (
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  year            integer NOT NULL,
  last_value      bigint NOT NULL DEFAULT 0,
  PRIMARY KEY (organization_id, year)
);

CREATE OR REPLACE FUNCTION next_signature_serial(p_org uuid, p_prefix text DEFAULT 'VTI')
RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_year integer := extract(year FROM now())::integer; v_next bigint;
BEGIN
  INSERT INTO signature_serial_counter (organization_id, year, last_value)
  VALUES (p_org, v_year, 1)
  ON CONFLICT (organization_id, year) DO UPDATE SET last_value = signature_serial_counter.last_value + 1
  RETURNING last_value INTO v_next;
  RETURN format('%s/%s/%s', p_prefix, v_year, lpad(v_next::text, 6, '0'));
END $$;

-- -----------------------------------------------------------------------------
-- Tanda tangan digital pada dokumen.
-- Nilai yang dipindai dari QR mengambil datanya dari sini: nama penandatangan,
-- nomor seri, jabatan saat menandatangani, nomor dokumen, dan waktu.
-- Kolom snapshot (signer_name/position/unit) sengaja disalin agar hasil verifikasi
-- tetap menampilkan keadaan saat penandatanganan, walau jabatan berubah kemudian.
-- -----------------------------------------------------------------------------
CREATE TABLE document_signature (
  id                uuid PRIMARY KEY DEFAULT new_id(),
  organization_id   uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  serial_number     text NOT NULL,
  signable_type     text NOT NULL DEFAULT 'plan_document'
                      CHECK (signable_type IN ('plan_document','final_report','employee_document','incident_report')),
  signable_id       uuid NOT NULL,
  plan_document_id  uuid REFERENCES plan_document(id),   -- diisi bila signable_type = 'plan_document'
  document_number   text NOT NULL,
  document_title    text NOT NULL,
  document_sha256   bytea NOT NULL,            -- isi persis yang ditandatangani
  signer_employee_id uuid NOT NULL REFERENCES employee(id),
  signer_name       text NOT NULL,             -- snapshot saat menandatangani
  signer_position   text NOT NULL,             -- snapshot jabatan
  signer_unit       text,
  signer_role       signature_role NOT NULL,
  signed_at         timestamptz NOT NULL DEFAULT now(),
  signing_key_id    uuid NOT NULL REFERENCES signing_key(id),
  signature         bytea NOT NULL,            -- hasil tanda tangan dari KMS
  signature_alg     text NOT NULL,
  signed_payload    jsonb NOT NULL,            -- payload kanonik yang ditandatangani
  revoked_at        timestamptz,
  revoked_reason    text,
  revoked_by        uuid REFERENCES employee(id),
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, serial_number),
  UNIQUE (signable_type, signable_id, signer_employee_id, signer_role)
);
CREATE INDEX document_signature_doc_idx ON document_signature (signable_type, signable_id);
CREATE INDEX document_signature_signer_idx ON document_signature (signer_employee_id, signed_at DESC);

-- Tanda tangan tidak boleh diubah. Yang boleh berubah hanya pencabutan.
CREATE OR REPLACE FUNCTION tg_signature_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.signature IS DISTINCT FROM OLD.signature
     OR NEW.document_sha256 IS DISTINCT FROM OLD.document_sha256
     OR NEW.signed_payload IS DISTINCT FROM OLD.signed_payload
     OR NEW.serial_number IS DISTINCT FROM OLD.serial_number
     OR NEW.signer_employee_id IS DISTINCT FROM OLD.signer_employee_id
     OR NEW.signed_at IS DISTINCT FROM OLD.signed_at THEN
    RAISE EXCEPTION 'Tanda tangan bersifat tetap. Cabut lalu terbitkan yang baru.'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER document_signature_immutable BEFORE UPDATE ON document_signature
  FOR EACH ROW EXECUTE FUNCTION tg_signature_immutable();
CREATE TRIGGER document_signature_audit AFTER INSERT OR UPDATE ON document_signature
  FOR EACH ROW EXECUTE FUNCTION tg_audit_row();

-- -----------------------------------------------------------------------------
-- Mencatat tanda tangan + menerbitkan QR verifikasinya dalam satu transaksi.
-- Tanda tangan dibuat di KMS oleh aplikasi, lalu diserahkan ke fungsi ini.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION register_document_signature(
  p_org uuid,
  p_signable_type text,
  p_signable_id uuid,
  p_document_number text,
  p_document_title text,
  p_document_sha256 bytea,
  p_signer_employee uuid,
  p_signer_role signature_role,
  p_signing_key uuid,
  p_signature bytea,
  p_signed_payload jsonb,
  p_issued_by uuid,
  p_valid_until timestamptz DEFAULT NULL
) RETURNS TABLE (signature_id uuid, serial_number text, qr_token_id uuid, qr_raw_token text)
LANGUAGE plpgsql AS $$
DECLARE
  v_emp employee%ROWTYPE;
  v_unit text;
  v_key signing_key%ROWTYPE;
  v_serial text;
  v_sig_id uuid;
  v_token record;
BEGIN
  SELECT * INTO v_emp FROM employee WHERE id = p_signer_employee;
  IF NOT FOUND THEN RAISE EXCEPTION 'Penandatangan tidak ditemukan.' USING ERRCODE = '23503'; END IF;
  SELECT name INTO v_unit FROM business_unit WHERE id = v_emp.unit_id;

  SELECT * INTO v_key FROM signing_key WHERE id = p_signing_key AND purpose = 'DOCUMENT_SIGNATURE';
  IF NOT FOUND THEN RAISE EXCEPTION 'Kunci penandatanganan tidak dikenal.' USING ERRCODE = '23503'; END IF;
  IF v_key.revoked_at IS NOT NULL OR (v_key.valid_to IS NOT NULL AND v_key.valid_to < now()) THEN
    RAISE EXCEPTION 'Kunci penandatanganan sudah tidak berlaku.' USING ERRCODE = '23514';
  END IF;

  v_serial := next_signature_serial(p_org);

  INSERT INTO document_signature (
    organization_id, serial_number, signable_type, signable_id,
    plan_document_id, document_number, document_title, document_sha256,
    signer_employee_id, signer_name, signer_position, signer_unit, signer_role,
    signing_key_id, signature, signature_alg, signed_payload
  ) VALUES (
    p_org, v_serial, p_signable_type, p_signable_id,
    CASE WHEN p_signable_type = 'plan_document' THEN p_signable_id END,
    p_document_number, p_document_title, p_document_sha256,
    p_signer_employee, v_emp.full_name, v_emp.position, v_unit, p_signer_role,
    p_signing_key, p_signature, v_key.algorithm, p_signed_payload
  ) RETURNING id INTO v_sig_id;

  SELECT * INTO v_token FROM issue_qr_token(
    p_org, 'DOCUMENT_VERIFY', 'document_signature', v_sig_id, p_issued_by, p_valid_until, NULL, NULL, NULL);

  RETURN QUERY SELECT v_sig_id, v_serial, v_token.token_id, v_token.raw_token;
END $$;

-- -----------------------------------------------------------------------------
-- Verifikasi publik. Inilah yang tampil ketika QR dipindai.
-- Hanya mengembalikan data yang memang perlu dilihat pemverifikasi.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION verify_signature_qr(
  p_raw_token text,
  p_scanned_by uuid DEFAULT NULL,
  p_location geography DEFAULT NULL,
  p_device text DEFAULT NULL
) RETURNS TABLE (
  state           signature_state,
  serial_number   text,
  signer_name     text,
  signer_position text,
  signer_unit     text,
  signer_role     signature_role,
  document_number text,
  document_title  text,
  signed_at       timestamptz,
  key_id          text,
  algorithm       text,
  document_sha256_hex text,
  note            text
) LANGUAGE plpgsql AS $$
DECLARE
  v_token qr_token%ROWTYPE;
  v_sig   document_signature%ROWTYPE;
  v_key   signing_key%ROWTYPE;
  v_current_hash bytea;
  v_state signature_state := 'UNKNOWN';
  v_note  text;
  v_scan_result qr_scan_result := 'UNKNOWN_TOKEN';
BEGIN
  SELECT * INTO v_token FROM qr_token
   WHERE token_sha256 = digest(p_raw_token, 'sha256') AND purpose = 'DOCUMENT_VERIFY';

  IF FOUND THEN
    SELECT * INTO v_sig FROM document_signature WHERE id = v_token.subject_id;
    SELECT * INTO v_key FROM signing_key WHERE id = v_sig.signing_key_id;

    IF v_token.revoked_at IS NOT NULL OR v_sig.revoked_at IS NOT NULL THEN
      v_state := 'REVOKED';
      v_note := COALESCE(v_sig.revoked_reason, v_token.revoked_reason, 'Tanda tangan dicabut.');
      v_scan_result := 'REVOKED';
    ELSE
      v_scan_result := 'VALID';
      -- Dokumen yang ditandatangani harus masih sama persis dengan saat ditandatangani.
      IF v_sig.signable_type = 'plan_document' THEN
        SELECT snapshot_sha256 INTO v_current_hash FROM plan_document WHERE id = v_sig.signable_id;
        IF v_current_hash IS DISTINCT FROM v_sig.document_sha256 THEN
          v_state := 'DOCUMENT_CHANGED';
          v_note := 'Isi dokumen berbeda dengan yang ditandatangani. Jangan dipercaya.';
        END IF;
      END IF;

      IF v_state = 'UNKNOWN' THEN
        IF v_key.revoked_at IS NOT NULL THEN
          v_state := 'KEY_EXPIRED';
          v_note := 'Kunci penandatanganan telah dicabut; tanda tangan lama tetap tercatat.';
        ELSE
          v_state := 'VALID';
          v_note := 'Tanda tangan sah dan dokumen tidak berubah sejak ditandatangani.';
        END IF;
      END IF;
    END IF;
  ELSE
    v_note := 'Kode QR tidak dikenal.';
  END IF;

  INSERT INTO qr_scan (qr_token_id, scanned_by, result, location, device_label)
  VALUES (v_token.id, p_scanned_by, v_scan_result, p_location, p_device);

  IF v_scan_result = 'VALID' THEN
    UPDATE qr_token SET scan_count = scan_count + 1 WHERE id = v_token.id;
  END IF;

  RETURN QUERY SELECT v_state, v_sig.serial_number, v_sig.signer_name, v_sig.signer_position,
                      v_sig.signer_unit, v_sig.signer_role, v_sig.document_number, v_sig.document_title,
                      v_sig.signed_at, v_key.kid, v_sig.signature_alg,
                      encode(v_sig.document_sha256, 'hex'), v_note;
END $$;

-- Tampilan ringkas untuk halaman verifikasi publik (tanpa data pribadi lain).
CREATE OR REPLACE VIEW v_signature_public AS
SELECT s.serial_number, s.signer_name, s.signer_position, s.signer_unit, s.signer_role,
       s.document_number, s.document_title, s.signed_at,
       encode(s.document_sha256,'hex') AS document_sha256_hex,
       k.kid, s.signature_alg,
       (s.revoked_at IS NOT NULL) AS is_revoked
FROM document_signature s
JOIN signing_key k ON k.id = s.signing_key_id;

-- =============================================================================
-- Sesi JWT
--   Access token  : JWT pendek (10 menit), ditandatangani EdDSA, tidak disimpan.
--   Refresh token : nilai acak 32 byte, HANYA hash-nya disimpan, berotasi tiap
--                   pemakaian, dan punya deteksi pemakaian ulang (reuse detection).
-- =============================================================================
CREATE TABLE user_session (
  id              uuid PRIMARY KEY DEFAULT new_id(),
  organization_id uuid NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  user_id         uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  family_id       uuid NOT NULL,               -- satu rantai rotasi = satu perangkat
  refresh_sha256  bytea NOT NULL UNIQUE,
  device_label    text,
  device_fingerprint text,
  ip_address      inet,
  user_agent      text,
  state           session_state NOT NULL DEFAULT 'ACTIVE',
  issued_at       timestamptz NOT NULL DEFAULT now(),
  last_used_at    timestamptz,
  expires_at      timestamptz NOT NULL,
  rotated_to      uuid REFERENCES user_session(id),
  revoked_at      timestamptz,
  revoked_reason  text
);
CREATE INDEX user_session_user_idx ON user_session (user_id, state);
CREATE INDEX user_session_family_idx ON user_session (family_id);
CREATE INDEX user_session_expiry_idx ON user_session (expires_at) WHERE state = 'ACTIVE';

CREATE TABLE login_attempt (
  id           uuid PRIMARY KEY DEFAULT new_id(),
  login        citext NOT NULL,
  ip_address   inet,
  successful   boolean NOT NULL,
  reason       text,
  attempted_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX login_attempt_recent_idx ON login_attempt (login, attempted_at DESC);
CREATE INDEX login_attempt_ip_idx ON login_attempt (ip_address, attempted_at DESC);

-- Terbitkan sesi baru; pemanggil menyimpan refresh token mentah di perangkat.
CREATE OR REPLACE FUNCTION issue_session(
  p_org uuid, p_user uuid, p_device text, p_fingerprint text,
  p_ip inet, p_agent text, p_lifetime interval DEFAULT interval '14 days'
) RETURNS TABLE (session_id uuid, family_id uuid, refresh_token text, expires_at timestamptz)
LANGUAGE plpgsql AS $$
DECLARE v_raw text; v_family uuid := new_id(); v_id uuid; v_exp timestamptz := now() + p_lifetime;
BEGIN
  v_raw := encode(gen_random_bytes(32), 'base64');
  INSERT INTO user_session (organization_id, user_id, family_id, refresh_sha256, device_label,
                            device_fingerprint, ip_address, user_agent, expires_at)
  VALUES (p_org, p_user, v_family, digest(v_raw, 'sha256'), p_device, p_fingerprint, p_ip, p_agent, v_exp)
  RETURNING id INTO v_id;
  RETURN QUERY SELECT v_id, v_family, v_raw, v_exp;
END $$;

-- Rotasi refresh token. Bila token lama dipakai ulang (tanda pencurian),
-- seluruh rantai perangkat itu dicabut sekaligus.
CREATE OR REPLACE FUNCTION rotate_session(
  p_raw_refresh text, p_ip inet DEFAULT NULL, p_agent text DEFAULT NULL
) RETURNS TABLE (session_id uuid, user_id uuid, refresh_token text, expires_at timestamptz, reused boolean)
LANGUAGE plpgsql AS $$
DECLARE v_old user_session%ROWTYPE; v_raw text; v_id uuid; v_exp timestamptz;
BEGIN
  SELECT * INTO v_old FROM user_session WHERE refresh_sha256 = digest(p_raw_refresh, 'sha256');

  IF NOT FOUND THEN
    RETURN QUERY SELECT NULL::uuid, NULL::uuid, NULL::text, NULL::timestamptz, false;
    RETURN;
  END IF;

  IF v_old.state <> 'ACTIVE' OR v_old.expires_at < now() THEN
    -- Token yang sudah dirotasi dipakai lagi: perlakukan sebagai pencurian sesi.
    UPDATE user_session
       SET state = 'REVOKED', revoked_at = now(), revoked_reason = 'Refresh token dipakai ulang'
     WHERE family_id = v_old.family_id AND state <> 'REVOKED';
    RETURN QUERY SELECT NULL::uuid, v_old.user_id, NULL::text, NULL::timestamptz, true;
    RETURN;
  END IF;

  v_raw := encode(gen_random_bytes(32), 'base64');
  v_exp := now() + (v_old.expires_at - v_old.issued_at);
  INSERT INTO user_session (organization_id, user_id, family_id, refresh_sha256, device_label,
                            device_fingerprint, ip_address, user_agent, expires_at)
  VALUES (v_old.organization_id, v_old.user_id, v_old.family_id, digest(v_raw, 'sha256'),
          v_old.device_label, v_old.device_fingerprint, COALESCE(p_ip, v_old.ip_address),
          COALESCE(p_agent, v_old.user_agent), v_exp)
  RETURNING id INTO v_id;

  UPDATE user_session SET state = 'ROTATED', rotated_to = v_id, last_used_at = now()
   WHERE id = v_old.id;

  RETURN QUERY SELECT v_id, v_old.user_id, v_raw, v_exp, false;
END $$;

CREATE OR REPLACE FUNCTION revoke_sessions(p_user uuid, p_reason text DEFAULT 'Dicabut administrator')
RETURNS integer LANGUAGE plpgsql AS $$
DECLARE v_count integer;
BEGIN
  UPDATE user_session SET state = 'REVOKED', revoked_at = now(), revoked_reason = p_reason
   WHERE user_id = p_user AND state = 'ACTIVE';
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END $$;

-- Pembatasan percobaan masuk: 5 kegagalan dalam 15 menit mengunci sementara.
CREATE OR REPLACE FUNCTION login_is_locked(p_login citext, p_window interval DEFAULT interval '15 minutes',
                                           p_max_failures integer DEFAULT 5)
RETURNS boolean LANGUAGE sql STABLE AS $$
  SELECT count(*) >= p_max_failures
  FROM login_attempt
  WHERE login = p_login AND NOT successful AND attempted_at > now() - p_window
$$;

-- -----------------------------------------------------------------------------
-- Keamanan baris untuk tabel baru
-- -----------------------------------------------------------------------------
ALTER TABLE document_signature ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_session       ENABLE ROW LEVEL SECURITY;
ALTER TABLE signing_key        ENABLE ROW LEVEL SECURITY;

CREATE POLICY signature_visibility ON document_signature
  USING (organization_id = current_org_id());
CREATE POLICY session_visibility ON user_session
  USING (user_id = current_user_id() OR has_role('ADMIN'));
CREATE POLICY signing_key_visibility ON signing_key
  USING (organization_id = current_org_id() AND (has_role('ADMIN') OR has_role('OPS')));

GRANT SELECT, INSERT, UPDATE ON document_signature, user_session, login_attempt,
      signing_key, signature_serial_counter TO vms_app;
GRANT SELECT ON v_signature_public TO vms_readonly;
