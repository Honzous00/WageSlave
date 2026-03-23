# dochazka.pyw  ·  Páteční Věštec  ·  Midnight Navy Edition
# Framework : PySide6
# Design    : Monochromatic deep-blue, zero-decoration, data-first
# ─────────────────────────────────────────────────────────────
import sys
import csv
from datetime import datetime

import psutil

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel,
    QPushButton, QLineEdit, QCheckBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QHBoxLayout, QVBoxLayout, QSizePolicy,
    QScrollArea, QDialog, QAbstractItemView,
    QFileDialog, QMessageBox, QProgressBar,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QPalette, QCursor, QPainter, QPen, QBrush

import config
from utils import formatuj_minuty, normalizuj_cas, set_dark_title_bar
from database import DochazkaDB
import calculator

try:
    from tray import TrayIcon
    TRAY_DOSTUPNY = True
except ImportError:
    TRAY_DOSTUPNY = False

# ── Midnight Navy Palette ─────────────────────────────────────
ROOT        = "#07080d"   # absolute darkest  – window bg
SIDEBAR     = "#090b11"   # sidebar surface
TOPBAR_BDR  = "#0d1018"   # topbar bottom border
CARD        = "#08111f"   # card surface
CARD_DEEP   = "#050810"   # input / inset bg
BORDER      = "#0f1e35"   # card borders
BORDER_IN   = "#0e1a2a"   # input borders
ACCENT      = "#1e4fff"   # primary blue – buttons, active, bar
ACCENT_H    = "#1a42dd"   # hover
ACCENT_DIM  = "#0d2040"   # icon bg blue
LIVE_GREEN  = "#22c55e"
LIVE_DK     = "#071410"   # live row bg
POS_GREEN   = "#22c55e"
NEG_RED     = "#c0392b"
NEG_BG      = "#180e0e"
TEXT_HI     = "#c8d8f0"   # primary readable text
TEXT_MID    = "#5580aa"   # secondary – datum etc.
TEXT_DIM    = "#1a3255"   # captions, labels
TEXT_GHOST  = "#0e1e30"   # header cells
DUR_BLUE    = "#1e4fff"   # čistý čas value
ROW_NORM    = "#08111f"
ROW_ALT     = "#060c14"
ROW_LIVE    = "#071410"
NAV_ACTIVE  = "#0d1a30"
NAV_TEXT_ON = "#c8daf5"
DIVIDER     = "#0d1525"

