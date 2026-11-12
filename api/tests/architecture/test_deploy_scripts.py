"""
Pagar statis untuk skrip server (deploy/*.sh) dan konfigurasi web: tidak bisa dijalankan di CI, tetapi kesalahan yang
paling mahal (face-service terbuka ke publik, tanpa cadangan, kamera diblokir) harus tertangkap sebelum rilis.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "deploy"
INSTALLER = DEPLOY / "pasang-face-service.sh"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash tidak tersedia")
@pytest.mark.parametrize("script", sorted(DEPLOY.glob("*.sh")), ids=lambda p: p.name)
def test_deploy_scripts_have_valid_bash_syntax(script):
    result = subprocess.run(["bash", "-n"], input=read(script).encode("utf-8"), capture_output=True, check=False)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")


def test_installer_backs_up_everything_before_changing_it():
    text = read(INSTALLER)
    for backup in ("compose.yml", "api.env", "autodeploy.sh"):
        assert f'"{backup}.bak-face-$STAMP"' in text
    assert text.index("cp -p compose.yml") < text.index("python3 - <<'PY'")      # cadangan sebelum mengubah compose


def test_installer_keeps_face_service_internal_and_bounded():
    block = read(INSTALLER).split('block = """', 1)[1].split('"""', 1)[0]
    assert "ports:" not in block                      # tidak pernah dipublikasikan; hanya API yang memanggilnya
    assert "mem_limit:" in block and "restart: unless-stopped" in block
    assert "env_file: ./face.env" in block            # token tidak di compose.yml
    assert "aliases: [face]" in block                 # API memanggil http://face:8001


def test_installer_is_idempotent_and_secret_safe():
    text = read(INSTALLER)
    assert "set -euo pipefail" in text
    assert "if [ ! -f face.env ]" in text             # token tidak diganti saat dijalankan ulang
    assert "chmod 600 face.env" in text
    assert "sudah ada, dilewati" in text              # service face tidak ditambahkan dua kali
    assert "WAJIB_DAFTAR" in text and 'FACE_ENROLLMENT_REQUIRED' in text
    assert "echo \"$TOKEN\"" not in text and "echo $TOKEN" not in text   # token tidak dicetak


def test_autodeploy_copies_face_service_so_updates_ship_automatically():
    text = read(DEPLOY / "autodeploy.sh")
    assert "cp -a src/face-service face" in text


def test_caddy_allows_camera_but_not_microphone():
    caddy = read(ROOT / "web" / "Caddyfile")
    assert 'Permissions-Policy "camera=(self), microphone=(), geolocation=(self)"' in caddy


def test_face_service_image_ships_every_module_it_imports():
    dockerfile = read(ROOT / "face-service" / "Dockerfile")
    main = read(ROOT / "face-service" / "main.py")
    assert "import rules" in main
    assert "COPY main.py rules.py" in dockerfile      # tanpa rules.py kontainer gagal start
    for lib in ("libxcb1", "libgl1"):
        assert lib in dockerfile                      # pustaka sistem yang dibutuhkan OpenCV (build pernah gagal)


RELEASE_INSTALLER = DEPLOY / "pasang-rilis-apk.sh"


def test_release_installer_mounts_read_only_without_touching_compose_or_env():
    text = read(RELEASE_INSTALLER)
    assert "set -euo pipefail" in text
    assert "./rilis:/srv/rilis:ro" in text                    # API hanya membaca folder rilis
    assert "APP_RELEASE_DIR: /srv/rilis" in text
    for forbidden in ("> compose.yml", ">> api.env", "sed -i"):  # override saja; compose.yml & api.env tidak diubah
        assert forbidden not in text
    assert "bukan buatan skrip ini" in text                   # override asing tidak pernah ditimpa
    assert 'grep -q "read_only: true"' in text                # mount read-only diverifikasi lewat compose config


def test_release_script_verifies_signature_and_publishes_atomically():
    text = read(ROOT / "scripts" / "rilis-apk.sh")
    assert "set -euo pipefail" in text
    assert "--print-certs" in text and "android-release-cert.sha256" in text   # hanya kunci rilis Visiontech
    assert "versionCode='$build'" in text and "name='$PACKAGE'" in text
    assert text.index('"$out"/*.apk "$SERVER:$REMOTE_DIR/"') < text.index("latest.json.tmp")   # APK dulu
    assert "mv $REMOTE_DIR/latest.json.tmp $REMOTE_DIR/latest.json" in text    # manifest diganti atomik
    assert 'sha256sum < "$out/$dest"' in text                 # stdin: tanpa awalan "\" pada jalur Windows
    cert = read(DEPLOY / "android-release-cert.sha256")
    assert any(len(line) == 64 for line in cert.splitlines())


def test_runtime_role_switch_backs_up_never_prints_secret_and_rolls_back():
    text = read(DEPLOY / "pakai-peran-runtime.sh")
    assert "set -euo pipefail" in text
    assert "api.env.sebelum-vms_api." in text and "chmod 600" in text      # salinan rollback, tidak terbaca umum
    assert "openssl rand -hex 24" in text and "unset PW" in text             # sandi acak di server
    assert 'echo "$PW' not in text and "echo $PW" not in text                # sandi tidak pernah dicetak
    assert "MIGRATION_DATABASE_URL=" in text                                 # alembic tetap memakai pemilik
    assert '"vms_api False False"' in text                                    # API benar-benar bukan superuser
    assert text.count("restore_latest") >= 3                                  # /ready gagal / peran salah → rollback
    assert "kembalikan" in text


def test_runtime_role_sql_is_idempotent_least_privilege_and_has_no_secret():
    sql = read(DEPLOY / "peran-runtime.sql")
    assert "\\getenv pw VMS_API_PASSWORD" in sql                              # sandi dari env, bukan repo
    assert "NOSUPERUSER NOBYPASSRLS" in sql and "WHERE NOT EXISTS (SELECT 1 FROM pg_roles" in sql
    assert "ALTER DEFAULT PRIVILEGES" in sql and "ON ALL SEQUENCES" in sql
    assert "CREATE POLICY" not in sql and "PASSWORD '" not in sql


def test_runtime_role_script_has_check_apply_rollback_modes_by_pg_roles_not_alembic_name():
    text = read(DEPLOY / "pakai-peran-runtime.sh")
    assert "0024_runtime_role" not in text                                    # migrasi itu tidak pernah ada
    assert "FROM pg_roles" in text and "cek|terapkan" in text and "kembalikan" in text


def test_verify_url_script_sets_public_domain_and_keeps_rollback_copies_in_sync():
    text = read(DEPLOY / "setel-url-verifikasi.sh")
    assert "set -euo pipefail" in text
    # QR terbuka tanpa Tailscale
    assert 'DOMAIN="${1:-https://portal.visiontechindo.com}"' in text and "$DOMAIN/verify" in text
    assert "MINIO_PUBLIC_URL=$DOMAIN" in text                                 # pratinjau berkas lewat domain portal
    assert "api.env.sebelum-url-verifikasi." in text and "chmod 600" in text
    assert "api.env.sebelum-vms_api.*" in text                                # `kembalikan` tak membawa IP lama
    assert "s.PUBLIC_VERIFY_URL" in text and "s.MINIO_PUBLIC_URL" in text     # nilai yang benar-benar dibaca API


def test_restore_drill_uses_the_real_backup_path_and_never_touches_prod():
    text = read(DEPLOY / "uji-pulih-cadangan.sh")
    assert "set -euo pipefail" in text
    assert "./backup.sh uji-pulih" in text                                    # jalur cadangan yang sama dengan cron
    assert 'get_object("vms-backups"' in text and "sha256sum" in text          # salinan MinIO yang dipulihkan
    assert "--network none" in text and "trap cleanup EXIT" in text  # DB sementara terisolasi, selalu dihapus
    assert "pg_restore" in text and "^pg_restore: error" in text               # galat pemulihan harus 0
    for forbidden in ("DROP DATABASE", "pg_restore -U \"$OWNER\" -d \"$DB\" < \"$FILE\"", "--clean"):
        assert forbidden not in text                                           # prod tidak pernah ditimpa
    assert 'docker exec -i "$DB_CT" pg_restore' not in text


def test_autodeploy_backs_off_after_a_failed_deploy_of_the_same_commit():
    """Insiden 2026-10-23..28: deploy gagal diulang tiap menit (±650/hari). Gagal → jeda; sukses → hapus penanda."""
    text = read(DEPLOY / "autodeploy.sh")
    assert 'FAILED_FILE="$BASE/.last-failed"' in text
    assert "VMS_DEPLOY_RETRY_AFTER:-900" in text
    assert 'echo "$NEW $(date +%s)" > "$FAILED_FILE"' in text   # fail() menandai
    assert 'rm -f "$FAILED_FILE"' in text                          # sukses membersihkan
    assert text.index("FAILED_FILE=") < text.index("Checkout") if "Checkout" in text else True


def test_autodeploy_rolls_back_images_when_new_containers_are_unhealthy():
    text = read(DEPLOY / "autodeploy.sh")
    assert 'docker tag "${IMG}-$c" "${IMG}-$c:rollback"' in text         # simpan sebelum build
    assert "up -d --force-recreate --no-build" in text                   # pulihkan tanpa membangun ulang
    assert "case $RC in 14|16|17|18) rollback_images || true ;; esac" in text
    # rollback hanya setelah kontainer dinyalakan: tidak untuk kegagalan checkout/build/backup/migrasi (11-13, 15)
    assert text.index("rollback_images()") > text.index("Jalankan kontainer baru")


def test_images_carry_environment_and_revision_labels():
    """Citra harus menjelaskan dirinya (layanan, lingkungan, commit) dan autodeploy mengisinya lewat build-arg."""
    root = DEPLOY.parent
    for svc, dockerfile in (("api", "api/Dockerfile"), ("web", "web/Dockerfile"), ("face", "face-service/Dockerfile")):
        text = read(root / dockerfile)
        required = ("ARG GIT_SHA", "ARG VMS_ENV", f'vms.layanan="{svc}"', "vms.lingkungan=",
                    "org.opencontainers.image.revision")
        for needle in required:
            assert needle in text, f"{dockerfile}: tidak ada {needle}"
    deploy = read(DEPLOY / "autodeploy.sh")
    assert '--build-arg "GIT_SHA=' in deploy and '--build-arg "VMS_ENV=' in deploy


def test_autodeploy_updates_itself_once_from_repo():
    text = read(DEPLOY / "autodeploy.sh")
    assert "VMS_SELF_UPDATED" in text and "bash -n" in text and "cmp -s" in text
    # pembaruan diri harus terjadi sebelum penentuan commit baru / build
    first_heavy = text.index("NEW=$(git -C src rev-parse")
    assert text.index("VMS_SELF_UPDATED") < first_heavy


def test_builds_are_serialized_across_environments():
    text = read(DEPLOY / "autodeploy.sh")
    assert "flock -w" in text and "BUILD_LOCK" in text and "compose --progress=plain build" in text


def test_port_closing_script_replaces_literally_and_verifies_the_write():
    """Insiden 29-10-2026: pola `sed` tak cocok, berkas tak berubah, tetapi skrip melapor sukses."""
    text = read(DEPLOY / "tutup-port-layanan.sh")
    assert 'sed -i "s|' not in text
    assert '${isi/"$from"/$to}' in text
    assert 'grep -qF -- "$to" "$file" || {' in text.split("cp -p", 1)[1]    # hasil tulis diverifikasi


def test_backup_scripts_support_biometric_exclusion_for_pdp():
    """B-13: dump DB mendukung opsi eksklusi data biometrik mentah (face_embedding) demi kepatuhan UU PDP."""
    for script_name in ("backup.sh", "backup-terenkripsi.sh"):
        text = read(DEPLOY / script_name)
        assert "VMS_BACKUP_EXCLUDE_BIOMETRIC" in text
        assert "--exclude-table-data='*.employee'" in text


def test_backup_minio_uses_remove_and_respects_retention():
    """B-13: mirror MinIO memakai --remove bawaan agar berkas terhapus hilang dalam retensi maks 35 hari."""
    text = read(DEPLOY / "backup-minio.sh")
    assert "retensi berkas terhapus maksimal 35 hari" in text
    assert 'VMS_MINIO_REMOVE:-1' in text
    assert 'REMOVE_OPT="--remove"' in text


def test_backup_offsite_requires_age_encryption_and_refuses_plain_dumps():
    """B-13: cadangan ke luar server wajib terenkripsi age dan menolak dump polos tanpa enkripsi."""
    text = read(DEPLOY / "backup-offsite.sh")
    assert "KEPATUHAN PDP: Cadangan DB yang dikirim ke luar server WAJIB terenkripsi age." in text
    assert "age -R" in text
    assert "VMS_ALLOW_UNENCRYPTED_OFFSITE" in text


def test_biometric_sanitization_script_is_present_and_safe():
    """B-13: skrip pembersihan mandiri face_embedding tabel employee tersedia dan aman."""
    text = read(DEPLOY / "sanitasi-dump-biometrik.sh")
    assert "set -euo pipefail" in text
    assert "UPDATE employee SET face_embedding = NULL" in text
    assert "--network none" in text

