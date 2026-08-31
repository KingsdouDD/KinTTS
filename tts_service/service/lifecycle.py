"""
Service lifecycle management.
Manages PID file, auto-restart, health checks.
"""

import json
import os
import signal
import subprocess
import sys
import time
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "runtime"
SERVICE_PID_FILE = RUNTIME / "service.pid"
SERVICE_JSON_FILE = RUNTIME / "service.json"


class LifecycleManager:
    def __init__(self, config: dict):
        self.config = config
        self.host = config["server"]["host"]
        self.port = config["server"]["port"]
        self.startup_timeout = config["server"]["startup_timeout"]

    def _is_port_listening(self) -> bool:
        """真正连一下端口，确认服务在响应。"""
        try:
            with socket.create_connection((self.host, self.port), timeout=2):
                return True
        except (OSError, socket.timeout):
            return False

    def is_running(self) -> bool:
        """检查服务是否真实在运行：PID存在 + 进程活着 + 端口在响应。"""
        if not SERVICE_PID_FILE.exists():
            return False
        try:
            pid = int(SERVICE_PID_FILE.read_text().strip())
        except (ValueError, OSError):
            self._cleanup_stale()
            return False

        # 检查进程是否存在
        try:
            os.kill(pid, 0)
        except OSError:
            # 进程不存在，清理残留PID文件
            self._cleanup_stale()
            return False

        # 进程在，但端口不一定在响应（可能是僵死）
        if not self._is_port_listening():
            # 端口没在监听，说明服务已经死了但进程还在，强杀
            self._force_kill(pid)
            self._cleanup_stale()
            return False

        return True

    def _force_kill(self, pid: int):
        """强杀僵死进程。"""
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

    def get_pid(self) -> int | None:
        if SERVICE_PID_FILE.exists():
            try:
                return int(SERVICE_PID_FILE.read_text().strip())
            except ValueError:
                return None
        return None

    def start(self) -> bool:
        """启动服务，发现僵死进程自动强杀重拉。"""
        import logging
        logger = logging.getLogger("qwe3-tts")

        # 如果进程存在但不响应，强杀清理
        stale_pid = self.get_pid()
        if stale_pid is not None:
            try:
                os.kill(stale_pid, 0)
            except OSError:
                pass
            else:
                if not self._is_port_listening():
                    logger.warning(f"Stale service detected (PID={stale_pid}), killing...")
                    self._force_kill(stale_pid)
                    self._cleanup_stale()

        # 启动新进程
        python_exec = sys.executable
        server_script = ROOT / "service" / "server.py"
        env = os.environ.copy()
        env["QWE3_TTS_PORT"] = str(self.port)
        env["KMP_DUPLICATE_LIB_OK"] = "TRUE"

        proc = subprocess.Popen(
            [python_exec, str(server_script)],
            env=env,
            stdout=open(ROOT / "logs" / "qwe3-tts.log", "a"),
            stderr=subprocess.STDOUT,
        )

        SERVICE_PID_FILE.write_text(str(proc.pid))
        self._write_service_json(pid=proc.pid)

        # 等待端口响应
        start = time.time()
        while time.time() - start < self.startup_timeout:
            if self._is_port_listening():
                logger.info(f"Service started, PID={proc.pid}")
                return True
            # 也检查进程是否意外退出
            if proc.poll() is not None:
                logger.error("Service process exited unexpectedly")
                break
            time.sleep(0.5)

        logger.error("Service startup timeout")
        return False

    def stop(self):
        """停止服务。"""
        pid = self.get_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        self._cleanup_stale()

    def restart(self) -> bool:
        """停止然后启动。"""
        self.stop()
        time.sleep(1)
        return self.start()

    def _cleanup_stale(self):
        SERVICE_PID_FILE.unlink(missing_ok=True)
        SERVICE_JSON_FILE.unlink(missing_ok=True)

    def _write_service_json(self, pid: int):
        SERVICE_JSON_FILE.write_text(json.dumps({
            "pid": pid,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model_loaded": False,
            "last_used_at": None,
        }, indent=2))

    def update_last_used(self):
        if SERVICE_JSON_FILE.exists():
            try:
                data = json.loads(SERVICE_JSON_FILE.read_text())
                data["last_used_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                SERVICE_JSON_FILE.write_text(json.dumps(data, indent=2))
            except Exception:
                pass