# ══════════════════════════════════════════════════════════════
#  STYLESHEET
# ══════════════════════════════════════════════════════════════
QSS = f"""
/* ── Surfaces ── */
QMainWindow {{ background: {ROOT}; }}
QWidget#root {{ background: {ROOT}; }}
QWidget#main_area {{ background: {ROOT}; }}

/* ── Sidebar ── */
QFrame#sidebar {{
    background: {SIDEBAR};
    border-right: 1px solid {TOPBAR_BDR};
}}

/* ── Cards ── */
QFrame.card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

/* ── Nav buttons ── */
QPushButton.nav {{
    background: transparent;
    color: {TEXT_DIM};
    border: none;
    border-radius: 8px;
    padding: 9px 12px 9px 16px;
    font-size: 12px;
    font-weight: 500;
    text-align: left;
}}
QPushButton.nav:hover {{
    background: #10131c;
    color: {TEXT_MID};
}}
QPushButton.nav[on="1"] {{
    background: {NAV_ACTIVE};
    color: {NAV_TEXT_ON};
    font-weight: 600;
}}
QPushButton.nav[on="1"]:hover {{
    background: #0f1e38;
}}

/* ── Primary button ── */
QPushButton.primary {{
    background: {ACCENT};
    color: #c8d8ff;
    border: none;
    border-radius: 7px;
    padding: 7px 16px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QPushButton.primary:hover   {{ background: {ACCENT_H}; }}
QPushButton.primary:pressed {{ background: #152eb0; }}

/* ── Danger button ── */
QPushButton.danger {{
    background: transparent;
    color: {NEG_RED};
    border: 1px solid #1e1212;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QPushButton.danger:hover {{ background: {NEG_BG}; }}

/* ── Ghost / NOW ── */
QPushButton.ghost {{
    background: #0b1324;
    color: {TEXT_DIM};
    border: 1px solid {BORDER_IN};
    border-radius: 7px;
    padding: 4px 7px;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QPushButton.ghost:hover {{
    border-color: {ACCENT};
    color: {TEXT_MID};
}}

/* ── Inputs ── */
QLineEdit {{
    background: {CARD_DEEP};
    color: {TEXT_MID};
    border: 1px solid {BORDER_IN};
    border-radius: 7px;
    padding: 5px 10px;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{
    border-color: {ACCENT};
    color: {TEXT_HI};
    background: #060b16;
}}

/* ── ComboBox ── */
QComboBox {{
    background: {CARD_DEEP};
    color: {TEXT_MID};
    border: 1px solid {BORDER_IN};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 10px;
    min-height: 26px;
}}
QComboBox:hover {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 16px; }}
QComboBox QAbstractItemView {{
    background: {CARD};
    color: {TEXT_HI};
    border: 1px solid {BORDER};
    border-radius: 8px;
    selection-background-color: {ACCENT};
    outline: none;
}}

/* ── Checkbox ── */
QCheckBox {{
    color: {TEXT_DIM};
    font-size: 11px;
    spacing: 7px;
}}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {BORDER_IN};
    border-radius: 4px;
    background: {CARD_DEEP};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* ── Progress bar ── */
QProgressBar {{
    background: #0c1a2e;
    border: none;
    border-radius: 2px;
    height: 3px;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 2px;
}}

/* ── Table ── */
QTableWidget {{
    background: {CARD};
    alternate-background-color: {ROW_ALT};
    color: {TEXT_DIM};
    gridline-color: transparent;
    border: none;
    outline: none;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
}}
QTableWidget::item {{
    padding: 9px 8px;
    border-bottom: 1px solid {DIVIDER};
}}
QTableWidget::item:selected {{
    background: {ACCENT};
    color: #ddeeff;
}}
QHeaderView::section {{
    background: {CARD_DEEP};
    color: {TEXT_GHOST};
    border: none;
    border-bottom: 1px solid {DIVIDER};
    padding: 8px 8px;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 1.5px;
}}
QScrollBar:vertical {{
    background: {CARD_DEEP};
    width: 4px;
    border-radius: 2px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 2px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}

/* ── Labels ── */
QLabel {{ color: {TEXT_HI}; background: transparent; }}
QLabel.cap {{
    color: {TEXT_DIM};
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 2px;
}}
QLabel.hero_val {{
    color: {TEXT_HI};
    font-size: 42px;
    font-weight: 800;
    letter-spacing: -2px;
}}
QLabel.stat_val {{
    color: {TEXT_HI};
    font-size: 20px;
    font-weight: 800;
    letter-spacing: -0.5px;
}}
QLabel.sec_title {{
    color: {ACCENT};
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 2.5px;
}}
QLabel.logo_a {{
    color: {TEXT_HI};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 3px;
}}
QLabel.logo_b {{
    color: {TEXT_DIM};
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 2px;
}}
QLabel.topbar_title {{
    color: #c8d4e8;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: -0.3px;
}}
QLabel.topbar_sub {{
    color: {TEXT_DIM};
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 1px;
}}
QLabel.live_badge {{
    color: {LIVE_GREEN};
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
}}
QLabel.week_badge {{
    color: {TEXT_DIM};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.5px;
    background: #0c0f18;
    border: 1px solid #121828;
    border-radius: 6px;
    padding: 3px 10px;
}}
QLabel.nav_section {{
    color: #1e2d45;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 2.5px;
    padding-left: 20px;
}}
QLabel.pct {{
    color: {ACCENT};
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
"""


