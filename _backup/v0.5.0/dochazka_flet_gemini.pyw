import flet as ft
from datetime import datetime
import psutil

# Importy tvých modulů
from database import DochazkaDB
import calculator
from utils import formatuj_minuty

# --- BARVY (Zinc Palette) ---
BG = "#030712"
SIDEBAR = "#0f172a"
CARD = "#1e293b"
ACCENT = "#4f46e5"
TEXT_SUB = "#94a3b8"

class VestecApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.db = DochazkaDB()
        self.configure_page()
        self._init_controls() 
        self._build_ui()      
        self.obnovit_data()

    def configure_page(self):
        self.page.title = "Věštec Pro 2026"
        self.page.bgcolor = BG
        self.page.window_width = 1150
        self.page.window_height = 800
        self.page.window_resizable = False
        self.page.theme_mode = ft.ThemeMode.DARK

    def _init_controls(self):
        # Hero prvky
        self.hero_time = ft.Text("--:--", size=75, weight="bold", color=ft.Colors.WHITE)
        self.hero_progress = ft.ProgressBar(value=0, color=ft.Colors.WHITE, bgcolor=ft.Colors.WHITE24, height=8, width=280)
        self.stat_worked = ft.Text("0h 0m", size=28, weight="bold")
        self.stat_rem = ft.Text("0h 0m", size=28, weight="bold", color="#4ade80")
        
        # Form
        self.in_datum = ft.TextField(label="Datum", border_radius=12, height=45, text_size=13)
        self.in_prichod = ft.TextField(label="Příchod", border_radius=12, height=45, text_size=13)
        self.in_odchod = ft.TextField(label="Odchod", border_radius=12, height=45, text_size=13)
        
        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("DATUM")),
                ft.DataColumn(ft.Text("PŘÍCHOD")),
                ft.DataColumn(ft.Text("ODCHOD")),
                ft.DataColumn(ft.Text("STATUS")),
            ],
            heading_row_color=ft.Colors.WHITE10,
        )

    def _build_ui(self):
        sidebar = ft.Container(
            content=ft.Column([
                ft.Container(height=10),
                ft.Text("VĚŠTEC", size=24, weight="bold"),
                ft.Container(height=30),
                self._nav_item(ft.Icons.DASHBOARD_ROUNDED, "Dashboard", True),
                self._nav_item(ft.Icons.HISTORY_ROUNDED, "Historie", False),
            ]),
            width=240, bgcolor=SIDEBAR, padding=30,
        )

        main_content = ft.Column([
            # Hero & Stats řada
            ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text("ODCHOD V PÁTEK", size=11, weight="bold", color="white70"),
                        self.hero_time,
                        self.hero_progress,
                    ], spacing=5),
                    gradient=ft.LinearGradient(colors=["#4f46e5", "#7c3aed"]),
                    padding=35, border_radius=24, height=190,
                    shadow=ft.BoxShadow(blur_radius=25, color=ft.Colors.with_opacity(0.2, "#4f46e5"))
                ),
                ft.Column([
                    self._stat_box("ODPRACOVÁNO", self.stat_worked, ft.Icons.TIMER_OUTLINED),
                    self._stat_box("ZBÝVÁ", self.stat_rem, ft.Icons.DONE_ALL_ROUNDED, "#4ade80"),
                ], expand=True, spacing=15)
            ], spacing=25),

            # Tabulka a Editor
            ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text("AKTIVITA TENTO TÝDEN", size=13, weight="bold"),
                        ft.Column([self.table], scroll=ft.ScrollMode.ALWAYS, expand=True)
                    ]),
                    bgcolor=CARD, padding=25, border_radius=24, expand=True,
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("UPRAVIT DEN", size=13, weight="bold"),
                        self.in_datum, self.in_prichod, self.in_odchod,
                        ft.Button(
                            "AKTUALIZOVAT", 
                            on_click=self.obnovit_data, 
                            bgcolor=ACCENT, 
                            color=ft.Colors.WHITE,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                            height=48, width=250
                        )
                    ], spacing=15),
                    width=280, bgcolor=CARD, padding=25, border_radius=24
                )
            ], expand=True, spacing=25)
        ], spacing=30, expand=True)

        self.page.add(
            ft.Row([sidebar, ft.Container(main_content, padding=35, expand=True)], expand=True, spacing=0)
        )

    def _nav_item(self, icon, text, active):
        return ft.Container(
            content=ft.Row([ft.Icon(icon, color=ft.Colors.WHITE if active else TEXT_SUB, size=20), 
                            ft.Text(text, color=ft.Colors.WHITE if active else TEXT_SUB)], spacing=15),
            bgcolor="white10" if active else None,
            padding=12, border_radius=12
        )

    def _stat_box(self, title, control, icon, color=ft.Colors.WHITE):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, color=color, size=28),
                ft.Column([ft.Text(title, size=10, color=TEXT_SUB, weight="bold"), control], spacing=0)
            ], spacing=15),
            bgcolor=CARD, padding=20, border_radius=20, height=87, border=ft.border.all(1, "white10")
        )

    def obnovit_data(self, e=None):
        self.table.rows.clear()
        dnes = datetime.now().date()
        zaznamy = self.db.fetch_by_week(dnes.isocalendar()[1])
        
        for r in zaznamy:
            self.table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(r[2])),
                    ft.DataCell(ft.Text(r[3])),
                    ft.DataCell(ft.Text(r[4] if r[4] else "V PRÁCI", color="#4ade80" if not r[4] else ft.Colors.WHITE)),
                    ft.DataCell(ft.Icon(ft.Icons.CHECK_CIRCLE if r[4] else ft.Icons.PLAY_CIRCLE, size=18))
                ])
            )
        
        if zaznamy:
            try:
                wd = calculator.week_analysis(zaznamy, dnes)
                self.hero_time.value = wd["cas_patek"]
                self.hero_progress.value = wd["procenta"] / 100
                self.stat_worked.value = formatuj_minuty(wd["skutecne_celkem"])
                self.stat_rem.value = formatuj_minuty(wd["zbyva"])
            except: pass
        self.page.update()

def main(page: ft.Page):
    VestecApp(page)

if __name__ == "__main__":
    ft.run(main)