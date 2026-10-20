"""
Runner otomatis untuk validasi skema database dan backend API menggunakan Postman CLI.
Skrip ini:
1. Menyalakan FastAPI uvicorn worktree ini secara terisolasi di port VMS_POSTMAN_PORT (default 8000).
   Bila port sudah dipakai server lain, runner berhenti (kecuali VMS_POSTMAN_REUSE=1) — agar tidak
   diam-diam menguji kode checkout lain.
2. Memeriksa kesiapan sistem melalui probe /ready hingga HTTP 200.
3. Menjalankan suite pengujian Postman CLI (postman collection run).
4. Membersihkan proses server uvicorn secara andal.
"""
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
API_DIR = ROOT_DIR / "api"
PYTHON_BIN = API_DIR / ".venv" / "Scripts" / "python.exe"
COLLECTION_PATH = ROOT_DIR / "postman" / "collections" / "vms-feature-validation.collection.json"
ENVIRONMENT_PATH = ROOT_DIR / "postman" / "environments" / "vms-local.environment.json"
PORT = os.environ.get("VMS_POSTMAN_PORT", "8000")
ROOT_URL = f"http://127.0.0.1:{PORT}"

def is_server_ready(url: str = f"{ROOT_URL}/ready") -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False

def kill_process_tree(pid: int):
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            os.kill(pid, 9)
    except Exception as e:
        print(f"[WARN] Gagal menghentikan proses {pid}: {e}")

def main() -> int:
    print("=" * 70)
    print("   VMS SCHEMA & API VALIDATION SUITE — POSTMAN CLI RUNNER")
    print("=" * 70)
    
    if not COLLECTION_PATH.exists():
        print(f"[ERROR] Koleksi Postman tidak ditemukan di: {COLLECTION_PATH}")
        return 1
    if not ENVIRONMENT_PATH.exists():
        print(f"[ERROR] Environment Postman tidak ditemukan di: {ENVIRONMENT_PATH}")
        return 1

    already_running = is_server_ready()
    server_process = None
    server_log = None

    if already_running:
        if os.environ.get("VMS_POSTMAN_REUSE") != "1":
            print(f"[ERROR] Port {PORT} sudah dipakai server lain. Pakai VMS_POSTMAN_PORT=<port lain>, "
                  "atau VMS_POSTMAN_REUSE=1 bila server itu memang dari worktree ini.")
            return 1
        print(f"[INFO] Memakai server yang sudah berjalan di {ROOT_URL}/ready.")
    else:
        print("[INFO] Memulai server FastAPI uvicorn di latar belakang...")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(API_DIR)
        
        server_cmd = [
            str(PYTHON_BIN),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            PORT,
        ]
        
        # Log server ke berkas, bukan PIPE: pipa yang tidak dibaca akan penuh dan membuat uvicorn macet.
        server_log_path = Path(tempfile.gettempdir()) / "vms-postman-uvicorn.log"
        server_log = open(server_log_path, "w", encoding="utf-8")  # noqa: SIM115 - ditutup di finally
        print(f"[INFO] Log server: {server_log_path}")
        server_process = subprocess.Popen(
            server_cmd,
            cwd=str(API_DIR),
            env=env,
            stdout=server_log,
            stderr=subprocess.STDOUT,
        )
        
        print("[INFO] Menunggu server siap (health check /ready)...")
        ready = False
        start_time = time.time()
        timeout_seconds = 30
        
        while time.time() - start_time < timeout_seconds:
            if is_server_ready():
                ready = True
                print(f"[SUCCESS] Server siap dalam {time.time() - start_time:.2f} detik!")
                break
            # Cek jika proses mati lebih awal
            if server_process.poll() is not None:
                out = server_process.stdout.read() if server_process.stdout else ""
                print(f"[ERROR] Uvicorn berhenti sebelum siap dengan exit code {server_process.returncode}:\n{out}")
                return 1
            time.sleep(0.8)
            
        if not ready:
            print("[ERROR] Timeout menunggu kesiapan server /ready.")
            kill_process_tree(server_process.pid)
            return 1

    exit_code = 0
    try:
        print("\n[INFO] Menjalankan Postman CLI runner...")
        postman_cmd = (
            f'postman.cmd collection run "{COLLECTION_PATH}" -e "{ENVIRONMENT_PATH}" '
            f'--env-var "baseUrl={ROOT_URL}/api/v1" --env-var "rootUrl={ROOT_URL}"'
        )
        print(f"[CMD] {postman_cmd}\n")
        
        res = subprocess.run(
            postman_cmd,
            cwd=str(ROOT_DIR),
            shell=True,
        )
        exit_code = res.returncode
    except Exception as e:
        print(f"[ERROR] Eksekusi Postman CLI gagal: {e}")
        exit_code = 1
    finally:
        if server_process:
            print(f"\n[INFO] Menghentikan server uvicorn (PID: {server_process.pid})...")
            kill_process_tree(server_process.pid)
            print("[INFO] Server uvicorn berhasil dimatikan secara bersih.")
        if server_log:
            server_log.close()

    return exit_code

if __name__ == "__main__":
    sys.exit(main())
