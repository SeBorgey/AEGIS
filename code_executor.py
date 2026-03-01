import os
import subprocess
import time
from pathlib import Path


class CodeExecutor:
    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def test_app(self, script_name: str = "app.py") -> tuple[bool, str]:
        script_path = self.workspace / script_name
        if not script_path.exists():
            return False, f"File {script_name} not found"

        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"

        process = subprocess.Popen(
            ["python", str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=str(self.workspace),
        )

        time.sleep(3)
        return_code = process.poll()

        if return_code is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            return True, "App ran successfully for 3 seconds"

        stdout, stderr = process.communicate()
        error_message = stderr or stdout or f"Process exited with code {return_code}"
        return False, error_message

    def package_to_exe(self, script_name: str = "app.py") -> tuple[bool, str]:
        script_path = self.workspace / script_name
        if not script_path.exists():
            return False, f"File {script_name} not found"

        dist_path = self.workspace / "dist"

        command = [
            "python",
            "-m",
            "PyInstaller",
            "--onefile",
            "--windowed",
            "--exclude-module",
            "PyQt6",
            "--distpath",
            str(dist_path),
            "--specpath",
            str(self.workspace),
            "--workpath",
            str(self.workspace / "build"),
            str(script_path),
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                cwd=str(self.workspace),
            )

            exe_name = f"{script_path.stem}.exe" if os.name == "nt" else script_path.stem
            exe_path = dist_path / exe_name

            if exe_path.exists():
                return True, f"Success: {exe_path.absolute()}"

            return False, f"Executable not found\n{result.stdout}\n{result.stderr}"

        except subprocess.CalledProcessError as e:
            return False, f"PyInstaller error:\n{e.stderr}"
        except Exception as e:
            return False, str(e)
