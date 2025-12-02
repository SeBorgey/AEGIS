import logging
import os
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path


class LogManager:
    def __init__(
        self,
        base_dir: str = "runs",
        retention_days: int = 7,
        logger_name: str = "aegis",
        existing_run_dir: str = None,
        program_log_name: str = "program.log",
    ):
        self.base_dir = Path(base_dir).resolve()
        self.retention_days = int(retention_days)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        if existing_run_dir:
             self.run_dir = Path(existing_run_dir).resolve()
             if not self.run_dir.exists():
                 raise ValueError(f"Run directory not found: {existing_run_dir}")
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_name = f"run_{ts}_{os.getpid()}"
            self.run_dir = self.base_dir / run_name
            self.run_dir.mkdir(parents=True, exist_ok=True)
        
        self.logs_dir = self.run_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        self.code_dir = self.run_dir / "code"
        self.code_dir.mkdir(parents=True, exist_ok=True)

        self.program_log_path = self.logs_dir / program_log_name
        self.chat_log_path = self.logs_dir / "chat.md"
        self._setup_logger(logger_name)

        try:
            self._cleanup_old_runs()
        except Exception:
            pass

    def _setup_logger(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        for h in list(self.logger.handlers):
            self.logger.removeHandler(h)
        sh = logging.StreamHandler()
        fh = logging.FileHandler(self.program_log_path, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s %(levelname)-5s %(name)s: %(message)s")
        sh.setFormatter(fmt)
        fh.setFormatter(fmt)
        self.logger.addHandler(sh)
        self.logger.addHandler(fh)

    def _init_chat_file(self):
        with open(self.chat_log_path, "w", encoding="utf-8") as f:
            f.write("# Chat log\n\n")
            self._write_chat_session_header(f, "initial")

    def _write_chat_session_header(self, fileobj, session_name: str | None):
        now = datetime.now(timezone.utc).astimezone()
        ts = now.isoformat()
        header = f"## New chat — {ts}"
        if session_name:
            header += f" — {session_name}"
        header += "\n\n"
        fileobj.write(header)

    def start_chat(self, session_name: str = "main"):
        self.chat_log_path = self.logs_dir / f"{session_name}_chat.md"
        if not self.chat_log_path.exists():
            with open(self.chat_log_path, "w", encoding="utf-8") as f:
                f.write(f"# Chat log: {session_name}\n\n")
                self._write_chat_session_header(f, "initial")
        else:
             with open(self.chat_log_path, "a", encoding="utf-8") as f:
                self._write_chat_session_header(f, "continued")

    def append_chat(self, role: str, text: str, session_name: str = "main"):
        role = str(role)
        chat_path = self.logs_dir / f"{session_name}_chat.md"
        if not chat_path.exists():
             with open(chat_path, "w", encoding="utf-8") as f:
                f.write(f"# Chat log: {session_name}\n\n")
                self._write_chat_session_header(f, "auto-created")

        with open(chat_path, "a", encoding="utf-8") as f:
            now = datetime.now(timezone.utc).astimezone().isoformat()
            f.write(f"### {role} — {now}\n")
            f.write("```\n")
            f.write(text.rstrip() + "\n")
            f.write("```\n\n")

    def append_image(self, image_local_path: str, caption: str = "", role: str = "system", session_name: str = "main"):
        chat_path = self.logs_dir / f"{session_name}_chat.md"
        if not chat_path.exists():
             with open(chat_path, "w", encoding="utf-8") as f:
                f.write(f"# Chat log: {session_name}\n\n")
                self._write_chat_session_header(f, "auto-created")

        with open(chat_path, "a", encoding="utf-8") as f:
            now = datetime.now(timezone.utc).astimezone().isoformat()
            f.write(f"### {role} — {now}\n")
            f.write(f"![{caption}]({image_local_path})\n\n")

    def save_metadata(self, metadata: dict):
        metadata_path = self.logs_dir / "metadata.json"
        current_metadata = {}
        if metadata_path.exists():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    current_metadata = json.load(f)
            except Exception:
                pass
        
        current_metadata.update(metadata)
        
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(current_metadata, f, indent=2, ensure_ascii=False)

    def info(self, msg: str):
        self.logger.info(msg)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def exception(self, msg: str):
        self.logger.exception(msg)

    def _cleanup_old_runs(self):
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        for child in sorted(self.base_dir.iterdir()):
            if not child.is_dir():
                continue
            try:
                mtime = datetime.fromtimestamp(child.stat().st_mtime)
            except Exception:
                continue
            if mtime < cutoff:
                try:
                    shutil.rmtree(child)
                except Exception:
                    pass


def setup_logging(
    base_dir: str = "runs", retention_days: int = 7, logger_name: str = "aegis"
):
    lm = LogManager(
        base_dir=base_dir, retention_days=retention_days, logger_name=logger_name
    )
    return lm, lm.logger


# from log_manager import setup_logging
# lm, logger = setup_logging(base_dir="logs", retention_days=7)
# logger.info("Program start")
# lm.start_chat("dataset-run")
# lm.append_chat("system", "System prompt text")
# lm.append_chat("user", "User question full text")
# lm.append_chat("assistant", "Assistant full reply")
