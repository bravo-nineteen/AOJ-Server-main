from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import uvicorn


SERVER_HOST = os.getenv("AOJ_SERVER_HOST", "0.0.0.0").strip() or "0.0.0.0"
APP_HOST = os.getenv("AOJ_APP_HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = int((os.getenv("AOJ_SERVER_PORT", "8000") or "8000").strip())
HEALTH_URL = f"http://127.0.0.1:{PORT}/api/health"


def _resolve_frontend_dist() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # PyInstaller onefile extracts bundled data under _MEIPASS.
        return Path(getattr(sys, "_MEIPASS")) / "frontend" / "dist"
    return Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _find_edge_executable() -> str | None:
    candidates = [
        "msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for item in candidates:
        if item.lower().endswith(".exe") and Path(item).is_file():
            return item
        if item == "msedge.exe":
            return item
    return None


def _open_app_window(url: str) -> subprocess.Popen | None:
    edge = _find_edge_executable()
    if edge:
        try:
            return subprocess.Popen(
                [edge, f"--app={url}", "--new-window", "--disable-features=msWebOOUI,msPdfOOUI"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    # Fallback to default browser if Edge app mode is unavailable.
    try:
        os.startfile(url)  # type: ignore[attr-defined]
    except Exception:
        return None
    return None


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _wait_for_backend(timeout_seconds: float = 20.0) -> bool:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            resp = httpx.get(HEALTH_URL, timeout=1.5)
            if resp.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.35)
    return False


def _run_backend_process() -> int:
    uvicorn.run("app.main:app", host=SERVER_HOST, port=PORT, log_level="warning", access_log=False)
    return 0


def _best_lan_url(port: int) -> str:
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        probe.close()
        return f"http://{ip}:{port}"
    except Exception:
        return f"http://YOUR_PC_IP:{port}"


def main() -> int:
    if "--run-backend" in sys.argv:
        return _run_backend_process()

    frontend_dist = _resolve_frontend_dist()
    if not frontend_dist.is_dir():
        print(f"[AOJ] Frontend build not found: {frontend_dist}")
        print("[AOJ] Build frontend first with scripts/install_windows.ps1")
        return 1

    os.environ["AOJ_FRONTEND_DIST"] = str(frontend_dist)

    # If another AOJ backend is already running, attach the desktop window to it.
    should_start_server = not _is_port_open("127.0.0.1", PORT)
    backend_proc: subprocess.Popen | None = None

    if should_start_server:
        if getattr(sys, "frozen", False):
            backend_cmd = [sys.executable, "--run-backend"]
        else:
            backend_cmd = [sys.executable, str(Path(__file__).resolve()), "--run-backend"]
        backend_proc = subprocess.Popen(backend_cmd)

        if not _wait_for_backend():
            print("[AOJ] Backend did not become healthy in time.")
            if backend_proc and backend_proc.poll() is None:
                backend_proc.terminate()
            return 1

    try:
        app_url = f"http://{APP_HOST}:{PORT}"
        lan_url = _best_lan_url(PORT)
        print(f"[AOJ] Desktop app URL: {app_url}")
        print(f"[AOJ] LAN client URL: {lan_url}")
        window_proc = _open_app_window(app_url)
        if window_proc is not None:
            window_proc.wait()
        else:
            print(f"[AOJ] Opened AOJ at {app_url}. Close this console to stop backend.")
            while True:
                time.sleep(1)
    finally:
        if backend_proc is not None and backend_proc.poll() is None:
            backend_proc.terminate()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
