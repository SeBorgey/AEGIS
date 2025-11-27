import os
import re
import time
import subprocess
from pyvirtualdisplay import Display
import pyautogui
import pyatspi

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
        self.app_pid = None

    def launch(self, app_path):
        if not os.path.exists(app_path):
            raise FileNotFoundError(f"{app_path} not found")
        
        env = os.environ.copy()
        env['QT_LINUX_ACCESSIBILITY_ALWAYS_ON'] = '1'
        env['QT_ACCESSIBILITY'] = '1'
        
        self.app_process = subprocess.Popen(
            [app_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        self.app_pid = self.app_process.pid
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
                    time.sleep(1)
                    return
            except subprocess.CalledProcessError:
                pass
            time.sleep(0.5)

    def click(self, x, y):
        try:
            wid = subprocess.check_output(
                 ['xdotool', 'getactivewindow'], env=os.environ, stderr=subprocess.DEVNULL
            ).decode().strip()
            if wid:
                self.window_id = wid
        except:
            pass

        subprocess.run(
            [
                'xdotool', 
                'mousemove', '--sync', str(x), str(y),
                'sleep', '0.1',
                'click', '1'
            ],
            env=os.environ,
            check=True
        )
        time.sleep(0.5)

    def _get_window_geometry(self):
        try:
            wid = subprocess.check_output(['xdotool', 'getactivewindow'], env=os.environ).decode().strip()
        except:
            wid = self.window_id

        output = subprocess.check_output(
            ['xwininfo', '-id', wid],
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

    def print_interactive_elements(self):
        desktop = pyatspi.Registry.getDesktop(0)
        found_apps = []

        for i in range(desktop.childCount):
            try:
                child = desktop.getChildAtIndex(i)
                if child.getRoleName() == 'application':
                    found_apps.append(child)
                elif 'frame' in child.getRoleName():
                     found_apps.append(child)
            except Exception:
                continue
        
        print(f"{'Role':<20} | {'Name':<30} | {'X':<5} | {'Y':<5} | {'W':<5} | {'H':<5}")
        print("-" * 85)
        
        for app in found_apps:
            if app.name and ('python' in app.name.lower() or 'app' in app.name.lower()):
                 self._traverse_tree(app)

    def _traverse_tree(self, obj):
        try:
            role = obj.getRoleName()
            name = obj.name
            
            interactive_roles = [
                'push button', 'text', 'check box', 'radio button', 
                'menu item', 'page tab', 'combo box', 'list item', 
                'entry', 'spin button', 'slider', 'table cell', 'link'
            ]

            try:
                component = obj.queryComponent()
                x, y, w, h = component.getExtents(pyatspi.DESKTOP_COORDS)
            except:
                x, y, w, h = -1, -1, 0, 0

            if role in interactive_roles and w > 0 and h > 0:
                safe_name = (name[:28] + '..') if len(name) > 28 else name
                print(f"{role:<20} | {safe_name:<30} | {x:<5} | {y:<5} | {w:<5} | {h:<5}")

            for i in range(obj.childCount):
                self._traverse_tree(obj.getChildAtIndex(i))
                
        except Exception:
            pass

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
        
        print("Initial State:")
        tester.print_interactive_elements()
        tester.screenshot("screenshot_1_initial.png")
        
        tester.click(X, Y) 
        time.sleep(2)
        
        print("\nState after interaction:")
        tester.print_interactive_elements()
        tester.screenshot("screenshot_2_after.png")
        
    finally:
        tester.stop()