import threading

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


class TrayIcon:
    def __init__(self, parent):
        self.parent = parent
        self.icon = None
        self.thread = None

    def create(self):
        if not TRAY_AVAILABLE:
            return

        image = self._load_icon()

        menu = pystray.Menu(
            pystray.MenuItem("Zobrazit", self.parent.zobraz_okno),
            pystray.MenuItem("Ukončit", self.parent.ukoncit_aplikaci)
        )
        self.icon = pystray.Icon("WageSlave", image, "WageSlave System", menu)
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

    def _load_icon(self):
        import os, sys, shutil
        try:
            import config
            varianta = getattr(config, 'LOGO_VARIANTA', 'purple')
        except Exception:
            varianta = 'purple'

        ico_path = None
        root = os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) \
            else os.path.dirname(sys.executable)

        # Kandidáti v pořadí priority
        candidates = [
            os.path.join(root, 'img', 'icon', f"{varianta}.ico"),
            os.path.join(root, 'time.ico'),
        ]
        if getattr(sys, 'frozen', False):
            meipass = getattr(sys, '_MEIPASS', '')
            if meipass:
                candidates += [
                    os.path.join(meipass, 'img', 'icon', f"{varianta}.ico"),
                    os.path.join(meipass, 'time.ico'),
                ]

        for p in candidates:
            if os.path.exists(p):
                ico_path = p
                break

        if ico_path:
            try:
                img = Image.open(ico_path).convert("RGBA").resize((64, 64), Image.LANCZOS)
                return img
            except Exception:
                pass

        # Fallback: nakresli hodiny
        image = Image.new('RGB', (64, 64), color='#0d0f12')
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), outline='#3b82f6', width=4)
        draw.line((32, 32, 32, 18), fill='#3b82f6', width=3)
        draw.line((32, 32, 44, 38), fill='#60a5fa', width=2)
        return image

    def hide_window(self):
        if self.icon:
            self.icon.visible = True

    def show_window(self):
        if self.icon:
            self.icon.visible = False

    def stop(self):
        if self.icon:
            self.icon.stop()