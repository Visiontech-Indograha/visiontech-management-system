"""
Pagar statis untuk skrip server (deploy/*.sh) dan konfigurasi web: tidak bisa dijalankan di CI, tetapi kesalahan yang
paling mahal (face-service terbuka ke publik, tanpa cadangan, kamera diblokir) harus tertangkap sebelum rilis.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
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
