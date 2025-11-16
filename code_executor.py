import os
import subprocess
from pathlib import Path


class CodeExecutor:
    def __init__(self, workspace_path: str):
        self.workspace = Path(workspace_path).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

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
                command, capture_output=True, text=True, check=True, encoding="utf-8"
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