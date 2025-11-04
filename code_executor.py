import os
import re
import subprocess
import time


class CodeExecutor:
    def __init__(self, workspace_path: str = "workspace"):
        self.workspace_path = workspace_path
        os.makedirs(self.workspace_path, exist_ok=True)

    def save_code(self, code: str, filename: str = "generated_app.py") -> str:
        script_path = os.path.join(self.workspace_path, filename)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)
        return script_path

    def run_headless_test(self, script_path: str) -> tuple[bool, str]:
        max_retries = 3
        for i in range(max_retries):
            env = os.environ.copy()
            env["QT_QPA_PLATFORM"] = "offscreen"

            process = subprocess.Popen(
                ["python", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=env,
            )

            time.sleep(3)

            return_code = process.poll()

            if return_code is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                return True, "Приложение успешно запустилось и работало 3 секунды."
            else:
                stdout, stderr = process.communicate()
                error_message = (
                    stderr
                    or stdout
                    or f"Процесс завершился с кодом {return_code} без вывода."
                )

                if "ModuleNotFoundError" in stderr:
                    match = re.search(r"No module named '([^']*)'", stderr)
                    if match:
                        package_name = match.group(1)
                        print(
                            f"Обнаружен отсутствующий модуль: {package_name}. Попытка установки... ({i + 1}/{max_retries})"
                        )

                        install_process = subprocess.run(
                            ["python", "-m", "pip", "install", package_name],
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                        )

                        if install_process.returncode == 0:
                            print(
                                f"Модуль {package_name} успешно установлен. Повторный запуск..."
                            )
                            continue  # Try running the script again
                        else:
                            return (
                                False,
                                f"Не удалось установить модуль {package_name}:\n{install_process.stderr}",
                            )

                return False, error_message

        return (
            False,
            "Не удалось запустить приложение после нескольких попыток установки зависимостей.",
        )

    def package_with_pyinstaller(self, script_path: str) -> tuple[bool, str]:
        dist_path = os.path.join(self.workspace_path, "dist")

        command = [
            "python",
            "-m",
            "PyInstaller",
            "--onefile",
            "--windowed",
            "--distpath",
            dist_path,
            "--specpath",
            self.workspace_path,
            "--workpath",
            os.path.join(self.workspace_path, "build"),
            script_path,
        ]

        try:
            process = subprocess.run(
                command, capture_output=True, text=True, check=True, encoding="utf-8"
            )

            base_filename = os.path.basename(script_path).replace(".py", "")
            # На Windows PyInstaller добавляет .exe, на Linux - нет.
            exe_name = f"{base_filename}.exe" if os.name == "nt" else base_filename
            exe_path = os.path.join(dist_path, exe_name)

            if os.path.exists(exe_path):
                return (
                    True,
                    f"Приложение успешно упаковано: {os.path.abspath(exe_path)}",
                )
            else:
                return (
                    False,
                    f"Не удалось найти .exe файл. Вывод PyInstaller:\n{process.stdout}\n{process.stderr}",
                )

        except subprocess.CalledProcessError as e:
            return False, f"Ошибка PyInstaller:\n{e.stderr}"
        except Exception as e:
            return False, str(e)
