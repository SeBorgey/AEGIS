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
        self.app_name = None

    def launch(self, app_path):
        if not os.path.exists(app_path):
            raise FileNotFoundError(f"{app_path} not found")
        
        self.app_name = os.path.basename(app_path)
        
        env = os.environ.copy()
        env['QT_LINUX_ACCESSIBILITY_ALWAYS_ON'] = '1'
        
        self.app_process = subprocess.Popen(
            [app_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
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

    def print_interactive_elements(self):
        # Получаем координаты самого окна, чтобы вычесть их
        win_x, win_y, win_w, win_h = self._get_window_geometry()
        
        desktop = pyatspi.Registry.getDesktop(0)
        app_obj = None
        
        # Ищем наше приложение в дереве доступности
        for i in range(desktop.childCount):
            child = desktop.getChildAtIndex(i)
            if self.app_name in child.name:
                app_obj = child
                break
        
        if not app_obj:
            print("Application accessibility tree not found.")
            return

        print(f"{'Role':<20} | {'Name':<30} | {'Rel X':<5} | {'Rel Y':<5} | {'W':<5} | {'H':<5}")
        print("-" * 90)
        # Передаем смещение окна в рекурсивную функцию
        self._traverse_tree(app_obj, (win_x, win_y))


    def _traverse_tree(self, obj, window_offset):
        win_x, win_y = window_offset
        try:
            role = obj.getRoleName()
            name = obj.name
            
            interactive_roles = [
                'push button', 'text', 'check box', 'radio button', 
                'menu item', 'page tab', 'combo box', 'list item', 
                'entry', 'spin button', 'slider'
            ]

            if role in interactive_roles:
                component = obj.queryComponent()
                # Получаем абсолютные координаты экрана
                abs_x, abs_y, w, h = component.getExtents(pyatspi.DESKTOP_COORDS)
                
                # Вычисляем относительные координаты (внутри окна)
                rel_x = abs_x - win_x
                rel_y = abs_y - win_y

                # Фильтруем элементы с нулевыми размерами или те, что "улетели" за пределы окна
                if w > 0 and h > 0 and rel_x >= 0 and rel_y >= 0:
                     print(f"{role:<20} | {name[:28]:<30} | {rel_x:<5} | {rel_y:<5} | {w:<5} | {h:<5}")

            for i in range(obj.childCount):
                self._traverse_tree(obj.getChildAtIndex(i), window_offset)
                
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
        
        tester.print_interactive_elements()
        
        tester.screenshot("screenshot_initial.png")
        
        tester.click(165, 190) # Пример клика по координатам из списка
        time.sleep(1)
        tester.screenshot("screenshot_initial2.png")

    finally:
        tester.stop()