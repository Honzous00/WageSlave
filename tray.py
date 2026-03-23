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
        image = Image.new('RGB', (64, 64), color='#0d0f12')
        draw = ImageDraw.Draw(image)
        # Draw a simple clock icon
        draw.ellipse((8, 8, 56, 56), outline='#3b82f6', width=4)
        draw.line((32, 32, 32, 18), fill='#3b82f6', width=3)
        draw.line((32, 32, 44, 38), fill='#60a5fa', width=2)

        menu = pystray.Menu(
            pystray.MenuItem("Zobrazit", self.parent.zobraz_okno),
            pystray.MenuItem("Ukončit", self.parent.ukoncit_aplikaci)
        )
        self.icon = pystray.Icon("Dochazka", image, "Docházkový systém", menu)
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

    def hide_window(self):
        if self.icon:
            self.icon.visible = True

    def show_window(self):
        if self.icon:
            self.icon.visible = False

    def stop(self):
        if self.icon:
            self.icon.stop()