# ══════════════════════════════════════════════════════════════
#  LEFT ACCENT STRIPE  – painted onto the departure card
# ══════════════════════════════════════════════════════════════
class AccentCard(QFrame):
    """Card with a 2px blue left-edge accent stripe painted in Qt."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(ACCENT)))
        r = 12  # matches border-radius
        p.drawRoundedRect(0, 0, 3, self.height(), r, r)
        p.end()


# ══════════════════════════════════════════════════════════════
class PatecniVestec(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Páteční Věštec")
        self.setFixedSize(1100, 700)
        if sys.platform == "win32":
            set_dark_title_bar(self)

        self.db      = DochazkaDB()
        self.edit_id = None

        self.setup_ui()
        self.apply_styles()
        self.connect_signals()

        self.nacti_tydny_do_filtru()
        self.reset_form()
        self.obnovit_data()

        self._t_data = QTimer(self)
        self._t_data.timeout.connect(self.obnovit_data)
        self._t_data.start(60_000)

        self._t_clock = QTimer(self)
        self._t_clock.timeout.connect(self._tick)
        self._t_clock.start(1_000)
        self._tick()

        QTimer.singleShot(2_000, self.check_unfinished_shift)
        QTimer.singleShot(1_000, self.check_boot_time_and_record)

        if TRAY_DOSTUPNY:
            self.tray = TrayIcon(self)
            self.tray.create()

    # ─────────────────────────────────────────────────────────
    def setup_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self._sidebar(h)
        self._main(h)

    # ── SIDEBAR ──────────────────────────────────────────────
    def _sidebar(self, parent):
        sb = QFrame()
        sb.setObjectName("sidebar")
        sb.setFixedWidth(200)

        v = QVBoxLayout(sb)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Logo block
        logo_w = QWidget()
        logo_w.setFixedHeight(72)
        logo_w.setStyleSheet(f"background:{SIDEBAR}; border-bottom:1px solid {TOPBAR_BDR};")
        ll = QVBoxLayout(logo_w)
        ll.setContentsMargins(20, 18, 20, 14)
        ll.setSpacing(2)
        a = QLabel("PÁTEČNÍ")
        a.setProperty("class", "logo_a")
        b = QLabel("VĚŠTEC · v2")
        b.setProperty("class", "logo_b")
        ll.addWidget(a)
        ll.addWidget(b)
        v.addWidget(logo_w)

        v.addSpacing(14)

        sec = QLabel("WORKSPACE")
        sec.setProperty("class", "nav_section")
        v.addWidget(sec)
        v.addSpacing(6)

        nav_w = QWidget()
        nav_l = QVBoxLayout(nav_w)
        nav_l.setContentsMargins(8, 0, 8, 0)
        nav_l.setSpacing(1)
        self.btn_dash  = self._nav("● Dashboard", on=True)
        self.btn_hist  = self._nav("○ Historie")
        self.btn_sett  = self._nav("○ Nastavení")
        nav_l.addWidget(self.btn_dash)
        nav_l.addWidget(self.btn_hist)
        nav_l.addWidget(self.btn_sett)
        v.addWidget(nav_w)

        v.addStretch(1)

        foot_div = QFrame()
        foot_div.setFrameShape(QFrame.HLine)
        foot_div.setFixedHeight(1)
        foot_div.setStyleSheet(f"background:{TOPBAR_BDR}; border:none;")
        v.addWidget(foot_div)

        foot_w = QWidget()
        foot_l = QVBoxLayout(foot_w)
        foot_l.setContentsMargins(8, 8, 8, 12)
        foot_l.setSpacing(1)
        self.btn_export  = self._nav("↑ Export CSV")
        self.btn_refresh = self._nav("↻ Obnovit")
        foot_l.addWidget(self.btn_export)
        foot_l.addWidget(self.btn_refresh)
        v.addWidget(foot_w)

        parent.addWidget(sb)

    def _nav(self, text, on=False):
        b = QPushButton(text)
        b.setProperty("class", "nav")
        b.setProperty("on", "1" if on else "0")
        b.setCursor(QCursor(Qt.PointingHandCursor))
        b.setFixedHeight(36)
        return b

    # ── MAIN ─────────────────────────────────────────────────
    def _main(self, parent):
        w = QWidget()
        w.setObjectName("main_area")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self._topbar(v)

        scroll_w = QWidget()
        scroll_w.setObjectName("main_area")
        sv = QVBoxLayout(scroll_w)
        sv.setContentsMargins(18, 14, 18, 16)
        sv.setSpacing(10)

        self._hero_row(sv)
        self._form_card(sv)
        self._table_card(sv)

        v.addWidget(scroll_w, 1)
        parent.addWidget(w, 1)

    # ── TOPBAR ────────────────────────────────────────────────
    def _topbar(self, parent):
        bar = QFrame()
        bar.setFixedHeight(58)
        bar.setStyleSheet(f"background:{ROOT}; border-bottom:1px solid {TOPBAR_BDR};")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(22, 0, 22, 0)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(2)
        self.lbl_title = QLabel("Přehled týdne")
        self.lbl_title.setProperty("class", "topbar_title")
        self.lbl_sub = QLabel()
        self.lbl_sub.setProperty("class", "topbar_sub")
        self._refresh_sub()
        ll.addWidget(self.lbl_title)
        ll.addWidget(self.lbl_sub)

        bl.addWidget(left)
        bl.addStretch()

        self.lbl_week = QLabel("TÝDEN —")
        self.lbl_week.setProperty("class", "week_badge")
        bl.addWidget(self.lbl_week)
        bl.addSpacing(16)

        live = QLabel("● LIVE")
        live.setProperty("class", "live_badge")
        bl.addWidget(live)

        parent.addWidget(bar)

    def _refresh_sub(self):
        fmt = "%A, %d. %B %Y" if sys.platform == "win32" else "%A, %-d. %B %Y"
        self.lbl_sub.setText(datetime.now().strftime(fmt).upper())

    # ── HERO ROW ──────────────────────────────────────────────
    def _hero_row(self, parent):
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)

        # Departure card (custom painted left accent)
        dep = AccentCard()
        dep.setFixedWidth(178)
        dl = QVBoxLayout(dep)
        dl.setContentsMargins(16, 16, 16, 12)
        dl.setSpacing(5)

        dep_cap = QLabel("ODCHOD V PÁTEK")
        dep_cap.setProperty("class", "cap")
        dl.addWidget(dep_cap)

        self.hero_val = QLabel("--:--")
        self.hero_val.setProperty("class", "hero_val")
        dl.addWidget(self.hero_val)

        self.prog = QProgressBar()
        self.prog.setValue(0)
        self.prog.setTextVisible(False)
        self.prog.setFixedHeight(3)
        dl.addWidget(self.prog)

        self.lbl_pct = QLabel("0 %")
        self.lbl_pct.setProperty("class", "pct")
        self.lbl_pct.setAlignment(Qt.AlignRight)
        dl.addWidget(self.lbl_pct)
        dl.addStretch()

        rl.addWidget(dep)

        # 3 stat cards
        self._stat(rl, "ODPRACOVÁNO",     "work",    "odpracováno")
        self._stat(rl, "ZBÝVÁ DO KONCE",  "remain",  "zbývá")
        self._stat(rl, "MĚSÍČNÍ BILANCE", "balance", "bilance")

        # Clock
        clk = QFrame()
        clk.setProperty("class", "card")
        clk.setFixedWidth(126)
        cl = QVBoxLayout(clk)
        cl.setContentsMargins(16, 14, 16, 12)
        cl.setSpacing(2)

        clk_cap = QLabel("AKTUÁLNÍ ČAS")
        clk_cap.setProperty("class", "cap")
        cl.addWidget(clk_cap)
        cl.addSpacing(4)

        self.lbl_hm = QLabel("00:00")
        self.lbl_hm.setStyleSheet(
            f"color:{ACCENT}; font-size:26px; font-weight:800; "
            f"letter-spacing:-1px; font-variant-numeric:tabular-nums;")
        cl.addWidget(self.lbl_hm)

        self.lbl_sec = QLabel(":00")
        self.lbl_sec.setStyleSheet(
            f"color:{ACCENT_DIM}; font-size:13px; font-weight:700; "
            f"font-variant-numeric:tabular-nums;")
        cl.addWidget(self.lbl_sec)
        cl.addStretch()

        rl.addWidget(clk)
        parent.addWidget(row)

    def _stat(self, parent, label, kind, key):
        card = QFrame()
        card.setProperty("class", "card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 12)
        cl.setSpacing(8)

        # icon + label row
        top = QWidget()
        tl = QHBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(7)

        icon = self._icon_widget(kind)
        tl.addWidget(icon)

        cap = QLabel(label)
        cap.setProperty("class", "cap")
        tl.addWidget(cap)
        tl.addStretch()
        cl.addWidget(top)

        val = QLabel("--")
        val.setProperty("class", "stat_val")
        cl.addWidget(val)
        cl.addStretch()

        setattr(self, f"stat_{key}_value", val)
        parent.addWidget(card, 1)

    def _icon_widget(self, kind):
        """Tiny SVG-style icon via QLabel with unicode char in a colored box."""
        icons = {
            "work":    ("◷", "#0b1e3f"),
            "remain":  ("↑", "#0e1a2a"),
            "balance": ("+", "#071e18"),
        }
        ch, bg = icons.get(kind, ("·", ACCENT_DIM))
        lbl = QLabel(ch)
        lbl.setFixedSize(24, 24)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"background:{bg}; border-radius:6px; font-size:12px; "
            f"font-weight:700; color:{TEXT_MID};")
        return lbl

    # ── FORM CARD ─────────────────────────────────────────────
    def _form_card(self, parent):
        card = QFrame()
        card.setProperty("class", "card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 12, 18, 12)
        cl.setSpacing(10)

        hdr = QWidget()
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(0, 0, 0, 0)

        t = QLabel("EDITACE ZÁZNAMU")
        t.setProperty("class", "sec_title")
        hl.addWidget(t)
        hl.addStretch()

        self.btn_save = QPushButton("ULOŽIT ZÁZNAM")
        self.btn_save.setProperty("class", "primary")
        self.btn_save.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_save.setFixedHeight(30)
        hl.addWidget(self.btn_save)
        cl.addWidget(hdr)

        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(14)
        bl.setAlignment(Qt.AlignLeft)

        self.ent_datum   = self._field(bl, "DATUM",    108)
        self.ent_prichod = self._field_now(bl, "PŘÍCHOD", 78,
                               lambda: self._set_now(self.ent_prichod))
        self.ent_odchod  = self._field_now(bl, "ODCHOD",  78,
                               lambda: self._set_now(self.ent_odchod))

        # Oběd checkbox
        ob_w = QWidget()
        ob_l = QVBoxLayout(ob_w)
        ob_l.setContentsMargins(0, 0, 0, 0)
        ob_l.setSpacing(0)
        ob_l.addSpacing(16)
        self.chk_obed = QCheckBox("Oběd")
        self.chk_obed.setChecked(True)
        ob_l.addWidget(self.chk_obed)
        bl.addWidget(ob_w)
        bl.addStretch()

        cl.addWidget(body)
        parent.addWidget(card)

    def _field(self, parent, lbl_txt, w):
        wrap = QWidget()
        vl = QVBoxLayout(wrap)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(4)
        cap = QLabel(lbl_txt)
        cap.setProperty("class", "cap")
        vl.addWidget(cap)
        ent = QLineEdit()
        ent.setFixedSize(w, 30)
        vl.addWidget(ent)
        parent.addWidget(wrap)
        return ent

    def _field_now(self, parent, lbl_txt, w, cmd):
        wrap = QWidget()
        vl = QVBoxLayout(wrap)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(4)
        cap = QLabel(lbl_txt)
        cap.setProperty("class", "cap")
        vl.addWidget(cap)
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(4)
        ent = QLineEdit()
        ent.setFixedSize(w, 30)
        rl.addWidget(ent)
        btn = QPushButton("NOW")
        btn.setProperty("class", "ghost")
        btn.setFixedSize(40, 30)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.clicked.connect(cmd)
        rl.addWidget(btn)
        vl.addWidget(row)
        parent.addWidget(wrap)
        return ent

    # ── TABLE CARD ────────────────────────────────────────────
    def _table_card(self, parent):
        card = QFrame()
        card.setProperty("class", "card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(44)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(18, 0, 14, 0)

        t = QLabel("ZÁZNAMY DOCHÁZKY")
        t.setProperty("class", "sec_title")
        hl.addWidget(t)
        hl.addStretch()

        wk = QLabel("Týden")
        wk.setProperty("class", "cap")
        hl.addWidget(wk)
        hl.addSpacing(6)

        self.combo = QComboBox()
        self.combo.addItems(["Aktuální týden", "Všechny záznamy"])
        self.combo.setFixedHeight(28)
        self.combo.setFixedWidth(158)
        hl.addWidget(self.combo)
        hl.addSpacing(8)

        self.btn_del = QPushButton("SMAZAT")
        self.btn_del.setProperty("class", "danger")
        self.btn_del.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_del.setFixedHeight(28)
        hl.addWidget(self.btn_del)

        cl.addWidget(hdr)

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{DIVIDER}; border:none;")
        cl.addWidget(div)

        cols = ["ID", "Týden", "Datum", "Příchod", "Odchod", "Čistý čas"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels([c.upper() for c in cols])
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnHidden(0, True)
        self.table.setFocusPolicy(Qt.NoFocus)

        hv = self.table.horizontalHeader()
        self.table.setColumnWidth(1, 62)
        self.table.setColumnWidth(2, 102)
        self.table.setColumnWidth(3, 80)
        hv.setSectionResizeMode(4, QHeaderView.Stretch)
        hv.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(42)

        cl.addWidget(self.table, 1)
        parent.addWidget(card, 1)

    # ─────────────────────────────────────────────────────────
    def apply_styles(self):
        QApplication.instance().setStyleSheet(QSS)

    def connect_signals(self):
        self.btn_save.clicked.connect(self.ulozit)
        self.btn_del.clicked.connect(self.smazat)
        self.btn_export.clicked.connect(self.export_s_vyberem_mesicu)
        self.btn_refresh.clicked.connect(self.obnovit_data)
        self.combo.currentIndexChanged.connect(lambda _=None: self.obnovit_data())
        self.ent_prichod.editingFinished.connect(lambda: self._norm(self.ent_prichod))
        self.ent_odchod.editingFinished.connect(lambda: self._norm(self.ent_odchod))
        self.table.itemSelectionChanged.connect(self.nacist_do_editace)
        self.table.clicked.connect(self.zrusit_vyber)

    def _norm(self, e: QLineEdit):
        class _C:
            def __init__(self, x): self._x = x
            def get(self): return self._x.text()
            def delete(self, *_): self._x.clear()
            def insert(self, _, v): self._x.setText(v)
        normalizuj_cas(_C(e))

    def _set_now(self, e: QLineEdit):
        e.setText(datetime.now().strftime("%H:%M"))

    def _tick(self):
        n = datetime.now()
        self.lbl_hm.setText(n.strftime("%H:%M"))
        self.lbl_sec.setText(n.strftime(":%S"))

    # ─────────────────────────────────────────────────────────
    def closeEvent(self, event):
        if TRAY_DOSTUPNY:
            event.ignore()
            self.hide()
            self.tray.hide_window()
        else:
            event.accept()

    def minimalizuj_do_tray(self):
        self.hide()
        if TRAY_DOSTUPNY:
            self.tray.hide_window()

    def zobraz_okno(self):
        self.show()
        self.activateWindow()
        if TRAY_DOSTUPNY:
            self.tray.show_window()

    def ukoncit_aplikaci(self):
        if TRAY_DOSTUPNY:
            self.tray.stop()
        QApplication.instance().quit()

    # ═════════════════════════════════════════════════════════
    # BUSINESS LOGIC  (1:1 original)
    # ═════════════════════════════════════════════════════════

    def nacti_tydny_do_filtru(self):
        tydny = self.db.fetch_distinct_weeks()
        self.combo.blockSignals(True)
        cur = self.combo.currentText()
        self.combo.clear()
        self.combo.addItems(
            ["Aktuální týden", "Všechny záznamy"] + [str(t) for t in tydny])
        idx = self.combo.findText(cur)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
        self.combo.blockSignals(False)

    def reset_form(self):
        self.edit_id = None
        self.ent_datum.setText(datetime.now().strftime("%Y-%m-%d"))
        self.ent_prichod.clear()
        self.ent_odchod.clear()
        self.btn_save.setText("ULOŽIT ZÁZNAM")

    def ulozit(self):
        d    = self.ent_datum.text()
        p    = self.ent_prichod.text()
        o    = self.ent_odchod.text() or None
        obed = 1 if self.chk_obed.isChecked() else 0
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            t  = dt.isocalendar()[1]
            if self.edit_id:
                self.db.update(self.edit_id, d, p, o, obed, t)
            else:
                self.db.insert(d, p, o, obed, t)
            self.nacti_tydny_do_filtru()
            self.reset_form()
            self.obnovit_data()
        except Exception:
            QMessageBox.critical(self, "Chyba", "Špatný formát času nebo data!")

    def smazat(self):
        row = self.table.currentRow()
        if row < 0:
            return
        it = self.table.item(row, 0)
        if it:
            self.db.delete(it.text())
            self.obnovit_data()

    def nacist_do_editace(self):
        row = self.table.currentRow()
        if row < 0:
            return
        it = self.table.item(row, 0)
        if it is None:
            return
        self.edit_id = it.text()
        z = self.db.fetch_by_id(self.edit_id)
        if z:
            self.ent_datum.setText(z[2])
            self.ent_prichod.setText(z[3])
            self.ent_odchod.clear()
            if z[4]:
                self.ent_odchod.setText(z[4])
            self.chk_obed.setChecked(bool(z[6]))
            self.btn_save.setText("AKTUALIZOVAT")

    def zrusit_vyber(self, index):
        if not index.isValid():
            self.table.clearSelection()
            self.reset_form()

    def obnovit_data(self):
        self.table.setRowCount(0)
        self._refresh_sub()

        filtr = self.combo.currentText()
        dnes  = datetime.now().date()

        if filtr == "Aktuální týden":
            tw    = dnes.isocalendar()[1]
            rows  = self.db.fetch_by_week(tw)
            week_rows = rows
            self.lbl_week.setText(f"TÝDEN {tw}")
        elif filtr == "Všechny záznamy":
            rows  = self.db.fetch_all()
            week_rows = []
            self.lbl_week.setText("VŠECHNY")
        else:
            tw    = int(filtr)
            rows  = self.db.fetch_by_week(tw)
            week_rows = rows
            self.lbl_week.setText(f"TÝDEN {tw}")

        for idx, r in enumerate(rows):
            vals = list(r)
            self.table.insertRow(idx)
            live = not r[4]
            if live:
                vals[4] = "V PRÁCI"
                vals[5] = "--"
            else:
                vals[5] = formatuj_minuty(r[5])

            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setTextAlignment(Qt.AlignCenter)
                if live:
                    item.setForeground(QColor(LIVE_GREEN))
                    item.setBackground(QColor(ROW_LIVE))
                    f = item.font(); f.setBold(True); item.setFont(f)
                elif col == 2:   # datum → slightly brighter
                    item.setForeground(QColor(TEXT_MID))
                elif col == 5 and not live and val and val != "--":
                    item.setForeground(QColor(DUR_BLUE))
                    f = item.font(); f.setBold(True); item.setFont(f)
                self.table.setItem(idx, col, item)

        # stats
        if filtr == "Aktuální týden" and week_rows:
            wd = calculator.week_analysis(week_rows, dnes)
            self.hero_val.setText(wd["cas_patek"])
            self.prog.setValue(int(wd["procenta"]))
            self.lbl_pct.setText(f"{wd['procenta']} %")

            self.stat_odpracováno_value.setText(formatuj_minuty(wd["skutecne_celkem"]))
            self.stat_odpracováno_value.setStyleSheet(
                f"color:{TEXT_MID}; font-size:20px; font-weight:800; letter-spacing:-0.5px;")

            self.stat_zbývá_value.setText(formatuj_minuty(wd["zbyva"]))
            self.stat_zbývá_value.setStyleSheet(
                f"color:{TEXT_HI}; font-size:20px; font-weight:800; letter-spacing:-0.5px;")

            mesic   = dnes.strftime("%Y-%m")
            balance = calculator.month_balance(self.db.fetch_by_month(mesic), dnes)
            sign    = "+" if balance >= 0 else ""
            color   = POS_GREEN if balance >= 0 else NEG_RED
            self.stat_bilance_value.setText(f"{sign}{formatuj_minuty(abs(balance))}")
            self.stat_bilance_value.setStyleSheet(
                f"color:{color}; font-size:20px; font-weight:800; letter-spacing:-0.5px;")
        else:
            self.hero_val.setText("--:--")
            self.prog.setValue(0)
            self.lbl_pct.setText("0 %")
            for key in ("odpracováno", "zbývá", "bilance"):
                lbl = getattr(self, f"stat_{key}_value")
                lbl.setText("--")
                lbl.setStyleSheet(
                    f"color:{TEXT_DIM}; font-size:20px; font-weight:800; letter-spacing:-0.5px;")

    def check_boot_time_and_record(self):
        try:
            boot = datetime.fromtimestamp(psutil.boot_time())
            d, cas = boot.strftime("%Y-%m-%d"), boot.strftime("%H:%M")
            with self.db._connect() as conn:
                exists = conn.execute(
                    "SELECT id FROM dochazka WHERE datum=?", (d,)).fetchone()
            if not exists:
                self.ent_datum.setText(d)
                self.ent_prichod.setText(cas)
                self.ulozit()
                QMessageBox.information(self, "Auto-zápis",
                                        f"Start PC detekován v {cas}")
            else:
                self.obnovit_data()
        except Exception:
            pass

    def export_s_vyberem_mesicu(self):
        rows = self.db.fetch_months_for_export()
        if not rows:
            QMessageBox.information(self, "Info", "Databáze neobsahuje žádné záznamy.")
            return

        data = {}
        for rok, mesic in rows:
            data.setdefault(rok, []).append(mesic)

        nazvy = ["Leden","Únor","Březen","Duben","Květen","Červen",
                 "Červenec","Srpen","Září","Říjen","Listopad","Prosinec"]

        dlg = QDialog(self)
        dlg.setWindowTitle("Export měsíců")
        dlg.setFixedSize(340, 460)
        dlg.setStyleSheet(f"background:{ROOT}; color:{TEXT_HI};")

        dl = QVBoxLayout(dlg)
        dl.setContentsMargins(16, 16, 16, 16)
        dl.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"border:none; background:{ROOT};")
        sc = QWidget()
        sc.setStyleSheet(f"background:{ROOT};")
        sl = QVBoxLayout(sc)
        sl.setSpacing(4)

        self.export_vars: dict = {}
        for rok, mesice in data.items():
            y = QLabel(str(rok))
            y.setStyleSheet(f"color:{ACCENT}; font-size:14px; font-weight:bold;")
            sl.addWidget(y)
            for m in mesice:
                chk = QCheckBox(nazvy[int(m)-1])
                chk.setStyleSheet(
                    f"color:{TEXT_HI}; font-size:12px; margin-left:14px;")
                self.export_vars[(rok, m)] = chk
                sl.addWidget(chk)

        sl.addStretch()
        scroll.setWidget(sc)
        dl.addWidget(scroll, 1)

        br = QWidget()
        brl = QHBoxLayout(br)
        brl.setContentsMargins(0, 0, 0, 0)
        brl.setSpacing(8)

        def sel_all():
            for c in self.export_vars.values(): c.setChecked(True)

        def do_exp():
            chosen = [f"{r}-{m}" for (r, m), c in self.export_vars.items() if c.isChecked()]
            if not chosen:
                QMessageBox.warning(dlg, "Varování", "Není vybrán žádný měsíc.")
                return
            self.proved_export(chosen)
            dlg.accept()

        for txt, fn, prim in [("Vybrat vše", sel_all, False),
                               ("Exportovat",  do_exp,  True),
                               ("Storno",  dlg.reject, False)]:
            b = QPushButton(txt)
            b.setProperty("class", "primary" if prim else "ghost")
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setFixedHeight(32)
            b.clicked.connect(fn)
            brl.addWidget(b)

        dl.addWidget(br)
        dlg.exec()

    def proved_export(self, mesice):
        path, _ = QFileDialog.getSaveFileName(
            self, "Uložit CSV jako", "", "CSV (*.csv)")
        if not path:
            return
        try:
            data = self.db.fetch_for_export(mesice)
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Datum", "Příchod", "Odchod"])
                w.writerows(data)
            QMessageBox.information(self, "Hotovo",
                                    f"Export {len(data)} záznamů proběhl úspěšně!")
        except Exception as e:
            QMessageBox.critical(self, "Chyba", str(e))

    def check_unfinished_shift(self):
        try:
            from eventlog import get_last_system_offline_time
        except ImportError:
            return
        rec = self.db.find_open_record()
        if not rec:
            return
        rec_id, datum, prichod, _ = rec
        if not prichod:
            return
        off = get_last_system_offline_time()
        if not off:
            return
        try:
            pdt = datetime.strptime(f"{datum} {prichod}", "%Y-%m-%d %H:%M")
        except Exception:
            return
        if pdt < off <= datetime.now():
            s = off.strftime("%H:%M")
            self.db.update_odchod(rec_id, s)
            self.obnovit_data()
            QMessageBox.information(
                self, "Automatické doplnění",
                f"Poslední směna nebyla ukončena.\nČas odchodu doplněn: {s}")


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")

        pal = QPalette()
        pal.setColor(QPalette.Window,          QColor(ROOT))
        pal.setColor(QPalette.WindowText,      QColor(TEXT_HI))
        pal.setColor(QPalette.Base,            QColor(CARD))
        pal.setColor(QPalette.AlternateBase,   QColor(ROW_ALT))
        pal.setColor(QPalette.Text,            QColor(TEXT_HI))
        pal.setColor(QPalette.Button,          QColor(CARD))
        pal.setColor(QPalette.ButtonText,      QColor(TEXT_HI))
        pal.setColor(QPalette.Highlight,       QColor(ACCENT))
        pal.setColor(QPalette.HighlightedText, QColor("#ddeeff"))
        app.setPalette(pal)

        w = PatecniVestec()
        w.show()
        sys.exit(app.exec())
    except Exception:
        import traceback
        traceback.print_exc()
        input("Stiskni Enter pro ukončení…")
