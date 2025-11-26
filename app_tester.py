import os
import re
import time
import subprocess
from pyvirtualdisplay import Display
import pyautogui

class AppTester:
    def __init__(self, resolution=(1920, 1080)):
        self.display = Display(visible=0, size=resolution)
        self.display.start()
        
        self.wm_process = subprocess.Popen(
            ['fluxbox'],
            env=os.environ,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2)
        self.gui = pyautogui
        self.app_process = None
        self.window_id = None

    def launch(self, app_path):
        if not os.path.exists(app_path):
            raise FileNotFoundError(f"{app_path} not found")
        
        self.app_process = subprocess.Popen(
            [app_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=os.environ
        )
        self._wait_for_window()

    def _wait_for_window(self, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            try:
                wid = subprocess.check_output(
                    ['xdotool', 'getactivewindow'], 
                    env=os.environ,
                    stderr=subprocess.DEVNULL 
                ).decode().strip()
                
                if wid:
                    self.window_id = wid
                    subprocess.run(
                        ['xdotool', 'windowmove', wid, '0', '0'],
                        env=os.environ,
                        check=True,
                        stderr=subprocess.DEVNULL
                    )
                    time.sleep(0.5)
                    return
            except subprocess.CalledProcessError:
                pass
            time.sleep(0.5)
        raise TimeoutError("Application window did not appear")

    def click(self, x, y):
        if not self.window_id:
            self._wait_for_window()
            
        subprocess.run(
            [
                'xdotool', 
                'windowfocus', '--sync', self.window_id,
                'windowactivate', '--sync', self.window_id,
                'mousemove', '--sync', str(x), str(y),
                'sleep', '0.2',
                'click', '1'
            ],
            env=os.environ,
            check=True
        )

    def _get_window_geometry(self):
        if not self.window_id:
            self._wait_for_window()

        output = subprocess.check_output(
            ['xwininfo', '-id', self.window_id],
            env=os.environ
        ).decode()

        x = int(re.search(r'Absolute upper-left X:\s+(-?\d+)', output).group(1))
        y = int(re.search(r'Absolute upper-left Y:\s+(-?\d+)', output).group(1))
        w = int(re.search(r'Width:\s+(\d+)', output).group(1))
        h = int(re.search(r'Height:\s+(\d+)', output).group(1))
        
        return x, y, w, h

    def screenshot(self, save_path):
        try:
            x, y, w, h = self._get_window_geometry()
            screenshot = self.gui.screenshot(region=(x, y, w, h))
            screenshot.save(save_path)
        except Exception:
            self.gui.screenshot().save(save_path)

    def stop(self):
        if self.app_process:
            self.app_process.terminate()
            try:
                self.app_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.app_process.kill()
        
        if self.wm_process:
            self.wm_process.terminate()
        
        self.display.stop()

if __name__ == "__main__":
    tester = AppTester()
    try:
        app_path = os.path.abspath("./app")
        tester.launch(app_path)
        
        tester.screenshot("screenshot_initial.png")
        
        tester.click(210, 440)
        time.sleep(1)
        
        tester.screenshot("screenshot_after_click.png")
    finally:
        tester.stop()