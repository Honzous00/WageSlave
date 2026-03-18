import threading
import pystray
from PIL import Image, ImageDraw

class TrayIcon:
    def __init__(self, parent):
        self.parent = parent
        self.icon = None
        self.thread = None

    def create(self):
        image = Image.new('RGB', (64, 64), color='#0078d4')
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill='white')

        menu = pystray.Menu(
            pystray.MenuItem("Zobrazit", self.parent.zobraz_okno),
            pystray.MenuItem("Ukončit", self.parent.ukoncit_aplikaci)
        )
        self.icon = pystray.Icon("PatecniVestec", image, "Páteční Věštec", menu)
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