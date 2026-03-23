import sys
import sqlite3
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QFrame, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QLineEdit, QCheckBox, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QLinearGradient, QPalette

class AttendanceEngine:
    """Jádro pro manipulaci s daty dochazka.db"""
    def __init__(self, db_path="dochazka.db"):
        self.db_path = db_path

    def save_entry(self, prichod, odchod, obed):
        try:
            now = datetime.now()
            datum = now.strftime("%Y-%m-%d") [cite: 70, 71]
            tyden = now.isocalendar()[1]
            
            t1 = datetime.strptime(prichod, "%H:%M")
            t2 = datetime.strptime(odchod, "%H:%M")
            delta = t2 - t1
            minuty = int(delta.total_seconds() / 60)
            if obed: minuty -= 30

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO dochazka (tyden, datum, prichod, odchod, minut, obed)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (tyden, datum, prichod, odchod, minuty, 1 if obed else 0)) [cite: 37]
            return True
        except: return False

    def get_recent(self, limit=15):
        with sqlite3.connect(self.db_path) as conn:
            # Načítáme data přímo z tabulky dochazka 
            return conn.execute(f"""
                SELECT datum, prichod, odchod, minut, obed 
                FROM dochazka ORDER BY id DESC LIMIT {limit}
            """).fetchall() [cite: 70, 71, 72]

class VesticDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = AttendanceEngine()
        self.setWindowFlags(Qt.FramelessWindowHint) # Čistý bezrámový vzhled
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(1150, 750)
        
        self.setup_ui()
        self.apply_styles()
        self.refresh_data()
        
        # Hodiny a plynulý refresh
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

    def setup_ui(self):
        # Hlavní kontejner se zaoblením a stínem
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("mainFrame")
        self.main_frame.setGeometry(10, 10, 1130, 730)
        
        shadow = QGraphicsDropShadowEffect(blurRadius=25, xOffset=0, yOffset=5)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.main_frame.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self.main_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- NEON SIDEBAR ---
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(25, 40, 25, 40)

        logo = QLabel("VĚŠTEC\nPRO")
        logo.setObjectName("logo")
        side_layout.addWidget(logo)
        side_layout.addSpacing(50)

        for text in ["DASHBOARD", "LOGY", "STATISTIKY", "EXPORT"]:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            side_layout.addWidget(btn)
        
        side_layout.addStretch()
        
        exit_btn = QPushButton("UKONČIT")
        exit_btn.setObjectName("exitBtn")
        exit_btn.clicked.connect(self.close)
        side_layout.addWidget(exit_btn)
        
        layout.addWidget(sidebar)

        # --- DYNAMICKÝ CONTENT ---
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(30)

        # Top Bar: Nadpis a Hodiny
        top_bar = QHBoxLayout()
        title_v = QVBoxLayout()
        self.main_title = QLabel("System Overview")
        self.main_title.setObjectName("h1")
        self.sub_title = QLabel("Vítejte v operačním centru")
        self.sub_title.setObjectName("h2")
        title_v.addWidget(self.main_title)
        title_v.addWidget(self.sub_title)
        
        self.clock = QLabel("00:00:00")
        self.clock.setObjectName("clock")
        
        top_bar.addLayout(title_v)
        top_bar.addStretch()
        top_bar.addWidget(self.clock)
        content_layout.addLayout(top_bar)

        # Input Zone: Moderní karty pro zápis
        input_zone = QFrame()
        input_zone.setObjectName("inputCard")
        iz_layout = QHBoxLayout(input_zone)
        iz_layout.setContentsMargins(25, 20, 25, 20)

        # Pole pro čas
        self.in_start = self.create_input("PŘÍCHOD", "06:45")
        self.in_end = self.create_input("ODCHOD", datetime.now().strftime("%H:%M"))
        
        self.check_lunch = QCheckBox("LUNCH BREAK")
        self.check_lunch.setChecked(True)

        self.btn_save = QPushButton("LOG SYSTEM")
        self.btn_save.setObjectName("actionBtn")
        self.btn_save.clicked.connect(self.handle_save)

        iz_layout.addLayout(self.in_start)
        iz_layout.addLayout(self.in_end)
        iz_layout.addWidget(self.check_lunch)
        iz_layout.addSpacing(20)
        iz_layout.addWidget(self.btn_save)
        
        content_layout.addWidget(input_zone)

        # Table: Glassmorphism Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["DATUM", "IN", "OUT", "MIN", "OBĚD"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        content_layout.addWidget(self.table)

        layout.addWidget(content)

    def create_input(self, label, val):
        v = QVBoxLayout()
        lbl = QLabel(label)
        lbl.setObjectName("inputLabel")
        edit = QLineEdit(val)
        edit.setFixedWidth(120)
        v.addWidget(lbl)
        v.addWidget(edit)
        # Uložení reference pro pozdější čtení
        v.input_field = edit 
        return v

    def apply_styles(self):
        self.setStyleSheet("""
            #mainFrame { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #1e293b);
                border-radius: 20px;
                border: 1px solid #334155;
            }
            #sidebar { 
                background: rgba(15, 23, 42, 0.5); 
                border-top-left-radius: 20px; 
                border-bottom-left-radius: 20px;
                border-right: 1px solid #334155;
            }
            #logo { 
                color: #38bdf8; 
                font-size: 24px; 
                font-weight: 900; 
                letter-spacing: 2px;
                line-height: 1.2;
            }
            #h1 { color: white; font-size: 32px; font-weight: 800; }
            #h2 { color: #94a3b8; font-size: 14px; font-weight: 400; }
            #clock { 
                color: #38bdf8; font-family: 'Consolas'; font-size: 45px; font-weight: bold;
                text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
            }
            
            QPushButton { 
                background: transparent; color: #94a3b8; border: none; 
                text-align: left; padding: 15px; font-weight: 700; font-size: 12px;
                letter-spacing: 1px;
            }
            QPushButton:hover { color: #38bdf8; background: rgba(56, 189, 248, 0.1); border-radius: 10px; }
            
            #actionBtn { 
                background: #38bdf8; color: #0f172a; border-radius: 12px; 
                padding: 15px 35px; text-align: center; font-size: 14px;
            }
            #actionBtn:hover { background: #7dd3fc; }
            
            #inputCard { 
                background: rgba(30, 41, 59, 0.8); border: 1px solid #38bdf8; border-radius: 20px;
            }
            #inputLabel { color: #38bdf8; font-size: 10px; font-weight: 800; margin-bottom: 5px; }
            
            QLineEdit { 
                background: #0f172a; border: 1px solid #334155; color: white; 
                padding: 10px; border-radius: 8px; font-size: 16px; font-weight: bold;
            }
            QCheckBox { color: white; font-size: 11px; font-weight: bold; }
            
            QTableWidget { 
                background: transparent; border: none; color: #e2e8f0; font-size: 13px;
                alternate-background-color: rgba(255, 255, 255, 0.03);
            }
            QHeaderView::section { 
                background: transparent; color: #38bdf8; border: none; 
                padding: 15px; font-weight: 800; border-bottom: 2px solid #334155;
            }
            #exitBtn { color: #f43f5e; margin-top: 10px; }
            #exitBtn:hover { background: rgba(244, 63, 94, 0.1); }
        """)

    def update_time(self):
        self.clock.setText(datetime.now().strftime("%H:%M:%S"))

    def handle_save(self):
        start = self.in_start.input_field.text()
        end = self.in_end.input_field.text()
        if self.engine.save_entry(start, end, self.check_lunch.isChecked()):
            self.refresh_data()
            # Jednoduchá animace potvrzení barvou
            self.btn_save.setStyleSheet("background: #22c55e;")
            QTimer.singleShot(1000, lambda: self.btn_save.setStyleSheet(""))

    def refresh_data(self):
        data = self.engine.get_recent()
        self.table.setRowCount(0)
        for r_idx, row in enumerate(data):
            self.table.insertRow(r_idx)
            for c_idx, val in enumerate(row):
                val_str = "✓" if c_idx == 4 and val == 1 else ("-" if c_idx == 4 else str(val))
                item = QTableWidgetItem(val_str)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r_idx, c_idx, item)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VesticDashboard()
    window.show()
    sys.exit(app.exec())