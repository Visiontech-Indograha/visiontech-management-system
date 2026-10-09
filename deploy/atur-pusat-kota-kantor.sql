-- Pusat kota (kategori Dalam/Luar kota absensi) + lokasi kantor — dijalankan SEKALI di prod setelah migrasi 0035.
-- Keputusan pemilik 2026-10-09: kantor pusat di Pekanbaru; titik absen > 60 km dari pusat Pekanbaru = LUAR_KOTA.
-- Absen di radius kantor mana pun (site tanpa unit) atau lokasi tugas hari itu sah otomatis.
--
-- Cara pakai (sebagai pemilik DB/operator, bukan vms_api — RLS):
--   docker exec -i vms_db_prod sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < atur-pusat-kota-kantor.sql
--
-- Aman diulang: kantor dicocokkan menurut nama (diperbarui bila ada, dibuat bila belum).
-- Koordinat kantor di bawah PERKIRAAN — sesuaikan dulu dengan titik sebenarnya (Google Maps → klik kanan → salin
-- koordinat "lat, lng"), atau perbaiki nanti lewat menu Lokasi kerja di web.
-- Skrip berhenti di ROLLBACK bila organisasi tidak tepat satu; hasilnya ditampilkan sebelum COMMIT.

\set ON_ERROR_STOP on
BEGIN;

DO $$
DECLARE
  v_org uuid;
  v_n int;
  r record;
BEGIN
  SELECT count(*) INTO v_n FROM vms.organization;
  IF v_n <> 1 THEN
    RAISE EXCEPTION 'Diharapkan tepat 1 organisasi, ada %', v_n;
  END IF;
  SELECT id INTO v_org FROM vms.organization;
  PERFORM set_config('app.organization_id', v_org::text, true);
  PERFORM set_config('app.actor_label', 'atur pusat kota & kantor (deploy/atur-pusat-kota-kantor.sql)', true);

  -- Pusat kota: Pekanbaru, radius 60 km.
  UPDATE vms.organization
     SET city_name = 'Pekanbaru',
         city_center = ST_SetSRID(ST_MakePoint(101.4478, 0.5071), 4326)::geography,
         city_radius_km = 60
   WHERE id = v_org;

  -- Kantor: (nama, alamat, lat, lng, radius absen meter). unit_id NULL = lokasi kantor.
  FOR r IN SELECT * FROM (VALUES
      ('Kantor Pusat Visiontech', 'Pekanbaru, Riau (kantor pusat)',        0.5071,  101.4478, 150),
      ('Kantor Duri',             'Duri, Mandau, Bengkalis, Riau',          1.2679,  101.1905, 150),
      ('Kantor Dumai',            'Dumai, Riau',                            1.6667,  101.4472, 150),
      ('Kantor Jakarta',          'Jl. Jend. Sudirman, Jakarta Selatan',   -6.2253,  106.8024, 150)
    ) AS t(name, address, lat, lng, radius_m)
  LOOP
    UPDATE vms.site
       SET address = r.address,
           location = ST_SetSRID(ST_MakePoint(r.lng, r.lat), 4326)::geography,
           radius_m = r.radius_m, unit_id = NULL, deleted_at = NULL
     WHERE organization_id = v_org AND name = r.name;
    IF NOT FOUND THEN
      INSERT INTO vms.site (organization_id, name, address, location, radius_m)
      VALUES (v_org, r.name, r.address, ST_SetSRID(ST_MakePoint(r.lng, r.lat), 4326)::geography, r.radius_m);
    END IF;
  END LOOP;
END $$;

-- Pemeriksaan: semua lokasi kantor + jaraknya ke pusat kota + kategori.
SELECT o.city_name, o.city_radius_km FROM vms.organization o;
SELECT s.name,
       round(ST_Y(s.location::geometry)::numeric, 5) AS lat,
       round(ST_X(s.location::geometry)::numeric, 5) AS lng,
       s.radius_m,
       round((ST_Distance(s.location, o.city_center) / 1000)::numeric, 1) AS km_dari_pusat,
       CASE WHEN ST_Distance(s.location, o.city_center) > o.city_radius_km * 1000.0
            THEN 'LUAR_KOTA' ELSE 'DALAM_KOTA' END AS kategori
FROM vms.site s JOIN vms.organization o ON o.id = s.organization_id
WHERE s.unit_id IS NULL AND s.deleted_at IS NULL
ORDER BY km_dari_pusat;

COMMIT;
