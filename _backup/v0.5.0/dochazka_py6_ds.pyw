#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Páteční Věštec – NEO-GLASS EDITION
------------------------------------------------
Design z jiné dimenze. Skleněné karty, neonové akcenty,
asymetrická kompozice a dokonalé detaily.
"""

import sys
import csv
import psutil
from datetime import datetime
from collections import defaultdict

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFrame, QLabel, QPushButton, QLineEdit, QCheckBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QDialog, QScrollArea, QFileDialog, QMessageBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QFont, QColor, QLinearGradient, QBrush, QPalette, QPainter, QPainterPath

# Původní moduly
import config
from utils import formatuj_minuty, cas_na_minuty, normalizuj_cas
from database import DochazkaDB
import calculator

try:
    from tray import TrayIcon
    TRAY_DOSTUPNY = True
except ImportError:
    TRAY_DOSTUPNY = False


class GlassFrame(QFrame):
    """Vlastní rám s efektem skla a gradientním okrajem."""
    def __init__(self, parent=None, gradient_from="#2dd4bf", gradient_to="#a78bfa"):
        super().__init__(parent)
        self.gradient_from = QColor(gradient_from)
        self.gradient_to = QColor(gradient_to)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Hlavní výplň (průhledné sklo)
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)
        painter.setOpacity(0.85)
        painter.fillPath(path, QColor(10, 15, 25, 220))  # #0a0f19

        # Gradientní okraj
        painter.setOpacity(1.0)
        pen = painter.pen()
        pen.setWidth(2)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, self.gradient_from)
        gradient.setColorAt(1, self.gradient_to)
        pen.setBrush(QBrush(gradient))
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)


class PatecniVestec(QMainWindow):
    """
    Hlavní třída – NEO-GLASS provedení.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PÁTEČNÍ VĚŠTEC // NEO-GLASS")
        self.setFixedSize(1300, 800)  # Větší plátno pro dimenzi

        # Databáze a stav
        self.db = DochazkaDB()
        self.edit_id = None
        self.tray = None

        # Inicializace UI
        self._setup_ui()
        self._apply_animations()
        self._connect_signals()

        # Načtení dat a časovače
        self.nacti_tydny_do_filtru()
        self.reset_form()
        self.obnovit_data()
        self._start_timers()

        # Kontroly
        QTimer.singleShot(2000, self.check_unfinished_shift)
        QTimer.singleShot(1000, self.check_boot_time_and_record)

        # Tray
        if TRAY_DOSTUPNY:
            self.tray = TrayIcon(self)
            self.tray.create()
            self.closeEvent = self.minimalizuj_do_tray

    # ------------------------------------------------------------------
    # UI KONSTRUKCE – ABSOLUTNĚ NEJLEPŠÍ DESIGN
    # ------------------------------------------------------------------
    def _setup_ui(self):
        """Vytvoří widgety s důrazem na asymetrii a skleněný vzhled."""
        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet("background-color: #030712;")
        self.setCentralWidget(central)

        # Hlavní horizontální layout (žádný klasický sidebar)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== LEVÝ PANEL (NAVIGACE + LOGO) ==========
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_panel.setFixedWidth(100)  # Velmi úzký, minimalistický
        left_panel.setStyleSheet("""
            #leftPanel {
                background-color: rgba(10, 15, 25, 0.7);
                border-right: 1px solid rgba(45, 212, 191, 0.3);
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 40, 0, 40)
        left_layout.setSpacing(30)
        left_layout.setAlignment(Qt.AlignTop)

        # Logo (vertikální text)
        logo = QLabel("P\nV")
        logo.setObjectName("neoLogo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("""
            #neoLogo {
                font-size: 32px;
                font-weight: 800;
                color: transparent;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2dd4bf, stop:1 #a78bfa);
                background-clip: text;
                -webkit-text-fill-color: transparent;
                padding: 10px;
            }
        """)
        left_layout.addWidget(logo)

        # Navigační ikony (vertikální)
        nav_icons = [
            ("⌂", "dashboard"),
            ("▤", "history"),
            ("⚙", "settings"),
        ]
        self.nav_btns = {}
        for icon, name in nav_icons:
            btn = QPushButton(icon)
            btn.setObjectName("navIcon")
            btn.setFixedSize(50, 50)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                #navIcon {
                    background-color: rgba(255, 255, 255, 0.03);
                    color: #6b7280;
                    border: 1px solid rgba(45, 212, 191, 0.2);
                    border-radius: 25px;
                    font-size: 24px;
                    font-weight: 300;
                }
                #navIcon:hover {
                    background-color: rgba(45, 212, 191, 0.1);
                    color: #2dd4bf;
                    border-color: #2dd4bf;
                }
                #navIcon[active="true"] {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #2dd4bf, stop:1 #a78bfa);
                    color: #030712;
                    border: none;
                }
            """)
            btn.clicked.connect(lambda checked, n=name: self._nav_clicked(n))
            left_layout.addWidget(btn, alignment=Qt.AlignCenter)
            self.nav_btns[name] = btn

        left_layout.addStretch()

        # Spodní akce
        export_btn = QPushButton("↥")
        export_btn.setObjectName("navIcon")
        export_btn.setFixedSize(50, 50)
        export_btn.clicked.connect(self.export_s_vyberem_mesicu)
        left_layout.addWidget(export_btn, alignment=Qt.AlignCenter)

        refresh_btn = QPushButton("↻")
        refresh_btn.setObjectName("navIcon")
        refresh_btn.setFixedSize(50, 50)
        refresh_btn.clicked.connect(self.obnovit_data)
        left_layout.addWidget(refresh_btn, alignment=Qt.AlignCenter)

        main_layout.addWidget(left_panel)

        # ========== HLAVNÍ OBSAH ==========
        content = QWidget()
        content.setObjectName("content")
        main_layout.addWidget(content)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 30, 40, 30)
        content_layout.setSpacing(25)

        # ----- HEADER (asymetrický) -----
        self._create_neo_header(content_layout)

        # ----- HERO (dominantní prvek) -----
        self._create_neo_hero(content_layout)

        # ----- STATS + FORM v jedné řadě -----
        self._create_mid_section(content_layout)

        # ----- TABULKA (historické záznamy) -----
        self._create_neo_table(content_layout)

    def _create_neo_header(self, parent_layout):
        """Header s datem a velkým časem – asymetrický."""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 20)

        # Datum s efektem
        date_container = GlassFrame()
        date_container.setFixedHeight(60)
        date_container.setMaximumWidth(280)
        date_layout = QHBoxLayout(date_container)
        date_layout.setContentsMargins(20, 0, 20, 0)

        date_icon = QLabel("⏣")
        date_icon.setStyleSheet("font-size: 20px; color: #2dd4bf;")
        date_layout.addWidget(date_icon)

        self.lbl_date = QLabel()
        self.lbl_date.setStyleSheet("font-size: 15px; font-weight: 400; color: #e2e8f0; letter-spacing: 0.3px;")
        self._update_date()
        date_layout.addWidget(self.lbl_date)

        header_layout.addWidget(date_container)

        header_layout.addStretch()

        # Velký čas s podsvícením
        time_container = QWidget()
        time_layout = QHBoxLayout(time_container)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(15)

        self.lbl_big_time = QLabel()
        self.lbl_big_time.setStyleSheet("""
            font-size: 72px;
            font-weight: 700;
            color: #f8fafc;
            letter-spacing: 4px;
            text-shadow: 0 0 20px #2dd4bf, 0 0 40px rgba(45, 212, 191, 0.3);
        """)
        self._update_time()
        time_layout.addWidget(self.lbl_big_time)

        # Live indikátor (pulzující)
        self.lbl_live = QLabel("●")
        self.lbl_live.setStyleSheet("""
            font-size: 28px;
            color: #2dd4bf;
            text-shadow: 0 0 15px #2dd4bf;
        """)
        time_layout.addWidget(self.lbl_live)

        header_layout.addWidget(time_container)

        parent_layout.addWidget(header)

    def _create_neo_hero(self, parent_layout):
        """Hero sekce – odchod v pátek jako absolutní dominanta."""
        hero = GlassFrame()
        hero.setFixedHeight(220)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(40, 30, 40, 30)
        hero_layout.setSpacing(40)

        # Levá část – text a progress
        left_hero = QWidget()
        left_layout = QVBoxLayout(left_hero)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)

        hero_label = QLabel("ODCHOD V PÁTEK")
        hero_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #6b7280;
            letter-spacing: 4px;
            text-transform: uppercase;
        """)
        left_layout.addWidget(hero_label)

        self.hero_time = QLabel("--:--")
        self.hero_time.setStyleSheet("""
            font-size: 96px;
            font-weight: 800;
            color: #f8fafc;
            line-height: 1;
            text-shadow: 0 0 30px #a78bfa;
        """)
        left_layout.addWidget(self.hero_time)

        # Progress bar s glow
        progress_container = QWidget()
        progress_container.setFixedHeight(60)
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setFixedHeight(10)
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #1f2937;
                border: none;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2dd4bf, stop:1 #a78bfa);
                border-radius: 5px;
            }
        """)
        progress_layout.addWidget(self.progress)

        percent_row = QWidget()
        percent_layout = QHBoxLayout(percent_row)
        percent_layout.setContentsMargins(0, 5, 0, 0)

        self.lbl_percent = QLabel("0 %")
        self.lbl_percent.setStyleSheet("font-size: 18px; font-weight: 600; color: #a78bfa;")
        percent_layout.addWidget(self.lbl_percent)
        percent_layout.addStretch()

        progress_layout.addWidget(percent_row)
        left_layout.addWidget(progress_container)

        hero_layout.addWidget(left_hero)

        # Pravá část – 3 statistiky v kompaktním layoutu
        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(20)

        stats_data = [
            ("odpracovano", "⏱️", "ODPRACOVÁNO"),
            ("zbyva", "⏳", "ZBÝVÁ"),
            ("bilance", "⚖️", "BILANCE"),
        ]
        self.stat_cards = {}
        for key, icon, label in stats_data:
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: rgba(15, 23, 42, 0.6);
                    border: 1px solid rgba(45, 212, 191, 0.2);
                    border-radius: 20px;
                }
            """)
            card.setFixedSize(160, 120)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(15, 15, 15, 15)
            card_layout.setSpacing(8)

            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet("font-size: 22px; color: #2dd4bf;")
            card_layout.addWidget(icon_lbl)

            title_lbl = QLabel(label)
            title_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6b7280; letter-spacing: 0.5px;")
            card_layout.addWidget(title_lbl)

            value_lbl = QLabel("--")
            value_lbl.setStyleSheet("font-size: 28px; font-weight: 700; color: #f8fafc;")
            card_layout.addWidget(value_lbl)

            stats_layout.addWidget(card)
            self.stat_cards[key] = value_lbl

        hero_layout.addWidget(stats_container)

        parent_layout.addWidget(hero)

    def _create_mid_section(self, parent_layout):
        """Prostřední sekce – formulář vlevo, něco vpravo (placeholder pro symetrii)."""
        mid = QWidget()
        mid_layout = QHBoxLayout(mid)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(25)

        # Formulář – skleněná karta
        form_card = GlassFrame()
        form_card.setMaximumWidth(650)
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(30, 25, 30, 25)
        form_layout.setSpacing(20)

        # Záhlaví
        form_header = QWidget()
        form_header_layout = QHBoxLayout(form_header)
        form_header_layout.setContentsMargins(0, 0, 0, 0)

        form_title = QLabel("✦ EDITACE DNE")
        form_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #e2e8f0; letter-spacing: 1px;")
        form_header_layout.addWidget(form_title)

        form_header_layout.addStretch()

        self.btn_ulozit = QPushButton("▸ ULOŽIT")
        self.btn_ulozit.setCursor(Qt.PointingHandCursor)
        self.btn_ulozit.setFixedSize(120, 40)
        self.btn_ulozit.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2dd4bf, stop:1 #a78bfa);
                color: #030712;
                border: none;
                border-radius: 30px;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #a78bfa, stop:1 #2dd4bf);
            }
        """)
        self.btn_ulozit.clicked.connect(self.ulozit)
        form_header_layout.addWidget(self.btn_ulozit)

        form_layout.addWidget(form_header)

        # Grid vstupů
        inputs_grid = QWidget()
        grid_layout = QHBoxLayout(inputs_grid)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(15)

        # Datum
        date_field = self._create_neo_field("DATUM", "140")
        self.ent_datum = date_field["input"]
        grid_layout.addWidget(date_field["widget"])

        # Příchod
        prichod_field = self._create_neo_field("PŘÍCHOD", "90", with_now=True)
        self.ent_prichod = prichod_field["input"]
        self.ent_prichod.editingFinished.connect(lambda: normalizuj_cas(self.ent_prichod))
        prichod_field["now"].clicked.connect(lambda: self._set_now(self.ent_prichod))
        grid_layout.addWidget(prichod_field["widget"])

        # Odchod
        odchod_field = self._create_neo_field("ODCHOD", "90", with_now=True)
        self.ent_odchod = odchod_field["input"]
        self.ent_odchod.editingFinished.connect(lambda: normalizuj_cas(self.ent_odchod))
        odchod_field["now"].clicked.connect(lambda: self._set_now(self.ent_odchod))
        grid_layout.addWidget(odchod_field["widget"])

        # Checkbox
        self.obed_check = QCheckBox("⏲ OBĚD")
        self.obed_check.setChecked(True)
        self.obed_check.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                font-weight: 600;
                color: #cbd5e1;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 6px;
                border: 1px solid #2dd4bf;
                background-color: rgba(45, 212, 191, 0.1);
            }
            QCheckBox::indicator:checked {
                background-color: #2dd4bf;
                image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='%23030712'><path d='M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z'/></svg>");
            }
        """)
        grid_layout.addWidget(self.obed_check)

        grid_layout.addStretch()
        form_layout.addWidget(inputs_grid)

        mid_layout.addWidget(form_card)

        # Pravá část – čistě dekorativní prvek (můžeš sem dát něco užitečného)
        right_deco = GlassFrame()
        right_deco.setFixedWidth(200)
        deco_layout = QVBoxLayout(right_deco)
        deco_layout.setContentsMargins(20, 20, 20, 20)
        deco_layout.setAlignment(Qt.AlignCenter)

        deco_text = QLabel("⚡\nNEO\nGLASS")
        deco_text.setAlignment(Qt.AlignCenter)
        deco_text.setStyleSheet("""
            font-size: 24px;
            font-weight: 800;
            color: transparent;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #2dd4bf, stop:1 #a78bfa);
            background-clip: text;
            -webkit-text-fill-color: transparent;
        """)
        deco_layout.addWidget(deco_text)

        mid_layout.addWidget(right_deco)

        parent_layout.addWidget(mid)

    def _create_neo_field(self, label_text, width, with_now=False):
        """Vytvoří vstupní pole v neo stylu."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 10px; font-weight: 600; color: #6b7280; letter-spacing: 0.5px;")
        layout.addWidget(label)

        if with_now:
            input_row = QWidget()
            row_layout = QHBoxLayout(input_row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            line_edit = QLineEdit()
            line_edit.setFixedWidth(int(width))
            line_edit.setStyleSheet("""
                QLineEdit {
                    background-color: rgba(15, 23, 42, 0.8);
                    border: 1px solid #2dd4bf;
                    border-radius: 12px;
                    padding: 10px 12px;
                    color: #f8fafc;
                    font-size: 14px;
                    font-weight: 500;
                }
                QLineEdit:focus {
                    border-color: #a78bfa;
                    background-color: #0f172a;
                }
            """)
            row_layout.addWidget(line_edit)

            now_btn = QPushButton("NOW")
            now_btn.setCursor(Qt.PointingHandCursor)
            now_btn.setFixedSize(50, 38)
            now_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(45, 212, 191, 0.1);
                    color: #2dd4bf;
                    border: 1px solid #2dd4bf;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #2dd4bf;
                    color: #030712;
                }
            """)
            row_layout.addWidget(now_btn)

            layout.addWidget(input_row)
            return {"widget": container, "input": line_edit, "now": now_btn}
        else:
            line_edit = QLineEdit()
            line_edit.setFixedWidth(int(width))
            line_edit.setStyleSheet("""
                QLineEdit {
                    background-color: rgba(15, 23, 42, 0.8);
                    border: 1px solid #334155;
                    border-radius: 12px;
                    padding: 10px 12px;
                    color: #f8fafc;
                    font-size: 14px;
                    font-weight: 500;
                }
                QLineEdit:focus {
                    border-color: #2dd4bf;
                    background-color: #0f172a;
                }
            """)
            layout.addWidget(line_edit)
            return {"widget": container, "input": line_edit}

    def _create_neo_table(self, parent_layout):
        """Tabulka historie – futuristická, bez linek, s glow efektem."""
        table_card = GlassFrame()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(30, 25, 30, 25)
        table_layout.setSpacing(15)

        # Záhlaví
        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)

        table_title = QLabel("⚡ HISTORIE ZÁZNAMŮ")
        table_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #e2e8f0; letter-spacing: 1px;")
        header_layout.addWidget(table_title)

        header_layout.addStretch()

        # Filtr
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(10)

        filter_label = QLabel("TÝDEN")
        filter_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #6b7280;")
        filter_layout.addWidget(filter_label)

        self.combo_tyden = QComboBox()
        self.combo_tyden.setFixedWidth(160)
        self.combo_tyden.setStyleSheet("""
            QComboBox {
                background-color: rgba(15, 23, 42, 0.8);
                border: 1px solid #2dd4bf;
                border-radius: 20px;
                padding: 8px 16px;
                color: #f8fafc;
                font-size: 12px;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #2dd4bf;
            }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                border: 1px solid #2dd4bf;
                border-radius: 10px;
                color: #f8fafc;
                selection-background-color: #2dd4bf;
                selection-color: #030712;
            }
        """)
        filter_layout.addWidget(self.combo_tyden)

        header_layout.addWidget(filter_container)

        # Tlačítko Smazat
        self.btn_smazat = QPushButton("✕ SMAZAT")
        self.btn_smazat.setCursor(Qt.PointingHandCursor)
        self.btn_smazat.setFixedSize(110, 36)
        self.btn_smazat.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #f87171;
                border: 1px solid #f87171;
                border-radius: 30px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: #f87171;
                color: #030712;
            }
        """)
        self.btn_smazat.clicked.connect(self.smazat)
        header_layout.addWidget(self.btn_smazat)

        table_layout.addWidget(header_row)

        # Tabulka
        self.table = QTableWidget()
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                alternate-background-color: rgba(15, 23, 42, 0.3);
                border: none;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border: none;
                color: #cbd5e1;
                font-size: 13px;
            }
            QTableWidget::item:selected {
                background-color: rgba(45, 212, 191, 0.2);
                color: #2dd4bf;
            }
            QHeaderView::section {
                background-color: transparent;
                color: #6b7280;
                padding: 12px 8px;
                border: none;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
                border-bottom: 1px solid #2dd4bf;
            }
        """)

        # Sloupce
        columns = ["ID", "TÝDEN", "DATUM", "PŘÍCHOD", "ODCHOD", "ČISTÝ ČAS"]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)

        self.table.hideColumn(0)

        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 110)
        self.table.horizontalHeader().setStretchLastSection(True)

        table_layout.addWidget(self.table)

        parent_layout.addWidget(table_card)

    def _apply_animations(self):
        """Aplikuje jemné animace pro živost."""
        # Pulzování live indikátoru
        self.pulse_anim = QPropertyAnimation(self.lbl_live, b"geometry")
        self.pulse_anim.setDuration(1000)
        self.pulse_anim.setLoopCount(-1)
        self.pulse_anim.setKeyValueAt(0, self.lbl_live.geometry())
        self.pulse_anim.setKeyValueAt(0.5, self.lbl_live.geometry().adjusted(0, 0, 5, 5))
        self.pulse_anim.setKeyValueAt(1, self.lbl_live.geometry())
        self.pulse_anim.setEasingCurve(QEasingCurve.InOutSine)
        self.pulse_anim.start()

    # ------------------------------------------------------------------
    # SIGNÁLY A POMOCNÉ METODY
    # ------------------------------------------------------------------
    def _connect_signals(self):
        self.combo_tyden.currentIndexChanged.connect(self.obnovit_data)
        self.table.itemSelectionChanged.connect(self._on_table_selection)

    def _update_date(self):
        now = datetime.now()
        fmt = "%A, %d. %B %Y" if sys.platform == "win32" else "%A, %-d. %B %Y"
        self.lbl_date.setText(now.strftime(fmt).upper())

    def _update_time(self):
        now = datetime.now().strftime("%H:%M")
        self.lbl_big_time.setText(now)
        QTimer.singleShot(60000, self._update_time)

    def _set_now(self, line_edit):
        line_edit.setText(datetime.now().strftime("%H:%M"))

    def _nav_clicked(self, nav_id):
        for name, btn in self.nav_btns.items():
            btn.setProperty("active", name == nav_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ------------------------------------------------------------------
    # LOGIKA (převzato, adaptováno)
    # ------------------------------------------------------------------
    def nacti_tydny_do_filtru(self):
        tydny = self.db.fetch_distinct_weeks()
        self.combo_tyden.clear()
        self.combo_tyden.addItem("AKTUÁLNÍ")
        self.combo_tyden.addItem("VŠECHNY")
        for t in tydny:
            self.combo_tyden.addItem(str(t))

    def reset_form(self):
        self.edit_id = None
        self.ent_datum.setText(datetime.now().strftime("%Y-%m-%d"))
        self.ent_prichod.clear()
        self.ent_odchod.clear()
        self.btn_ulozit.setText("▸ ULOŽIT")
        self.obed_check.setChecked(True)

    def ulozit(self):
        d = self.ent_datum.text()
        p = self.ent_prichod.text()
        o = self.ent_odchod.text() or None
        obed = 1 if self.obed_check.isChecked() else 0
        try:
            dt_obj = datetime.strptime(d, "%Y-%m-%d")
            tyden = dt_obj.isocalendar()[1]
            if self.edit_id:
                self.db.update(self.edit_id, d, p, o, obed, tyden)
            else:
                self.db.insert(d, p, o, obed, tyden)
            self.nacti_tydny_do_filtru()
            self.reset_form()
            self.obnovit_data()
        except Exception:
            QMessageBox.critical(self, "CHYBA", "ŠPATNÝ FORMÁT ČASU NEBO DATA!")

    def smazat(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        id_item = self.table.item(row, 0)
        if id_item:
            id_db = int(id_item.text())
            self.db.delete(id_db)
            self.obnovit_data()

    def _on_table_selection(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        id_item = self.table.item(row, 0)
        if id_item:
            self.edit_id = int(id_item.text())
            zaznam = self.db.fetch_by_id(self.edit_id)
            if zaznam:
                self.ent_datum.setText(zaznam[2])
                self.ent_prichod.setText(zaznam[3])
                self.ent_odchod.setText(zaznam[4] if zaznam[4] else "")
                self.obed_check.setChecked(bool(zaznam[6]))
                self.btn_ulozit.setText("✎ AKTUALIZOVAT")

    def mousePressEvent(self, event):
        if not self.table.geometry().contains(event.pos()):
            self.table.clearSelection()
            self.reset_form()
        super().mousePressEvent(event)

    def obnovit_data(self):
        self.table.setRowCount(0)

        filtr = self.combo_tyden.currentText()
        dnes = datetime.now().date()

        if filtr == "AKTUÁLNÍ":
            hledany_tyden = dnes.isocalendar()[1]
            rows = self.db.fetch_by_week(hledany_tyden)
            vsechny_tyden = rows
        elif filtr == "VŠECHNY":
            rows = self.db.fetch_all()
            vsechny_tyden = []
        else:
            try:
                hledany_tyden = int(filtr)
                rows = self.db.fetch_by_week(hledany_tyden)
                vsechny_tyden = rows
            except ValueError:
                rows = []
                vsechny_tyden = []

        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            id_val = str(r[0])
            tyden_val = str(r[1])
            datum_val = r[2]
            prichod_val = r[3]
            odchod_val = r[4] if r[4] else "⚡V PRÁCI"
            cisty_val = formatuj_minuty(r[5]) if r[5] is not None else "--"

            items = [
                QTableWidgetItem(id_val),
                QTableWidgetItem(tyden_val),
                QTableWidgetItem(datum_val),
                QTableWidgetItem(prichod_val),
                QTableWidgetItem(odchod_val),
                QTableWidgetItem(cisty_val),
            ]
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, col, item)

            if not r[4]:
                for col in range(self.table.columnCount()):
                    self.table.item(i, col).setForeground(QColor("#2dd4bf"))
                    font = QFont("Inter", 10, QFont.Bold)
                    self.table.item(i, col).setFont(font)

        if filtr == "AKTUÁLNÍ" and vsechny_tyden:
            wd = calculator.week_analysis(vsechny_tyden, dnes)
            self.hero_time.setText(wd["cas_patek"])
            self.progress.setValue(wd["procenta"])
            self.lbl_percent.setText(f"{wd['procenta']} %")

            self.stat_cards["odpracovano"].setText(formatuj_minuty(wd["skutecne_celkem"]))
            self.stat_cards["zbyva"].setText(formatuj_minuty(wd["zbyva"]))

            mesic_str = dnes.strftime("%Y-%m")
            mesic_data = self.db.fetch_by_month(mesic_str)
            balance = calculator.month_balance(mesic_data, dnes)
            sign = "+" if balance >= 0 else ""
            self.stat_cards["bilance"].setText(f"{sign}{formatuj_minuty(abs(balance))}")
            if balance >= 0:
                self.stat_cards["bilance"].setStyleSheet("color: #2dd4bf; font-size: 28px; font-weight: 700;")
            else:
                self.stat_cards["bilance"].setStyleSheet("color: #f87171; font-size: 28px; font-weight: 700;")
        else:
            self.hero_time.setText("--:--")
            self.progress.setValue(0)
            self.lbl_percent.setText("0 %")
            for key in self.stat_cards:
                self.stat_cards[key].setText("--")
            self.stat_cards["bilance"].setStyleSheet("color: #f8fafc; font-size: 28px; font-weight: 700;")

    def _start_timers(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.obnovit_data)
        self.timer.start(60000)
        self._update_time()

    # ------------------------------------------------------------------
    # SYSTÉMOVÉ FUNKCE
    # ------------------------------------------------------------------
    def minimalizuj_do_tray(self, event):
        event.ignore()
        self.hide()
        if self.tray:
            self.tray.hide_window()

    def zobraz_okno(self):
        self.show()
        if self.tray:
            self.tray.show_window()

    def ukoncit_aplikaci(self):
        if self.tray:
            self.tray.stop()
        QApplication.quit()

    def check_boot_time_and_record(self):
        try:
            boot_dt = datetime.fromtimestamp(psutil.boot_time())
            dnes, cas = boot_dt.strftime("%Y-%m-%d"), boot_dt.strftime("%H:%M")
            with self.db._connect() as conn:
                exists = conn.execute(
                    "SELECT id FROM dochazka WHERE datum=?", (dnes,)
                ).fetchone()
            if not exists:
                self.ent_datum.setText(dnes)
                self.ent_prichod.setText(cas)
                self.ulozit()
                QMessageBox.information(self, "⚡ AUTO-ZÁPIS", f"START PC DETEKOVÁN V {cas}")
            else:
                self.obnovit_data()
        except Exception:
            pass

    def check_unfinished_shift(self):
        try:
            from eventlog import get_last_system_offline_time
        except ImportError:
            return

        open_rec = self.db.find_open_record()
        if not open_rec:
            return
        rec_id, datum, prichod, obed = open_rec
        if not prichod:
            return
        offline_dt = get_last_system_offline_time()
        if not offline_dt:
            return
        try:
            prichod_dt = datetime.strptime(f"{datum} {prichod}", "%Y-%m-%d %H:%M")
        except Exception:
            return

        now = datetime.now()
        if prichod_dt < offline_dt <= now:
            offline_str = offline_dt.strftime("%H:%M")
            self.db.update_odchod(rec_id, offline_str)
            self.obnovit_data()
            QMessageBox.information(
                self,
                "⚡ AUTO-DOPLNĚNÍ",
                f"POSLEDNÍ SMĚNA NEByla ukončena.\n"
                f"ČAS ODCHODU DOPLNĚN: {offline_str}"
            )

    # ------------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------------
    def export_s_vyberem_mesicu(self):
        rows = self.db.fetch_months_for_export()
        if not rows:
            QMessageBox.information(self, "INFO", "DATABÁZE NEobsAHUJE ŽÁDNÉ ZÁZNAMY.")
            return

        data = {}
        for rok, mesic in rows:
            data.setdefault(rok, []).append(mesic)

        nazvy = ["LEDEN", "ÚNOR", "BŘEZEN", "DUBEN", "KVĚTEN", "ČERVEN",
                 "ČERVENEC", "SRPEN", "ZÁŘÍ", "ŘÍJEN", "LISTOPAD", "PROSINEC"]

        dialog = QDialog(self)
        dialog.setWindowTitle("EXPORT MĚSÍCŮ")
        dialog.setFixedSize(380, 500)
        dialog.setStyleSheet("background-color: #030712; color: #f8fafc;")

        layout = QVBoxLayout(dialog)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        scroll_layout = QVBoxLayout(content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)

        self.export_vars = {}
        for rok, mesice in data.items():
            rok_label = QLabel(str(rok))
            rok_label.setStyleSheet("font-size: 20px; font-weight: 700; color: #2dd4bf; margin-top: 15px;")
            scroll_layout.addWidget(rok_label)

            for m in sorted(mesice):
                cb = QCheckBox(nazvy[int(m) - 1])
                cb.setStyleSheet("""
                    QCheckBox {
                        color: #cbd5e1;
                        font-size: 13px;
                        spacing: 8px;
                    }
                    QCheckBox::indicator {
                        width: 18px;
                        height: 18px;
                        border-radius: 5px;
                        border: 1px solid #2dd4bf;
                        background-color: rgba(45, 212, 191, 0.1);
                    }
                    QCheckBox::indicator:checked {
                        background-color: #2dd4bf;
                    }
                """)
                self.export_vars[(rok, m)] = cb
                scroll_layout.addWidget(cb)

        scroll_layout.addStretch()
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_all = QPushButton("VYBRAT VŠE")
        btn_export = QPushButton("EXPORTOVAT")
        btn_cancel = QPushButton("ZRUŠIT")

        for btn in (btn_all, btn_export, btn_cancel):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    color: #f8fafc;
                    border: none;
                    border-radius: 30px;
                    padding: 10px 20px;
                    font-size: 12px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #2dd4bf;
                    color: #030712;
                }
            """)
            btn_layout.addWidget(btn)

        btn_all.clicked.connect(lambda: [v.setChecked(True) for v in self.export_vars.values()])
        btn_export.clicked.connect(lambda: self._do_export(dialog))
        btn_cancel.clicked.connect(dialog.reject)

        layout.addLayout(btn_layout)
        dialog.exec()

    def _do_export(self, dialog):
        chosen = [f"{r}-{m}" for (r, m), cb in self.export_vars.items() if cb.isChecked()]
        if not chosen:
            QMessageBox.warning(self, "VAROVÁNÍ", "NEVYBRÁN ŽÁDNÝ MĚSÍC.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "ULOŽIT CSV", "", "CSV (*.csv)"
        )
        if not path:
            return

        try:
            data = self.db.fetch_for_export(chosen)
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Datum", "Příchod", "Odchod"])
                w.writerows(data)
            QMessageBox.information(self, "HOTOVO", f"EXPORT {len(data)} ZÁZNAMŮ ÚSPĚŠNÝ!")
            dialog.accept()
        except Exception as e:
            QMessageBox.critical(self, "CHYBA", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PatecniVestec()
    window.show()
    sys.exit(app.exec())