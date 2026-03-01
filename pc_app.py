import sys
import warnings
# Suppress PyQt5 sip deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*sipPyTypeDict.*")
import json
import httpx
import asyncio
import websockets
from datetime import datetime, date, timedelta, timezone
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QStackedWidget, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QFrame, QHeaderView, QGraphicsDropShadowEffect,
    QAbstractItemView, QDialog, QFormLayout, QMessageBox, QInputDialog, QStyledItemDelegate, QTimeEdit, QDateEdit, QCalendarWidget, QLayout
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QThread, QTime, QDate, QByteArray
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap

# --- Config (override via env or edit for deployment) ---
# 기본: Railway 백엔드 (가이드 예시 주소). 로컬 사용 시 MEAL_API_BASE_URL 으로 http://localhost:8000/api/admin 설정.
import os
_DEFAULT_RAILWAY = "https://web-production-e758d.up.railway.app/api/admin"
_API_BASE = os.environ.get("MEAL_API_BASE_URL", _DEFAULT_RAILWAY)
API_BASE_URL = _API_BASE
_ws_origin = _API_BASE.replace("https://", "wss://").replace("http://", "ws://").split("/api")[0]
WS_URL = _ws_origin + "/api/admin/ws"
API_TIMEOUT = 10.0

# --- WebSocket Client Thread ---
class WSClient(QThread):
    message_received = pyqtSignal(dict)
    
    def __init__(self, ws_url=None):
        super().__init__()
        self.ws_url = ws_url or WS_URL
        self.running = True
        self.loop = None
        
    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.listen())
        
    async def listen(self):
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.ws = ws
                    while self.running:
                        msg = await ws.recv()
                        try:
                            data = json.loads(msg)
                            self.message_received.emit(data)
                        except (json.JSONDecodeError, TypeError):
                            pass
            except Exception:
                # Reconnect on error after delay
                if self.running:
                    await asyncio.sleep(3)
                    
    def stop(self):
        self.running = False
        if hasattr(self, 'ws') and self.ws and self.loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)
            except Exception:
                pass
        self.quit()
        self.wait(3000)

# --- Worker Thread for Async Data Loading ---
class DataLoader(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

# --- Premium QSS Styling ---
QSS = """
QMainWindow { background-color: #0f172a; font-family: 'Malgun Gothic', 'Segoe UI', sans-serif; font-weight: bold; }
QWidget#Sidebar { background-color: #1e293b; border-right: 1px solid #334155; min-width: 260px; }
QLabel#Logo { color: #f8fafc; font-size: 28px; font-weight: bold; font-family: 'Malgun Gothic'; padding: 25px; }
QPushButton#MenuBtn {
    background-color: transparent; color: #94a3b8; border: none; text-align: left;
    padding: 15px 25px; font-size: 20px; font-weight: bold; font-family: 'Malgun Gothic'; border-radius: 8px; margin: 4px 12px;
}
QPushButton#MenuBtn:hover { background-color: #334155; color: #f8fafc; }
QPushButton#MenuBtn[active="true"] { background-color: #6366f1; color: #ffffff; }
QWidget#ContentArea { background-color: #0f172a; }
QLabel#HeaderTitle { color: #f8fafc; font-size: 36px; font-weight: bold; font-family: 'Malgun Gothic'; }
QFrame#StatCard { background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; padding: 15px; }
QLabel#StatValue { color: #f8fafc; font-size: 52px; font-weight: bold; font-family: 'Malgun Gothic'; }
QLabel#StatLabel { color: #94a3b8; font-size: 22px; font-weight: bold; font-family: 'Malgun Gothic'; }
QTableWidget { background-color: #1e293b; color: #f1f5f9; gridline-color: #334155; border: none; border-radius: 12px; alternate-background-color: #1a2333; font-size: 17px; selection-background-color: #3b82f6; outline: none; font-weight: bold; }
QTableWidget::item { padding: 0px; border-bottom: 1px solid #334155; }
QTableWidget::item:selected { background-color: #3b82f6; color: #ffffff; font-weight: bold; }
QHeaderView::section { background-color: #111b2d; color: #94a3b8; padding: 12px; border: none; font-weight: bold; font-size: 19px; font-family: 'Malgun Gothic'; border-bottom: 2px solid #334155; }
QLineEdit, QTimeEdit { background-color: #1e293b; border: 1px solid #475569; border-radius: 8px; color: #f8fafc; padding: 10px 15px; font-size: 19px; height: 40px; font-weight: bold; font-family: 'Malgun Gothic'; }
QDateEdit { background-color: #1e293b; border: 1px solid #475569; border-radius: 8px; color: #f8fafc; padding-left: 10px; padding-right: 30px; font-size: 19px; height: 40px; font-weight: bold; font-family: 'Malgun Gothic'; }
QDateEdit::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 20px; height: 16px; border-left: 1px solid #475569; border-top-right-radius: 8px; background-color: #334155; }
QDateEdit::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; height: 16px; border-left: 1px solid #475569; border-top: 1px solid #475569; border-bottom-right-radius: 8px; background-color: #334155; }
QDateEdit::drop-down { subcontrol-origin: border; subcontrol-position: top right; width: 26px; border-left: 1px solid #475569; border-top-right-radius: 8px; border-bottom-right-radius: 8px; background-color: #334155; }
QDateEdit::down-arrow { image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMCIgaGVpZ2h0PSIxMCIgdmlld0JveD0iMCAwIDEwIDEwIj48cGF0aCBkPSJNMSAzIEg5IEw1IDggWiIgZmlsbD0iI2Y4ZmFmYyIvPjwvc3ZnPg=="); width: 12px; height: 12px; }
QCalendarWidget QWidget { background-color: #1e293b; color: #f8fafc; font-family: 'Malgun Gothic'; }
QCalendarWidget QAbstractItemView:enabled { background-color: #1e293b; color: #f8fafc; selection-background-color: #6366f1; selection-color: white; }
QCalendarWidget QToolButton { color: #f8fafc; background-color: #334155; border-radius: 4px; font-weight: bold; }
QCalendarWidget QMenu { background-color: #1e293b; color: #f8fafc; }
QCalendarWidget QSpinBox { color: #f8fafc; background-color: #1e293b; selection-background-color: #6366f1; }
QPushButton#PrimaryBtn { background-color: #3b82f6; color: white; border-radius: 8px; padding: 10px 20px; font-weight: bold; font-size: 19px; min-height: 40px; min-width: 100px; font-family: 'Malgun Gothic'; }
QPushButton#PrimaryBtn:hover { background-color: #2563eb; }
QPushButton#SecondaryBtn { background-color: #64748b; color: #f8fafc; border-radius: 8px; padding: 10px 20px; font-weight: bold; font-size: 19px; min-height: 40px; min-width: 100px; font-family: 'Malgun Gothic'; }
QPushButton#SecondaryBtn:hover { background-color: #475569; }
QPushButton#DangerBtn { background-color: #ef4444; color: white; border-radius: 8px; padding: 10px 20px; font-weight: bold; font-size: 19px; min-height: 40px; min-width: 100px; font-family: 'Malgun Gothic'; }
QPushButton#DangerBtn:hover { background-color: #dc2626; }
QComboBox { background-color: #1e293b; border: 1px solid #475569; border-radius: 8px; color: #f8fafc; padding: 5px 15px; font-size: 21px; height: 40px; font-weight: bold; font-family: 'Malgun Gothic'; }
QComboBox QAbstractItemView { background-color: #1e293b; color: #f8fafc; selection-background-color: #3b82f6; border: 1px solid #334155; outline: none; }
QComboBox QAbstractItemView::item { min-height: 35px; padding: 2px 10px; }
QLabel#InputLabel { color: #ffffff; font-weight: bold; font-family: 'Malgun Gothic'; font-size: 18px; }
"""

class EmployeeSearchDialog(QDialog):
    def __init__(self, api, main_win, parent=None):
        super().__init__(parent)
        self.api = api
        self.main_win = main_win
        self.selected_employee = None
        self.setWindowTitle("사원 검색")
        self.setMinimumSize(600, 500)
        self.setStyleSheet(QSS)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Search area
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색할 성명 입력...")
        self.search_input.returnPressed.connect(self.on_search)
        
        self.search_btn = QPushButton("조회")
        self.search_btn.setObjectName("PrimaryBtn")
        self.search_btn.setFixedWidth(80)
        self.search_btn.clicked.connect(self.on_search)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)
        
        # Table area
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["사번", "성명", "부서", "회사"])
        setup_standard_table(self.table)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.on_select)
        layout.addWidget(self.table)
        
        # Bottom buttons
        btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("선택")
        self.select_btn.setObjectName("PrimaryBtn")
        self.select_btn.clicked.connect(self.on_select)
        
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.setObjectName("SecondaryBtn")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.select_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def on_search(self):
        name = self.search_input.text().strip()
        if not name:
            return
        self.search_btn.setEnabled(False)
        self.loader = DataLoader(self.api.get_employees, name)
        self.loader.finished.connect(self.display_results)
        self.loader.error.connect(self.on_search_error)
        self.loader.start()

    def on_search_error(self, err_msg):
        self.search_btn.setEnabled(True)
        QMessageBox.warning(self, "조회 실패", f"사원 검색 중 오류가 발생했습니다:\n{err_msg}")

    def display_results(self, data):
        self.search_btn.setEnabled(True)
        if not isinstance(data, list):
            return
        self.results = data
        self.table.setRowCount(len(data))
        
        comp_map = {c["id"]: c["name"] for c in self.main_win.companies_data if isinstance(c, dict)}
        dept_map = {d["id"]: d["name"] for d in self.main_win.departments_data if isinstance(d, dict)}
        
        for i, row in enumerate(data):
            comp_name = comp_map.get(row.get("company_id"), "Unknown")
            dept_name = dept_map.get(row.get("department_id"), "Unknown")
            
            item_no = QTableWidgetItem(str(row.get("emp_no", "")))
            item_no.setData(Qt.UserRole, i) # Original index in self.results
            
            self.table.setItem(i, 0, item_no)
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("name", ""))))
            self.table.setItem(i, 2, QTableWidgetItem(dept_name))
            self.table.setItem(i, 3, QTableWidgetItem(comp_name))
            
    def on_select(self):
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            item = self.table.item(row, 0)
            if item is not None:
                original_idx = item.data(Qt.UserRole)
                if original_idx is not None and 0 <= original_idx < len(self.results):
                    self.selected_employee = self.results[original_idx]
                    self.accept()
                    return
            QMessageBox.warning(self, "경고", "선택한 행의 데이터를 찾을 수 없습니다.")
        else:
            QMessageBox.warning(self, "경고", "사원을 선택해 주세요.")

def setup_standard_table(table):
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(38)
    table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.setShowGrid(True)
    table.setSortingEnabled(True)

class APIClient:
    def __init__(self, base_url=None):
        self.base_url = base_url or API_BASE_URL
        self.client = httpx.Client(timeout=API_TIMEOUT)

    def get_stats(self):
        try:
            r = self.client.get(f"{self.base_url}/stats/today")
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None


    def get_raw_data(self, search="", start_date=None, end_date=None):
        try:
            params = {"search": search} if search else {}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            r = self.client.get(f"{self.base_url}/raw-data", params=params)
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def create_manual_raw_data(self, data):
        try:
            r = self.client.post(f"{self.base_url}/raw-data/manual", params=data)
            if r.status_code == 200:
                return (True, r.json())
            try:
                detail = r.json().get("detail", "등록 실패")
            except Exception:
                detail = r.text or "등록 실패"
            return (False, detail)
        except Exception as e:
            return (False, str(e))

    def update_raw_data(self, log_id, data):
        try:
            r = self.client.put(f"{self.base_url}/raw-data/{log_id}", json=data)
            if r.status_code == 200:
                return (True, r.json())
            try:
                detail = r.json().get("detail", "수정 실패")
            except Exception:
                detail = r.text or "수정 실패"
            return (False, detail)
        except Exception as e:
            return (False, str(e))

    def delete_raw_data(self, log_id):
        try:
            r = self.client.delete(f"{self.base_url}/raw-data/{log_id}")
            return r.status_code == 200
        except Exception:
            return False

    def void_log(self, log_id, reason):
        try:
            r = self.client.patch(f"{self.base_url}/raw-data/{log_id}/void", json={"reason": reason})
            return r.status_code == 200
        except Exception:
            return False

    # Company Actions
    def get_companies(self):
        try:
            r = self.client.get(f"{self.base_url}/companies")
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def create_company(self, code, name):
        try:
            r = self.client.post(f"{self.base_url}/companies", json={"code": code, "name": name})
            if r.status_code == 200:
                return True, r.json()
            else:
                detail = r.json().get("detail", "알 수 없는 오류")
                return False, detail
        except Exception as e:
            return False, str(e)

    def update_company(self, cid, code, name):
        try:
            r = self.client.patch(f"{self.base_url}/companies/{cid}", json={"code": code, "name": name})
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None

    def delete_company(self, cid):
        try:
            r = self.client.delete(f"{self.base_url}/companies/{cid}")
            return r.status_code == 200
        except Exception:
            return False

    # Policy Actions
    def get_policies(self):
        try:
            r = self.client.get(f"{self.base_url}/policies")
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def create_policy(self, data):
        try:
            r = self.client.post(f"{self.base_url}/policies", json=data)
            if r.status_code == 200:
                return (True, r.json())
            try:
                detail = r.json().get("detail", "등록 실패")
            except Exception:
                detail = r.text or "등록 실패"
            return (False, detail)
        except Exception as e:
            return (False, str(e))

    def update_policy(self, policy_id, data):
        try:
            r = self.client.put(f"{self.base_url}/policies/{policy_id}", json=data)
            if r.status_code == 200:
                return (True, r.json())
            try:
                detail = r.json().get("detail", "수정 실패")
            except Exception:
                detail = r.text or "수정 실패"
            return (False, detail)
        except Exception as e:
            return (False, str(e))

    def delete_policy(self, policy_id):
        try:
            r = self.client.delete(f"{self.base_url}/policies/{policy_id}")
            return r.status_code == 200
        except: return False

    # Department Actions
    def get_departments(self, company_id=None):
        try:
            params = {"company_id": company_id} if company_id else {}
            r = self.client.get(f"{self.base_url}/departments", params=params)
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def create_department(self, company_id, code, name):
        try:
            r = self.client.post(f"{self.base_url}/departments", json={"company_id": company_id, "code": code, "name": name})
            if r.status_code == 200:
                return True, r.json()
            else:
                detail = r.json().get("detail", "알 수 없는 오류")
                return False, detail
        except Exception as e:
            return False, str(e)

    def update_department(self, did, code, name):
        try:
            r = self.client.patch(f"{self.base_url}/departments/{did}", json={"code": code, "name": name})
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None

    def delete_department(self, did):
        try:
            r = self.client.delete(f"{self.base_url}/departments/{did}")
            return r.status_code == 200
        except Exception:
            return False

    # Employee Actions
    def get_employees(self, search="", status=None):
        try:
            params = {"search": search}
            if status:
                params["status"] = status
            r = self.client.get(f"{self.base_url}/employees", params=params)
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def create_employee(self, data):
        try:
            r = self.client.post(f"{self.base_url}/employees", json=data)
            return (True, r.json()) if r.status_code == 200 else (False, r.json().get("detail", "등록 실패"))
        except Exception as e: return (False, str(e))

    def update_employee(self, emp_id, data):
        try:
            r = self.client.put(f"{self.base_url}/employees/{emp_id}", json=data)
            return (True, r.json()) if r.status_code == 200 else (False, r.json().get("detail", "수정 실패"))
        except Exception as e: return (False, str(e))

    def delete_employee(self, emp_id, permanent=False):
        try:
            # 서버가 bool 쿼리 파라미터를 확실히 인식하도록 1/0 사용
            params = {"permanent": "1"} if permanent else {}
            r = self.client.delete(f"{self.base_url}/employees/{emp_id}", params=params)
            return r.status_code == 200
        except Exception:
            return False

    def get_excel_report_data(self, year, month):
        try:
            r = self.client.get(f"{self.base_url}/reports/excel", params={"year": year, "month": month})
            return r.content if r.status_code == 200 else None
        except Exception:
            return None

    def import_employees_excel(self, company_id, file_content):
        try:
            r = self.client.post(
                f"{self.base_url}/employees/import", 
                params={"company_id": company_id},
                content=file_content
            )
            return (True, r.json()) if r.status_code == 200 else (False, r.json().get("detail", "가져오기 실패"))
        except Exception as e: return (False, str(e))

    def reset_device_auth(self, emp_id):
        try:
            r = self.client.post(f"{self.base_url}/employees/{emp_id}/reset-device")
            return (True, r.json()) if r.status_code == 200 else (False, r.json().get("detail", "초기화 실패"))
        except Exception as e: return (False, str(e))

    def close(self):
        self.client.close()

class StatCard(QFrame):
    def __init__(self, title, icon_text, color):
        super().__init__()
        self.setObjectName("StatCard")
        layout = QVBoxLayout(self)
        self.val_label = QLabel("0")
        self.val_label.setObjectName("StatValue")
        self.title_label = QLabel(title)
        self.title_label.setObjectName("StatLabel")
        layout.addWidget(self.val_label)
        layout.addWidget(self.title_label)
    def set_value(self, val):
        self.val_label.setText(str(val))

class DashboardScreen(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        header_h_layout = QHBoxLayout()
        header = QLabel("오늘의 현황")
        header.setObjectName("HeaderTitle")
        
        # Digital Clock
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("color: #6366f1; font-size: 26px; font-weight: bold; font-family: 'Malgun Gothic'; margin-left: 20px; margin-top: 10px;")
        
        header_h_layout.addWidget(header)
        header_h_layout.addWidget(self.clock_label)
        header_h_layout.addStretch()
        layout.addLayout(header_h_layout)

        # Update clock every second
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()
        
        # Stats layout (Dynamic cards)
        self.stats_layout = QHBoxLayout()
        layout.addLayout(self.stats_layout)
        
        self.cards = {} # Store cards by title
        
        info_frame = QFrame()
        info_frame.setObjectName("StatCard")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(0, 0, 0, 0) # 테이블이 프레임에 꽉 차도록 여백 제거
        self.recent_table = QTableWidget(0, 4)
        self.recent_table.setHorizontalHeaderLabels(["시간", "이름", "부서", "식사종류"])
        setup_standard_table(self.recent_table) # 표준 테이블 스타일 적용
        
        # Fixed height for exactly 17 rows + header
        # Header(50px) + 17 rows * 38px + border/padding
        self.recent_table.setFixedHeight(700)
        
        info_layout.addWidget(self.recent_table)
        layout.addWidget(info_frame, 1)


    def update_clock(self):
        now = datetime.now()
        days = ["월", "화", "수", "목", "금", "토", "일"]
        day_str = days[now.weekday()]
        time_str = now.strftime(f"%m월 %d일({day_str}) %H:%M:%S")
        self.clock_label.setText(time_str)

    def update_stats(self, stats):
        if not stats or not isinstance(stats, dict): return
        
        # Define card data to build
        # Order: Total -> Meal Summaries (Policies) -> Exception
        card_data = []
        card_data.append({"title": "오늘 총 식수", "val": stats.get("total_count", 0), "color": "#6366f1", "icon": "👥"})
        
        # Add meal summaries (Policies)
        colors = ["#8b5cf6", "#10b981", "#f59e0b", "#06b6d4"] # Shared palette
        for i, s in enumerate(stats.get("meal_summaries", [])):
            color = colors[i % len(colors)]
            card_data.append({"title": s["meal_type"], "val": s["count"], "color": color, "icon": "🍱"})
            
        # Add exception (Unified)
        card_data.append({"title": "예외", "val": stats.get("exception_count", 0), "color": "#ef4444", "icon": "⚠️"})
        
        # Refresh cards
        # If card counts match, just update values (for performance)
        if len(self.cards) == len(card_data):
            for item in card_data:
                title = item["title"]
                if title in self.cards:
                    self.cards[title].set_value(item["val"])
                else: 
                    # Rebuild if titles mismatch
                    self._rebuild_cards(card_data)
                    break
        else:
            self._rebuild_cards(card_data)

    def _rebuild_cards(self, card_data):
        # Clear existing
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        self.cards = {}
        
        # Create new
        for item in card_data:
            card = StatCard(item["title"], item["icon"], item["color"])
            card.set_value(item["val"])
            self.stats_layout.addWidget(card)
            self.cards[item["title"]] = card

    def update_recent(self, data):
        if not isinstance(data, list): return
        self.recent_table.setSortingEnabled(False)
        self.recent_table.setUpdatesEnabled(False)
        self.recent_table.setRowCount(len(data))
        kst = timezone(timedelta(hours=9))
        for i, row in enumerate(data):
            if not isinstance(row, dict): continue
            user = row.get("user") or {}
            policy = row.get("policy") or {}
            ts = row.get("created_at", "")
            # 서버(UTC) 기준 created_at → 한국 시간(KST)으로 변환해 표시
            try:
                if isinstance(ts, str):
                    s = ts.replace("Z", "+00:00").replace(" ", "T")
                    if "+" in s or s.endswith("Z"):
                        dt = datetime.fromisoformat(s)
                    else:
                        dt = datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
                    dt_kst = dt.astimezone(kst)
                    ts = dt_kst.strftime("%H:%M")
                else:
                    ts = str(ts)[:8] if ts else ""
            except Exception:
                if isinstance(ts, str) and "T" in ts:
                    ts = ts.split("T")[-1][:5]
                elif isinstance(ts, str) and " " in ts:
                    ts = ts.split(" ")[-1][:5]
                else:
                    ts = str(ts)[:5] if ts else ""
            self.recent_table.setItem(i, 0, QTableWidgetItem(ts[:5] if len(ts) >= 5 else ts))
            self.recent_table.setItem(i, 1, QTableWidgetItem(str(user.get("name", ""))))
            self.recent_table.setItem(i, 2, QTableWidgetItem(str(user.get("department_name", ""))))
            self.recent_table.setItem(i, 3, QTableWidgetItem(str(policy.get("meal_type", ""))))
        self.recent_table.setUpdatesEnabled(True)
        self.recent_table.setSortingEnabled(True)

class CompanyScreen(QWidget):
    def __init__(self, api, main_win):
        super().__init__()
        self.api = api
        self.main_win = main_win
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        header_layout = QHBoxLayout()
        header = QLabel("회사 관리")
        header.setObjectName("HeaderTitle")
        
        reg_frame = QFrame()
        reg_frame.setObjectName("StatCard")
        reg_layout = QHBoxLayout(reg_frame)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("회사코드")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("회사명")
        self.add_btn = QPushButton("등록")
        self.add_btn.setObjectName("PrimaryBtn")
        self.add_btn.setFixedWidth(100)
        self.add_btn.clicked.connect(self.on_add)
        
        self.edit_btn = QPushButton("수정")
        self.edit_btn.setObjectName("SecondaryBtn")
        self.edit_btn.setFixedWidth(100)
        self.edit_btn.clicked.connect(self.on_edit)
        
        self.del_btn = QPushButton("삭제")
        self.del_btn.setObjectName("DangerBtn")
        self.del_btn.setFixedWidth(100)
        self.del_btn.clicked.connect(self.on_delete)
        
        reg_layout.addWidget(self.code_input)
        reg_layout.addWidget(self.name_input)
        reg_layout.addWidget(self.add_btn)
        reg_layout.addWidget(self.edit_btn)
        reg_layout.addWidget(self.del_btn)
        
        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(reg_frame)
        layout.addLayout(header_layout)
        
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["회사코드", "회사명"])
        setup_standard_table(self.table)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.table)

    def on_selection_changed(self):
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            item0 = self.table.item(row, 0)
            item1 = self.table.item(row, 1)
            self.code_input.setText(item0.text() if item0 else "")
            self.name_input.setText(item1.text() if item1 else "")
            cid = item0.data(Qt.UserRole) if item0 else None
            self.edit_btn.setEnabled(cid is not None)
            self.del_btn.setEnabled(cid is not None)
            self.name_input.setFocus()
            self.name_input.selectAll()
        else:
            self.code_input.clear()
            self.name_input.clear()
            self.edit_btn.setEnabled(False)
            self.del_btn.setEnabled(False)
        
    def load_data(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.loader = DataLoader(self.api.get_companies)
        self.loader.finished.connect(self.display_data)
        self.loader.start()

    def display_data(self, data):
        QApplication.restoreOverrideCursor()
        if not isinstance(data, list): return
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            if not isinstance(row, dict): continue
            code = row.get("code", "")
            name = row.get("name", "")
            item_code = QTableWidgetItem(str(code))
            item_code.setData(Qt.UserRole, row.get("id"))
            self.table.setItem(i, 0, item_code)
            self.table.setItem(i, 1, QTableWidgetItem(str(name)))
        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)

    def clear_inputs(self):
        self.code_input.clear()
        self.name_input.clear()
        self.table.clearSelection()
        self.edit_btn.setEnabled(False)
        self.del_btn.setEnabled(False)

    def on_edit(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "경고", "수정할 회사를 선택하세요.")
            return

        row = selected[0].row()
        item0 = self.table.item(row, 0)
        cid = item0.data(Qt.UserRole) if item0 else None
        if cid is None:
            QMessageBox.warning(self, "경고", "선택한 항목을 수정할 수 없습니다.")
            return
        code = self.code_input.text()
        name = self.name_input.text()
        
        self.edit_btn.setEnabled(False)
        self.main_win.statusBar().showMessage("수정 중...", 2000)
        self.edit_loader = DataLoader(self.api.update_company, cid, code, name)
        self.edit_loader.finished.connect(self.on_edit_finished)
        self.edit_loader.start()

    def on_edit_finished(self, data):
        self.edit_btn.setEnabled(True)
        if data:
            self.main_win.statusBar().showMessage("수정되었습니다.", 3000)
            selected = self.table.selectedItems()
            if selected:
                row = selected[0].row()
                item0 = self.table.item(row, 0)
                if item0 is not None:
                    self.table.setItem(row, 0, QTableWidgetItem(data.get("code", "")))
                    self.table.item(row, 0).setData(Qt.UserRole, data.get("id"))
                self.table.setItem(row, 1, QTableWidgetItem(str(data.get("name", ""))))
            self.main_win.on_company_changed()
            QMessageBox.information(self, "성공", "수정되었습니다.")
            self.clear_inputs()
        else:
            QMessageBox.warning(self, "오류", "수정에 실패했습니다.")

    def on_delete(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "경고", "삭제할 회사를 선택하세요.")
            return

        row = selected[0].row()
        item0 = self.table.item(row, 0)
        item1 = self.table.item(row, 1)
        cid = item0.data(Qt.UserRole) if item0 else None
        if cid is None:
            QMessageBox.warning(self, "경고", "선택한 항목을 삭제할 수 없습니다.")
            return
        name = item1.text() if item1 else "(선택 행)"
        
        reply = QMessageBox.question(self, "삭제 확인", f"'{name}' 회사를 정말 삭제하시겠습니까?\n관련 부서 및 사원 데이터에 영향을 줄 수 있습니다.",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.del_btn.setEnabled(False)
            self.main_win.statusBar().showMessage("삭제 중...", 2000)
            self.del_loader = DataLoader(self.api.delete_company, cid)
            self.del_loader.finished.connect(self.on_delete_finished)
            self.del_loader.start()

    def on_delete_finished(self, success):
        self.del_btn.setEnabled(True)
        if success:
            self.main_win.statusBar().showMessage("삭제되었습니다.", 3000)
            selected = self.table.selectedItems()
            if selected:
                row = selected[0].row()
                self.table.removeRow(row) # UI에서 즉시 제거
                self.main_win.on_company_changed()
            QMessageBox.information(self, "성공", "삭제되었습니다.")
            self.clear_inputs()
            self.load_data() # 데이터 서버와 동기화
        else:
            QMessageBox.warning(self, "오류", "삭제에 실패했습니다.")
            
    def on_add(self):
        code = self.code_input.text()
        name = self.name_input.text()
        if not code or not name:
            QMessageBox.warning(self, "경고", "코드와 이름을 입력하세요.")
            return
        
        # Optimistic UI update: Insert row immediately
        pos = self.table.rowCount()
        self.table.insertRow(pos)
        item_code = QTableWidgetItem(code)
        item_code.setData(Qt.UserRole, None) # Pending ID
        self.table.setItem(pos, 0, item_code)
        self.table.setItem(pos, 1, QTableWidgetItem(name))
        
        self.main_win.statusBar().showMessage(f"'{name}' 등록 중...", 2000)
        self.add_btn.setEnabled(False)
        self.add_loader = DataLoader(self.api.create_company, code, name)
        self.add_loader.finished.connect(self.on_add_finished)
        self.add_loader.error.connect(self.on_add_error)
        self.add_loader.start()

    def on_add_error(self, e):
        self.add_btn.setEnabled(True)
        self.load_data() # Rollback optimistic change by reloading
        QMessageBox.critical(self, "치명적 오류", f"스레드 오류: {e}")

    def on_add_finished(self, result):
        self.add_btn.setEnabled(True)
        success, data = result if isinstance(result, tuple) else (False, str(result))
        if success and isinstance(data, dict):
            self.main_win.statusBar().showMessage("회사가 등록되었습니다.", 3000)
            for i in range(self.table.rowCount()):
                item0 = self.table.item(i, 0)
                if item0 is not None and item0.data(Qt.UserRole) is None:
                    item0.setData(Qt.UserRole, data.get("id"))
                    break
            self.main_win.on_company_changed()
            QMessageBox.information(self, "성공", "등록되었습니다.")
            self.clear_inputs()
        else:
            self.load_data()
            msg = data if isinstance(data, str) else "등록 실패"
            QMessageBox.warning(self, "오류", f"등록에 실패했습니다: {msg}")

class DepartmentScreen(QWidget):
    def __init__(self, api, main_win):
        super().__init__()
        self.api = api
        self.main_win = main_win
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        header_layout = QHBoxLayout()
        header = QLabel("부서 관리")
        header.setObjectName("HeaderTitle")
        
        reg_frame = QFrame()
        reg_frame.setObjectName("StatCard")
        reg_layout = QHBoxLayout(reg_frame)
        self.company_combo = QComboBox()
        self.company_combo.setItemDelegate(QStyledItemDelegate())
        self.company_combo.setFixedWidth(200)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("부서코드")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("부서명")
        self.add_btn = QPushButton("등록")
        self.add_btn.setObjectName("PrimaryBtn")
        self.add_btn.setFixedWidth(100)
        self.add_btn.clicked.connect(self.on_add)
        
        self.edit_btn = QPushButton("수정")
        self.edit_btn.setObjectName("SecondaryBtn")
        self.edit_btn.setFixedWidth(100)
        self.edit_btn.clicked.connect(self.on_edit)
        
        self.del_btn = QPushButton("삭제")
        self.del_btn.setObjectName("DangerBtn")
        self.del_btn.setFixedWidth(100)
        self.del_btn.clicked.connect(self.on_delete)
        
        reg_layout.addWidget(self.company_combo)
        reg_layout.addWidget(self.code_input)
        reg_layout.addWidget(self.name_input)
        reg_layout.addWidget(self.add_btn)
        reg_layout.addWidget(self.edit_btn)
        reg_layout.addWidget(self.del_btn)
        
        # Connect combo change to filtering
        self.company_combo.currentIndexChanged.connect(self.load_data)
        
        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(reg_frame)
        layout.addLayout(header_layout)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["회사", "부서코드", "부서명"])
        setup_standard_table(self.table)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.table)

    def on_selection_changed(self):
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            item0 = self.table.item(row, 0)
            comp_id = item0.data(Qt.UserRole + 1) if item0 else None
            if comp_id is not None:
                idx = self.company_combo.findData(comp_id)
                if idx >= 0:
                    self.company_combo.setCurrentIndex(idx)
            item1 = self.table.item(row, 1)
            item2 = self.table.item(row, 2)
            self.code_input.setText(item1.text() if item1 else "")
            self.name_input.setText(item2.text() if item2 else "")
            dept_id = item0.data(Qt.UserRole) if item0 else None
            self.edit_btn.setEnabled(dept_id is not None)
            self.del_btn.setEnabled(dept_id is not None)
            self.name_input.setFocus()
            self.name_input.selectAll()
        else:
            self.code_input.clear()
            self.name_input.clear()
            self.edit_btn.setEnabled(False)
            self.del_btn.setEnabled(False)
    def clear_inputs(self):
        self.code_input.clear()
        self.name_input.clear()
        self.table.clearSelection()
        self.edit_btn.setEnabled(False)
        self.del_btn.setEnabled(False)

    def update_company_combo(self, companies):
        self.company_combo.blockSignals(True)
        self.company_combo.clear()
        self.company_combo.addItem("** 선택 **", None)
        for c in companies:
            if isinstance(c, dict):
                self.company_combo.addItem(c["name"], c["id"])
        self.company_combo.blockSignals(False)

    def load_data(self):
        cid = self.company_combo.currentData()
        if cid is None:
            self.table.setRowCount(0)
            return

        try:
            cid_int = int(cid)
        except (TypeError, ValueError):
            cid_int = None
        if cid_int is None:
            self.table.setRowCount(0)
            return

        # Optimization: Use local cache from main window (match company_id as int)
        dept_list = [
            d for d in self.main_win.departments_data
            if isinstance(d, dict) and d.get("company_id") is not None and int(d.get("company_id")) == cid_int
        ]
        self.display_data(dept_list)

    def display_data(self, data):
        QApplication.restoreOverrideCursor()
        if not isinstance(data, list): return
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(data))

        # Create mapping for company names
        comp_map = {c["id"]: c["name"] for c in self.main_win.companies_data if isinstance(c, dict)}

        for i, row in enumerate(data):
            if not isinstance(row, dict): continue
            cid = row.get("company_id")
            comp_name = comp_map.get(cid, str(cid)) if cid is not None else ""
            item_comp = QTableWidgetItem(comp_name)
            item_comp.setData(Qt.UserRole, row.get("id"))
            item_comp.setData(Qt.UserRole + 1, cid)
            self.table.setItem(i, 0, item_comp)
            code = row.get("code")
            name = row.get("name")
            self.table.setItem(i, 1, QTableWidgetItem(str(code) if code is not None else ""))
            self.table.setItem(i, 2, QTableWidgetItem(str(name) if name is not None else ""))
        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)

    def on_edit(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "경고", "수정할 부서를 선택하세요.")
            return
        
        row = selected[0].row()
        did = self.table.item(row, 0).data(Qt.UserRole)
        if did is None:
            QMessageBox.warning(self, "경고", "선택한 항목을 수정할 수 없습니다.")
            return
        code = self.code_input.text()
        name = self.name_input.text()
        
        self.edit_btn.setEnabled(False)
        self.main_win.statusBar().showMessage("부서 수정 중...", 2000)
        self.edit_loader = DataLoader(self.api.update_department, did, code, name)
        self.edit_loader.finished.connect(self.on_edit_finished)
        self.edit_loader.start()

    def on_edit_finished(self, data):
        self.edit_btn.setEnabled(True)
        if data:
            self.main_win.statusBar().showMessage("수정되었습니다.", 3000)
            # Update local cache in main window
            for i, d in enumerate(self.main_win.departments_data):
                if d["id"] == data["id"]:
                    self.main_win.departments_data[i] = data
                    break
            
            QMessageBox.information(self, "성공", "수정되었습니다.")
            self.clear_inputs()
            self.load_data()
        else:
            QMessageBox.warning(self, "오류", "수정에 실패했습니다.")

    def on_delete(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "경고", "삭제할 부서를 선택하세요.")
            return
            
        row = selected[0].row()
        did = self.table.item(row, 0).data(Qt.UserRole)
        if did is None:
            QMessageBox.warning(self, "경고", "선택한 항목을 삭제할 수 없습니다.")
            return
        name_item = self.table.item(row, 2)
        name = name_item.text() if name_item else "(선택 행)"
        
        reply = QMessageBox.question(self, "삭제 확인", f"'{name}' 부서를 정말 삭제하시겠습니까?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.del_btn.setEnabled(False)
            self.main_win.statusBar().showMessage("부서 삭제 중...", 2000)
            self.del_loader = DataLoader(self.api.delete_department, did)
            self.del_loader.finished.connect(self.on_delete_finished)
            self.del_loader.start()

    def on_delete_finished(self, success):
        self.del_btn.setEnabled(True)
        if success:
            self.main_win.statusBar().showMessage("삭제되었습니다.", 3000)
            selected = self.table.selectedItems()
            if selected:
                row = selected[0].row()
                target_did = self.table.item(row, 0).data(Qt.UserRole)
                self.main_win.departments_data = [d for d in self.main_win.departments_data if d["id"] != target_did]
                self.table.removeRow(row)
            self.main_win.sync_departments()
            QMessageBox.information(self, "성공", "삭제되었습니다.")
            self.clear_inputs()
            self.load_data()
        else:
            QMessageBox.warning(self, "오류", "삭제에 실패했습니다.")

    def on_add(self):
        cid = self.company_combo.currentData()
        code = self.code_input.text()
        name = self.name_input.text()
        if not cid or not code or not name:
            QMessageBox.warning(self, "경고", "회사 선택 및 코드/이름을 입력하세요.")
            return

        # Optimistic UI update
        pos = self.table.rowCount()
        self.table.insertRow(pos)
        comp_name = self.company_combo.currentText()
        item_comp = QTableWidgetItem(comp_name)
        item_comp.setData(Qt.UserRole, None)
        item_comp.setData(Qt.UserRole + 1, cid)
        self.table.setItem(pos, 0, item_comp)
        self.table.setItem(pos, 1, QTableWidgetItem(code))
        self.table.setItem(pos, 2, QTableWidgetItem(name))

        self.add_btn.setEnabled(False)
        self.add_loader = DataLoader(self.api.create_department, cid, code, name)
        self.add_loader.finished.connect(self.on_add_finished)
        self.add_loader.error.connect(self.on_add_error)
        self.add_loader.start()

    def on_add_error(self, e):
        self.add_btn.setEnabled(True)
        self.load_data()
        QMessageBox.critical(self, "치명적 오류", f"스레드 오류: {e}")

    def on_add_finished(self, result):
        self.add_btn.setEnabled(True)
        success, data = result if isinstance(result, tuple) else (False, str(result))
        if success and isinstance(data, dict):
            self.main_win.statusBar().showMessage("부서가 등록되었습니다.", 3000)
            self.main_win.departments_data.append(data)
            # Refresh table from cache so all rows (existing + new) show code/name correctly (avoids sort/row glitches)
            self.load_data()
            QMessageBox.information(self, "성공", "등록되었습니다.")
            self.clear_inputs()
        else:
            self.main_win.sync_departments()
            msg = data if isinstance(data, str) else "등록 실패"
            QMessageBox.warning(self, "오류", f"등록에 실패했습니다: {msg}")

class EmployeeScreen(QWidget):
    def __init__(self, api, main_win):
        super().__init__()
        self.api = api
        self.main_win = main_win
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        header = QLabel("사원 관리")
        header.setObjectName("HeaderTitle")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("사번 또는 이름 검색...")
        self.search_input.setFixedWidth(250)
        
        self.refresh_btn = QPushButton("새로고침")
        self.refresh_btn.setFixedWidth(80)
        self.refresh_btn.clicked.connect(self.load_data)
        
        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(self.search_input)
        layout.addLayout(header_layout)

        # Registration Frame
        reg_frame = QFrame()
        reg_frame.setObjectName("StatCard")
        reg_layout = QHBoxLayout(reg_frame)
        
        self.company_combo = QComboBox()
        self.company_combo.setItemDelegate(QStyledItemDelegate())
        self.company_combo.setPlaceholderText("회사")
        self.company_combo.setFixedWidth(180)
        
        self.dept_combo = QComboBox()
        self.dept_combo.setItemDelegate(QStyledItemDelegate())
        self.dept_combo.setPlaceholderText("부서")
        self.dept_combo.setFixedWidth(180)
        
        self.emp_no_input = QLineEdit()
        self.emp_no_input.setPlaceholderText("사번")
        self.emp_no_input.setFixedWidth(120)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("이름")
        self.name_input.setFixedWidth(150)
        
        
        self.add_btn = QPushButton("등록")
        self.add_btn.setObjectName("PrimaryBtn")
        self.add_btn.setFixedWidth(100)
        self.add_btn.clicked.connect(self.on_add)
        
        self.edit_btn = QPushButton("수정")
        self.edit_btn.setObjectName("SecondaryBtn")
        self.edit_btn.setFixedWidth(100)
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.on_edit)
        
        self.del_btn = QPushButton("삭제(퇴사)")
        self.del_btn.setObjectName("DangerBtn")
        self.del_btn.setFixedWidth(100)
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self.on_delete)

        self.permanent_del_btn = QPushButton("완전 삭제")
        self.permanent_del_btn.setObjectName("DangerBtn")
        self.permanent_del_btn.setFixedWidth(100)
        self.permanent_del_btn.setEnabled(False)
        self.permanent_del_btn.setToolTip("DB에서 제거하여 같은 사번으로 재등록 가능")
        self.permanent_del_btn.clicked.connect(self.on_permanent_delete)
        
        self.reset_btn = QPushButton("기기 초기화")
        self.reset_btn.setObjectName("SecondaryBtn")
        self.reset_btn.setFixedWidth(110)
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self.on_reset_device)

        self.import_btn = QPushButton("엑셀 일괄등록")
        self.import_btn.setObjectName("SecondaryBtn")
        self.import_btn.setFixedWidth(120)
        self.import_btn.clicked.connect(self.on_import_excel)
        
        reg_layout.addWidget(self.company_combo)
        reg_layout.addWidget(self.dept_combo)
        reg_layout.addWidget(self.emp_no_input)
        reg_layout.addWidget(self.name_input)
        reg_layout.addWidget(self.add_btn)
        reg_layout.addWidget(self.edit_btn)
        reg_layout.addWidget(self.del_btn)
        reg_layout.addWidget(self.permanent_del_btn)
        reg_layout.addWidget(self.reset_btn)
        reg_layout.addWidget(self.import_btn)
        layout.addWidget(reg_frame)

        # Table (재직+퇴사 한 테이블, 상태 컬럼 추가)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["사번", "회사", "이름", "부서", "인증", "상태"])
        setup_standard_table(self.table)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.table)

        # Connections
        self.search_input.textChanged.connect(self.load_data)
        self.company_combo.currentIndexChanged.connect(self.update_dept_combo)

    def update_company_combo(self, companies):
        self.company_combo.blockSignals(True)
        self.company_combo.clear()
        self.company_combo.addItem("** 선택 **", None)
        for c in companies:
            if isinstance(c, dict):
                self.company_combo.addItem(c["name"], c["id"])
        self.company_combo.blockSignals(False)
        self.update_dept_combo()

    def update_dept_combo(self):
        cid = self.company_combo.currentData()
        self.dept_combo.clear()
        self.dept_combo.addItem("** 선택 **", None)
        if cid is not None:
            depts = [d for d in self.main_win.departments_data if d.get("company_id") == cid]
            for d in depts:
                self.dept_combo.addItem(d["name"], d["id"]) # Use ID as data

    def on_selection_changed(self):
        self.edit_btn.setEnabled(False)
        self.del_btn.setEnabled(False)
        self.permanent_del_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            item0 = self.table.item(row, 0)
            item1 = self.table.item(row, 1)
            item2 = self.table.item(row, 2)
            item3 = self.table.item(row, 3)
            item5 = self.table.item(row, 5)
            emp_no = item0.text() if item0 else ""
            comp_name = item1.text() if item1 else ""
            name = item2.text() if item2 else ""
            dept_name = item3.text() if item3 else ""
            status_text = (item5.text() if item5 else "").strip()

            self.emp_no_input.setText(emp_no)
            self.name_input.setText(name)

            idx = self.company_combo.findText(comp_name)
            if idx >= 0: self.company_combo.setCurrentIndex(idx)

            idx = self.dept_combo.findText(dept_name)
            if idx >= 0: self.dept_combo.setCurrentIndex(idx)

            if item0 and item0.data(Qt.UserRole) is not None:
                self.edit_btn.setEnabled(True)
                self.permanent_del_btn.setEnabled(True)
                if status_text == "재직":
                    self.del_btn.setEnabled(True)
                    self.reset_btn.setEnabled(True)
                else:
                    self.del_btn.setEnabled(False)
                    self.reset_btn.setEnabled(False)

    def clear_inputs(self):
        self.emp_no_input.clear()
        self.name_input.clear()
        self.table.clearSelection()
        self.edit_btn.setEnabled(False)
        self.del_btn.setEnabled(False)
        self.permanent_del_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)

    def on_add(self):
        cid = self.company_combo.currentData()
        did = self.dept_combo.currentData()
        emp_no = self.emp_no_input.text().strip()
        name = self.name_input.text().strip()
        
        if not cid or not emp_no or not name:
            QMessageBox.warning(self, "경고", "모든 정보를 입력하세요.")
            return

        payload = {
            "company_id": cid,
            "department_id": did,
            "emp_no": emp_no,
            "name": name,
            "status": "ACTIVE"
        }
        
        self.main_win.statusBar().showMessage("사원 등록 중...", 5000)
        self.add_btn.setEnabled(False)
        self.loader = DataLoader(self.api.create_employee, payload)
        self.loader.finished.connect(self.on_action_finished)
        self.loader.error.connect(self.on_action_error)
        self.loader.start()

    def on_edit(self):
        selected = self.table.selectedItems()
        if not selected: return
        row = selected[0].row()
        item0 = self.table.item(row, 0)
        eid = item0.data(Qt.UserRole) if item0 else None
        if eid is None: return
        
        cid = self.company_combo.currentData()
        did = self.dept_combo.currentData()
        emp_no = self.emp_no_input.text().strip()
        name = self.name_input.text().strip()

        payload = {
            "company_id": cid,
            "department_id": did,
            "emp_no": emp_no,
            "name": name
        }
        
        self.loader = DataLoader(self.api.update_employee, eid, payload)
        self.loader.finished.connect(self.on_action_finished)
        self.loader.start()

    def on_import_excel(self):
        cid = self.company_combo.currentData()
        if not cid:
            QMessageBox.warning(self, "경고", "먼저 회사를 선택해 주세요.")
            return
            
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "사원 엑셀 파일 선택", "", "Excel Files (*.xlsx *.xls)")
        if not file_path: return
        
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            self.import_btn.setEnabled(False)
            self.main_win.statusBar().showMessage("엑셀 데이터 업로드 중...", 5000)
            self.import_loader = DataLoader(self.api.import_employees_excel, cid, file_content)
            self.import_loader.finished.connect(self.on_import_finished)
            self.import_loader.start()
        except Exception as e:
            QMessageBox.critical(self, "오류", f" 파일을 읽을 수 없습니다: {str(e)}")

    def on_import_finished(self, result):
        self.import_btn.setEnabled(True)
        success, data = result if isinstance(result, tuple) else (False, result)
        if success:
            msg = data.get("message", "완료되었습니다.")
            QMessageBox.information(self, "임포트 성공", msg)
            self.load_data() # Refresh table
        else:
            QMessageBox.warning(self, "임포트 실패", str(data))

    def on_delete(self):
        selected = self.table.selectedItems()
        if not selected: return
        row = selected[0].row()
        item0 = self.table.item(row, 0)
        eid = item0.data(Qt.UserRole) if item0 else None
        if eid is None: return
        
        if QMessageBox.question(self, "확인", "정말 이 사원을 삭제(퇴사) 처리하시겠습니까?\n(DB에는 남아 있어 같은 사번으로 재등록 시 '재등록' 처리됩니다.)") == QMessageBox.Yes:
            self.del_btn.setEnabled(False)
            self.permanent_del_btn.setEnabled(False)
            self.loader = DataLoader(self.api.delete_employee, eid, False)
            self.loader.finished.connect(self.on_delete_finished)
            self.loader.error.connect(self.on_action_error)
            self.loader.start()

    def on_permanent_delete(self):
        selected = self.table.selectedItems()
        if not selected: return
        row = selected[0].row()
        item0 = self.table.item(row, 0)
        item5 = self.table.item(row, 5)
        eid = item0.data(Qt.UserRole) if item0 else None
        if eid is None: return
        name_item = self.table.item(row, 2)
        name = name_item.text() if name_item else "(선택 행)"
        status_text = (item5.text() if item5 else "").strip()

        if status_text == "재직":
            msg = (
                f"'{name}' 사원은 재직자입니다.\n"
                "완전 삭제하면 DB에서 제거되며, 모든 식사 기록도 삭제됩니다.\n"
                "정말 삭제하시겠습니까?"
            )
        else:
            msg = (
                f"'{name}' 사원을 DB에서 완전히 제거합니다.\n"
                "같은 사번으로 다시 등록할 수 있습니다.\n"
                "관련 식사 기록도 삭제됩니다. 계속하시겠습니까?"
            )
        if QMessageBox.question(
            self, "완전 삭제 확인", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) == QMessageBox.Yes:
            self.del_btn.setEnabled(False)
            self.permanent_del_btn.setEnabled(False)
            self.loader = DataLoader(self.api.delete_employee, eid, True)
            self.loader.finished.connect(self.on_delete_finished)
            self.loader.error.connect(self.on_action_error)
            self.loader.start()

    def on_delete_finished(self, success):
        self.del_btn.setEnabled(True)
        self.permanent_del_btn.setEnabled(True)
        if success:
            # 서버 상태 기준으로 다시 로드해 삭제 반영 보장
            self.clear_inputs()
            self.load_data()
            QMessageBox.information(self, "성공", "삭제되었습니다.")
        else:
            QMessageBox.warning(self, "오류", "삭제에 실패했습니다.")

    def on_reset_device(self):
        selected = self.table.selectedItems()
        if not selected: return
        row = selected[0].row()
        item0 = self.table.item(row, 0)
        eid = item0.data(Qt.UserRole) if item0 else None
        if eid is None: return
        name_item = self.table.item(row, 2)
        name = name_item.text() if name_item else "(선택 행)"
        
        if QMessageBox.question(self, "확인", f"'{name}' 사원의 기기 인증 상태 및 비밀번호를 초기화하시겠습니까?") == QMessageBox.Yes:
            self.reset_btn.setEnabled(False)
            self.loader = DataLoader(self.api.reset_device_auth, eid)
            self.loader.finished.connect(self.on_action_finished)
            self.loader.error.connect(self.on_action_error)
            self.loader.start()

    def on_action_finished(self, result):
        self.add_btn.setEnabled(True)
        self.edit_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        if isinstance(result, tuple):
            success, data = result
        else:
            success, data = bool(result), None
        if success:
            QMessageBox.information(self, "성공", "작업이 완료되었습니다.")
            self.load_data()
            self.clear_inputs()
        else:
            msg = str(data) if data is not None else "작업에 실패했습니다."
            QMessageBox.warning(self, "오류", msg)

    def on_action_error(self, err_msg):
        self.add_btn.setEnabled(True)
        self.edit_btn.setEnabled(True)
        self.del_btn.setEnabled(True)
        self.permanent_del_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        QMessageBox.critical(self, "네트워크 오류", f"서버 통신 중 오류가 발생했습니다:\n{err_msg}")

    def load_data(self):
        # 재직+퇴사 모두 조회 (status 없음 = 전체)
        self.loader = DataLoader(self.api.get_employees, self.search_input.text(), None)
        self.loader.finished.connect(self.display_data)
        self.loader.start()

    def display_data(self, data):
        if not isinstance(data, list): return

        selected_ids = set()
        for item in self.table.selectedItems():
            if item.column() == 0 and item.data(Qt.UserRole) is not None:
                selected_ids.add(item.data(Qt.UserRole))

        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(data))
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["사번", "회사", "이름", "부서", "인증", "상태"])

        comp_map = {c["id"]: c["name"] for c in self.main_win.companies_data if isinstance(c, dict)}
        dept_map = {d["id"]: d["name"] for d in self.main_win.departments_data if isinstance(d, dict)}

        for i, row in enumerate(data):
            if not isinstance(row, dict): continue
            item_no = QTableWidgetItem(str(row.get("emp_no", "")))
            row_id = row.get("id")
            item_no.setData(Qt.UserRole, row_id)

            comp_name = comp_map.get(row.get("company_id"), "Unknown")
            dept_name = dept_map.get(row.get("department_id"), "Unknown")
            status_label = "재직" if row.get("status") == "ACTIVE" else "퇴사"

            self.table.setItem(i, 0, item_no)
            self.table.setItem(i, 1, QTableWidgetItem(comp_name))
            self.table.setItem(i, 2, QTableWidgetItem(str(row.get("name", ""))))
            self.table.setItem(i, 3, QTableWidgetItem(dept_name))

            is_verified = row.get("is_verified", False)
            auth_status = "O" if is_verified else "X"
            item_auth = QTableWidgetItem(auth_status)
            if not is_verified:
                item_auth.setForeground(QColor("#ef4444"))
            else:
                item_auth.setForeground(QColor("#10b981"))
            self.table.setItem(i, 4, item_auth)

            item_status = QTableWidgetItem(status_label)
            self.table.setItem(i, 5, item_status)

            if row.get("status") == "RESIGNED":
                for col in range(6):
                    it = self.table.item(i, col)
                    if it: it.setForeground(QColor("#999999"))

            if row_id in selected_ids:
                for col in range(6):
                    it = self.table.item(i, col)
                    if it: it.setSelected(True)

        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)

class RawDataScreen(QWidget):
    def __init__(self, api, main_win):
        super().__init__()
        self.api = api
        self.main_win = main_win
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        header_layout = QHBoxLayout()
        header = QLabel("원시 데이터 관리")
        header.setObjectName("HeaderTitle")
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate())
        self.start_date_edit.setFixedWidth(180)

        tilde = QLabel("~")
        tilde.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setFixedWidth(180)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("사번 또는 성명 검색...")
        self.search_input.setFixedWidth(250)
        self.search_input.returnPressed.connect(self.load_data)

        self.search_btn = QPushButton("조회")
        self.search_btn.setObjectName("PrimaryBtn")
        self.search_btn.setFixedWidth(80)
        self.search_btn.clicked.connect(self.load_data)
        
        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(self.start_date_edit)
        header_layout.addWidget(tilde)
        header_layout.addWidget(self.end_date_edit)
        header_layout.addSpacing(10)
        header_layout.addWidget(self.search_input)
        header_layout.addWidget(self.search_btn)

        # Main layout structure: Left (Table) / Right (Inputs)
        main_h_layout = QHBoxLayout()
        layout.addLayout(main_h_layout)
        
        # Left side: Table Area
        left_layout = QVBoxLayout()
        left_layout.addLayout(header_layout)
        
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["No", "날짜", "시간", "이름", "사번", "식사종류", "경로", "상태"])
        setup_standard_table(self.table)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 80)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.table)
        main_h_layout.addLayout(left_layout, 7) # 70% width
        
        # Right side: Input Panel
        self.input_panel = QFrame()
        self.input_panel.setObjectName("StatCard")
        self.input_panel.setFixedWidth(350)
        input_layout = QVBoxLayout(self.input_panel)
        input_layout.setSpacing(15)
        
        panel_title = QLabel("기록 등록/수정")
        panel_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #6366f1; margin-bottom: 10px;")
        input_layout.addWidget(panel_title)
        
        # Date & Time
        date_label = QLabel("날짜")
        date_label.setObjectName("InputLabel")
        self.edit_date = QDateEdit()
        self.edit_date.setCalendarPopup(True)
        self.edit_date.setDate(QDate.currentDate())
        self.edit_date.setFixedHeight(40)
        
        time_label = QLabel("시간")
        time_label.setObjectName("InputLabel")
        self.edit_time = QTimeEdit()
        self.edit_time.setTime(QTime.currentTime())
        self.edit_time.setFixedHeight(40)
        
        # Employee Search
        emp_label = QLabel("사원 검색 (이름)")
        emp_label.setObjectName("InputLabel")
        search_h = QHBoxLayout()
        self.emp_search_input = QLineEdit()
        self.emp_search_input.setPlaceholderText("검색 버튼을 클릭하세요...")
        self.emp_search_input.setReadOnly(True)
        self.emp_search_btn = QPushButton("검색")
        self.emp_search_btn.setObjectName("PrimaryBtn")
        self.emp_search_btn.setFixedWidth(100)
        self.emp_search_btn.clicked.connect(self.on_search_employee)
        search_h.addWidget(self.emp_search_input)
        search_h.addWidget(self.emp_search_btn)
        
        self.selected_emp_label = QLabel("선택된 사원: 없음")
        self.selected_emp_label.setStyleSheet("color: #94a3b8; font-size: 16px;")
        self.selected_user_id = None
        
        # Meal Policy (Meal Type)
        policy_label = QLabel("식사 종류")
        policy_label.setObjectName("InputLabel")
        self.policy_combo = QComboBox()
        self.policy_combo.setFixedHeight(40)
        self.policy_combo.addItem("선택하세요", None)
        self.policy_combo.currentIndexChanged.connect(self.on_policy_changed)
        
        # Policies data for auto-time
        self.policies_list = []
        self.load_policies()
        
        guest_label = QLabel("게스트 인원")
        guest_label.setObjectName("InputLabel")
        self.edit_guest = QLineEdit("0")
        self.edit_guest.setFixedHeight(40)
        
        # Add to input layout
        for label, widget in [
            (emp_label, None), (None, search_h), (None, self.selected_emp_label),
            (date_label, self.edit_date), (time_label, self.edit_time),
            (policy_label, self.policy_combo), (guest_label, self.edit_guest)
        ]:
            if label: input_layout.addWidget(label)
            if widget: 
                if isinstance(widget, QLayout): input_layout.addLayout(widget)
                else: input_layout.addWidget(widget)
        
        input_layout.addStretch()
        
        # Action Buttons
        btn_layout = QVBoxLayout()
        self.add_btn = QPushButton("기록 등록")
        self.add_btn.setObjectName("PrimaryBtn")
        self.add_btn.clicked.connect(self.on_add)
        
        self.edit_btn = QPushButton("기록 수정")
        self.edit_btn.setObjectName("SecondaryBtn")
        self.edit_btn.clicked.connect(self.on_update)
        self.edit_btn.setEnabled(False)
        
        self.del_btn = QPushButton("기록 삭제")
        self.del_btn.setObjectName("DangerBtn")
        self.del_btn.clicked.connect(self.on_delete)
        self.del_btn.setEnabled(False)
        
        self.clear_btn = QPushButton("입력창 초기화")
        self.clear_btn.clicked.connect(self.clear_inputs)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addSpacing(10)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addWidget(self.clear_btn)
        input_layout.addLayout(btn_layout)
        
        main_h_layout.addWidget(self.input_panel)
        self.current_log_id = None
    def load_data(self):
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        self.loader = DataLoader(self.api.get_raw_data, self.search_input.text(), start_date, end_date)
        self.loader.finished.connect(self.display_data)
        self.loader.start()
    def display_data(self, data):
        if not isinstance(data, list): return
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(data))
        self.full_data = data
        for i, row in enumerate(data):
            if not isinstance(row, dict): continue
            created_at = row.get("created_at", "")
            date_part = created_at.split("T")[0]
            time_part = created_at.split("T")[-1][:8]
            
            # Row Number (No) - Use numeric data for sorting
            item_no = QTableWidgetItem()
            item_no.setData(Qt.DisplayRole, i + 1)
            row_id = row.get("id")
            item_no.setData(Qt.UserRole, row_id)
            
            self.table.setItem(i, 0, item_no)
            self.table.setItem(i, 1, QTableWidgetItem(date_part))
            self.table.setItem(i, 2, QTableWidgetItem(time_part))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("user", {}).get("name", ""))))
            self.table.setItem(i, 4, QTableWidgetItem(str(row.get("user", {}).get("emp_no", ""))))
            
            # Dynamic Meal Type based on time
            meal_type = self.get_meal_type_by_time(time_part)
            item_type = QTableWidgetItem(meal_type)
            if meal_type == "번외":
                item_type.setForeground(QColor("#94a3b8")) # Gray color for extra
            self.table.setItem(i, 5, item_type)
            
            self.table.setItem(i, 6, QTableWidgetItem(str(row.get("path", ""))))
            status = "취소됨" if row.get("is_void") else "정상"
            self.table.setItem(i, 7, QTableWidgetItem(status))
        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)

    def load_policies(self):
        self.pol_loader = DataLoader(self.api.get_policies)
        self.pol_loader.finished.connect(self.on_policies_loaded)
        self.pol_loader.start()

    def on_policies_loaded(self, data):
        if not isinstance(data, list): return
        self.policies_list = data
        self.policy_combo.clear()
        self.policy_combo.addItem("선택하세요", None)
        for p in data:
            self.policy_combo.addItem(p["meal_type"], p["id"])

    def on_policy_changed(self, idx):
        if idx <= 0: return
        policy_id = self.policy_combo.currentData()
        policy = next((p for p in self.policies_list if p["id"] == policy_id), None)
        if policy and policy.get("start_time"):
            # Set time to start_time + 5 minutes
            try:
                h, m = map(int, policy["start_time"].split(":")[:2])
                qtime = QTime(h, m).addSecs(300) # 5 mins
                self.edit_time.setTime(qtime)
            except: pass

    def get_meal_type_by_time(self, time_str):
        if not time_str: return "번외"
        try:
            h, m, s = map(int, time_str.split(":"))
            target_time = QTime(h, m, s)
            
            for p in self.policies_list:
                if not p.get("start_time") or not p.get("end_time"): continue
                
                # Times from API are HH:MM:SS
                sh, sm, ss = map(int, p["start_time"].split(":")[:3])
                eh, em, es = map(int, p["end_time"].split(":")[:3])
                
                start = QTime(sh, sm, ss)
                end = QTime(eh, em, es)
                
                if start <= end:
                    if start <= target_time <= end:
                        return p["meal_type"]
                else: # Overnight
                    if target_time >= start or target_time <= end:
                        return p["meal_type"]
            return "번외"
        except Exception as e:
            print(f"Error judging meal type: {e}")
            return "번외"

    def on_search_employee(self):
        dialog = EmployeeSearchDialog(self.api, self.main_win, self)
        if dialog.exec_():
            emp = dialog.selected_employee
            if emp:
                self.selected_user_id = emp["id"]
                self.emp_search_input.setText(emp['name'])
                self.selected_emp_label.setText(f"선택됨: {emp['name']} ({emp['emp_no']})")

    def on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            self.current_log_id = None
            self.add_btn.setEnabled(True)
            self.edit_btn.setEnabled(False)
            self.del_btn.setEnabled(False)
            return

        row_idx = selected[0].row()
        item0 = self.table.item(row_idx, 0)
        log_id = item0.data(Qt.UserRole) if item0 else None
        if log_id is None:
            self.current_log_id = None
            return
        # Find log by log_id in full_data
        log = next((x for x in self.full_data if x["id"] == log_id), None)
        if not log: return
        
        self.current_log_id = log["id"]
        
        # Fill inputs
        dt = datetime.fromisoformat(log["created_at"].replace("Z", ""))
        self.edit_date.setDate(QDate(dt.year, dt.month, dt.day))
        self.edit_time.setTime(QTime(dt.hour, dt.minute, dt.second))
        
        self.selected_user_id = log["user_id"]
        self.selected_emp_label.setText(f"선택됨: {log['user']['name']} ({log['user']['emp_no']})")
        
        # Select policy in combo
        policy_id = log["policy_id"]
        for i in range(self.policy_combo.count()):
            if self.policy_combo.itemData(i) == policy_id:
                self.policy_combo.setCurrentIndex(i)
                break
        
        self.edit_guest.setText(str(log.get("guest_count", 0)))
        
        self.add_btn.setEnabled(False)
        self.edit_btn.setEnabled(True)
        self.del_btn.setEnabled(True)

    def clear_inputs(self):
        self.edit_date.setDate(QDate.currentDate())
        self.edit_time.setTime(QTime.currentTime())
        self.emp_search_input.clear()
        self.selected_user_id = None
        self.selected_emp_label.setText("선택된 사원: 없음")
        self.policy_combo.setCurrentIndex(0)
        self.edit_guest.setText("0")
        self.table.clearSelection()
        self.current_log_id = None
        self.add_btn.setEnabled(True)
        self.edit_btn.setEnabled(False)
        self.del_btn.setEnabled(False)

    def on_add(self):
        if not self.selected_user_id:
            QMessageBox.warning(self, "경고", "사원을 먼저 선택하세요.")
            return
        policy_id = self.policy_combo.currentData()
        if not policy_id:
            QMessageBox.warning(self, "경고", "식사 종류를 선택하세요.")
            return
            
        dt_str = f"{self.edit_date.date().toString('yyyy-MM-dd')}T{self.edit_time.time().toString('HH:mm:ss')}"
        data = {
            "user_id": self.selected_user_id,
            "policy_id": policy_id,
            "created_at": dt_str,
            "guest_count": int(self.edit_guest.text() or 0)
        }
        
        self.action_loader = DataLoader(self.api.create_manual_raw_data, data)
        self.action_loader.finished.connect(self.on_action_finished)
        self.action_loader.start()

    def on_update(self):
        if not self.current_log_id: return
        policy_id = self.policy_combo.currentData()
        dt_str = f"{self.edit_date.date().toString('yyyy-MM-dd')}T{self.edit_time.time().toString('HH:mm:ss')}"
        data = {
            "user_id": self.selected_user_id,
            "policy_id": policy_id,
            "created_at": dt_str,
            "guest_count": int(self.edit_guest.text() or 0)
        }
        self.edit_btn.setEnabled(False)
        self.action_loader = DataLoader(self.api.update_raw_data, self.current_log_id, data)
        self.action_loader.finished.connect(self.on_action_finished)
        self.action_loader.start()

    def on_delete(self):
        if not self.current_log_id: return
        if QMessageBox.question(self, "삭제 확인", "정말로 이 기록을 완전히 삭제하시겠습니까?", 
                               QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return
        self.del_btn.setEnabled(False)
        self.action_loader = DataLoader(self.api.delete_raw_data, self.current_log_id)
        self.action_loader.finished.connect(self.on_action_finished)
        self.action_loader.start()

    def on_action_finished(self, result):
        success = False
        message = ""
        if isinstance(result, tuple): # Add/Update
            success, detail = result
            message = "등록/수정되었습니다." if success else str(detail)
        else: # Delete
            success = result
            message = "삭제되었습니다." if success else "삭제 실패"
            
        if success:
            QMessageBox.information(self, "성공", message)
            selected = self.table.selectedItems()
            if selected and "삭제" in message:
                self.table.removeRow(selected[0].row())
            self.load_data()
            self.clear_inputs()
        else:
            QMessageBox.warning(self, "오류", f"작업 실패: {message}")
            self.edit_btn.setEnabled(True)
            self.del_btn.setEnabled(True)
    
    def on_void_header(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "경고", "취소할 기록을 선택하세요.")
            return
        
        row_idx = selected[0].row()
        log_id = self.table.item(row_idx, 0).data(Qt.UserRole)
        if log_id is None:
            QMessageBox.warning(self, "경고", "선택한 행의 기록 ID를 찾을 수 없습니다.")
            return
        log = next((x for x in self.full_data if x.get("id") == log_id), None)
        if log is None:
            QMessageBox.warning(self, "경고", "선택한 기록을 찾을 수 없습니다.")
            return
        if log.get("is_void"):
            QMessageBox.warning(self, "경고", "이미 취소된 기록입니다.")
            return
            
        self.on_void(log_id)
    def on_void(self, log_id):
        reason, ok = QInputDialog.getText(self, "취소 사유", "취소 사유를 입력하세요:")
        if ok and reason:
            if self.api.void_log(log_id, reason):
                QMessageBox.information(self, "성공", "취소 처리가 완료되었습니다.")
                # Local UI update for performance
                selected = self.table.selectedItems()
                if selected:
                    row_idx = selected[0].row()
                    self.full_data[row_idx]["is_void"] = True
                    self.table.setItem(row_idx, 7, QTableWidgetItem("취소됨"))
            else:
                QMessageBox.warning(self, "오류", "처리에 실패했습니다.")

class PolicyScreen(QWidget):
    def __init__(self, api, main_win):
        super().__init__()
        self.api = api
        self.main_win = main_win
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        header_layout = QHBoxLayout()
        
        reg_frame = QFrame()
        reg_frame.setObjectName("StatCard")
        reg_layout = QHBoxLayout(reg_frame)
        self.type_input = QLineEdit()
        self.type_input.setPlaceholderText("식사 종류 (예: 조식)")
        self.type_input.setFixedWidth(250)
        self.start_input = QTimeEdit()
        self.start_input.setDisplayFormat("HH:mm:ss")
        self.start_input.setFixedWidth(180)
        self.end_input = QTimeEdit()
        self.end_input.setDisplayFormat("HH:mm:ss")
        self.end_input.setFixedWidth(180)
        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("단가 (원)")
        self.price_input.setFixedWidth(180)
        
        self.add_btn = QPushButton("등록")
        self.add_btn.setObjectName("PrimaryBtn")
        self.add_btn.setFixedWidth(100)
        self.add_btn.clicked.connect(self.on_add)
        
        self.edit_btn = QPushButton("수정")
        self.edit_btn.setObjectName("SecondaryBtn")
        self.edit_btn.setFixedWidth(100)
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self.on_edit)
        
        self.del_btn = QPushButton("삭제")
        self.del_btn.setObjectName("DangerBtn")
        self.del_btn.setFixedWidth(100)
        self.del_btn.setEnabled(False)
        self.del_btn.clicked.connect(self.on_delete)
        
        reg_layout.addWidget(self.type_input)
        reg_layout.addWidget(self.start_input)
        reg_layout.addWidget(self.end_input)
        reg_layout.addWidget(self.price_input)
        reg_layout.addWidget(self.add_btn)
        reg_layout.addWidget(self.edit_btn)
        reg_layout.addWidget(self.del_btn)
        
        header_layout.addWidget(reg_frame)
        layout.addLayout(header_layout)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["식사 종류", "시작 시간", "종료 시간", "기본 단가"])
        setup_standard_table(self.table)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.table)
        
        help_label = QLabel("* 시간 형식: HH:MM:SS (예: 12:00:00)")
        help_label.setStyleSheet("color: #94a3b8; font-size: 14px; font-weight: bold; font-family: 'Malgun Gothic';")
        layout.addWidget(help_label)
        layout.addStretch()

    def load_data(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.loader = DataLoader(self.api.get_policies)
        self.loader.finished.connect(self.display_data)
        self.loader.start()

    def display_data(self, data):
        QApplication.restoreOverrideCursor()
        if not isinstance(data, list): return
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(data))
        meal_names = {"breakfast": "조식", "lunch": "중식", "dinner": "석식"}
        
        for i, row in enumerate(data):
            if not isinstance(row, dict): continue
            meal_type = row.get("meal_type", "")
            row_id = row.get("id")
            item_meal = QTableWidgetItem(meal_type)
            item_meal.setData(Qt.UserRole, row_id)
            item_meal.setData(Qt.UserRole + 1, meal_type)
            self.table.setItem(i, 0, item_meal)
            self.table.setItem(i, 1, QTableWidgetItem(str(row.get("start_time", ""))))
            self.table.setItem(i, 2, QTableWidgetItem(str(row.get("end_time", ""))))

            item_price = QTableWidgetItem(str(row.get("base_price", 0)))
            self.table.setItem(i, 3, item_price)
        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)

    def on_selection_changed(self):
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            item0 = self.table.item(row, 0)
            item1 = self.table.item(row, 1)
            item2 = self.table.item(row, 2)
            item3 = self.table.item(row, 3)
            meal_display = item0.text() if item0 else ""
            start_time = item1.text() if item1 else ""
            end_time = item2.text() if item2 else ""
            price = item3.text() if item3 else ""

            self.type_input.setText(meal_display)

            self.start_input.setTime(QTime.fromString(start_time, "HH:mm:ss"))
            self.end_input.setTime(QTime.fromString(end_time, "HH:mm:ss"))
            self.price_input.setText(price)

            self.edit_btn.setEnabled(item0 is not None and item0.data(Qt.UserRole) is not None)
            self.del_btn.setEnabled(item0 is not None and item0.data(Qt.UserRole) is not None)
        else:
            self.type_input.clear()
            self.start_input.setTime(QTime(0, 0, 0))
            self.end_input.setTime(QTime(0, 0, 0))
            self.price_input.clear()
            self.edit_btn.setEnabled(False)
            self.del_btn.setEnabled(False)

    def clear_inputs(self):
        self.type_input.clear()
        self.start_input.setTime(QTime(0, 0, 0))
        self.end_input.setTime(QTime(0, 0, 0))
        self.price_input.clear()
        self.table.clearSelection()
        self.edit_btn.setEnabled(False)
        self.del_btn.setEnabled(False)

    def on_add(self):
        meal_type = self.type_input.text().strip()
        start_time = self.start_input.time().toString("HH:mm:ss")
        end_time = self.end_input.time().toString("HH:mm:ss")
        price = self.price_input.text().strip()
        
        if not meal_type or not start_time or not end_time or not price:
            QMessageBox.warning(self, "경고", "모든 정보를 입력하세요.")
            return

        try:
            price_val = int(price)
            data = {
                "meal_type": meal_type,
                "start_time": start_time,
                "end_time": end_time,
                "base_price": price_val,
                "guest_price": price_val,
                "is_active": True
            }
            self.add_btn.setEnabled(False)
            self.loader = DataLoader(self.api.create_policy, data)
            self.loader.finished.connect(self.on_action_finished)
            self.loader.start()
        except ValueError:
            QMessageBox.warning(self, "경고", "단가는 숫자여야 합니다.")

    def on_edit(self):
        selected = self.table.selectedItems()
        if not selected: return
        row = selected[0].row()
        item0 = self.table.item(row, 0)
        pid = item0.data(Qt.UserRole) if item0 else None
        if pid is None: return
        
        meal_type = self.type_input.text().strip()
        start_time = self.start_input.time().toString("HH:mm:ss")
        end_time = self.end_input.time().toString("HH:mm:ss")
        price = self.price_input.text().strip()
        
        if not meal_type or not start_time or not end_time or not price:
            QMessageBox.warning(self, "경고", "모든 정보를 입력하세요.")
            return
        
        try:
            price_val = int(price)
            data = {
                "meal_type": meal_type,
                "start_time": start_time,
                "end_time": end_time,
                "base_price": price_val,
                "guest_price": price_val,
                "is_active": True
            }
            self.edit_btn.setEnabled(False)
            self.loader = DataLoader(self.api.update_policy, pid, data)
            self.loader.finished.connect(self.on_action_finished)
            self.loader.start()
        except ValueError:
            QMessageBox.warning(self, "경고", "단가는 숫자여야 합니다.")

    def on_delete(self):
        selected = self.table.selectedItems()
        if not selected: return
        row = selected[0].row()
        item0 = self.table.item(row, 0)
        pid = item0.data(Qt.UserRole) if item0 else None
        if pid is None: return
        meal_name = item0.text() if item0 else "(선택 행)"
        
        if QMessageBox.question(self, "확인", f"'{meal_name}' 정책을 삭제하시겠습니까?") == QMessageBox.Yes:
            self.del_btn.setEnabled(False)
            self.loader = DataLoader(self.api.delete_policy, pid)
            self.loader.finished.connect(self.on_delete_finished)
            self.loader.start()

    def on_action_finished(self, result):
        self.add_btn.setEnabled(True)
        self.edit_btn.setEnabled(True)
        if isinstance(result, tuple):
            success, data = result
        else:
            success, data = bool(result), None
        if success:
            QMessageBox.information(self, "성공", "작업이 완료되었습니다.")
            self.load_data()
            self.clear_inputs()
        else:
            msg = str(data) if data is not None else "작업에 실패했습니다."
            QMessageBox.warning(self, "오류", msg)

    def on_delete_finished(self, success):
        self.del_btn.setEnabled(True)
        if success:
            selected = self.table.selectedItems()
            if selected:
                self.table.removeRow(selected[0].row())
            QMessageBox.information(self, "성공", "삭제되었습니다.")
            self.load_data()
            self.clear_inputs()
        else:
            QMessageBox.warning(self, "오류", "삭제에 실패했습니다.")

class ReportScreen(QWidget):
    def __init__(self, api, main_win):
        super().__init__()
        self.api = api
        self.main_win = main_win
        self.full_data = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("식사 통계 보고서")
        header.setObjectName("HeaderTitle")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Controls Frame
        controls_frame = QFrame()
        controls_frame.setObjectName("StatCard")
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setSpacing(15)
        
        date_label = QLabel("조회 기간")
        date_label.setObjectName("InputLabel")
        
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-7))
        self.start_date_edit.setFixedWidth(180)
        
        tilde = QLabel("~")
        tilde.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setFixedWidth(180)
        
        cond_label = QLabel("출력 조건")
        cond_label.setObjectName("InputLabel")
        
        self.condition_combo = QComboBox()
        self.condition_combo.addItems(["개인별", "부서별", "전체", "상세 내역"])
        self.condition_combo.setFixedWidth(160)
        self.condition_combo.currentIndexChanged.connect(self.display_data)
        
        self.search_btn = QPushButton("조회")
        self.search_btn.setObjectName("PrimaryBtn")
        self.search_btn.setFixedWidth(100)
        self.search_btn.clicked.connect(self.load_data)

        self.download_btn = QPushButton()
        self.download_btn.setObjectName("SecondaryBtn")
        self.download_btn.setToolTip("엑셀 다운로드")
        self.download_btn.setFixedWidth(50)
        
        # Excel Icon SVG (Base64)
        excel_svg = QByteArray.fromBase64(b"PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMxMGI5ODEiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj4KICA8cGF0aCBkPSJNMTUgMkg2YTIgMiAwIDAgMC0yIDJ2MTZhMiAyIDAgMCAwIDIgMmgxMmEyIDIgMCAwIDAgMi0yVjdaIi8+CiAgPHBhdGggZD0iTTE0IDJ2NGEyIDIgMCAwIDAgMiAyaDQiLz4KICA8cGF0aCBkPSJNOCAxM2gyIi8+CiAgPHBhdGggZD0iTTE0IDEzaDIiLz4KICA8cGF0aCBkPSJNOCAxN2gyIi8+CiAgPHBhdGggZD0iTTE0IDE3aDIiLz4KICA8cGF0aCBkPSJNMTAgMTFoNHYxMGgtNHoiLz4KPC9zdmc+")
        pixmap = QPixmap()
        pixmap.loadFromData(excel_svg)
        self.download_btn.setIcon(QIcon(pixmap))
        self.download_btn.setIconSize(QSize(28, 28))
        
        self.download_btn.clicked.connect(self.on_download_excel)
        
        controls_layout.addWidget(date_label)
        controls_layout.addWidget(self.start_date_edit)
        controls_layout.addWidget(tilde)
        controls_layout.addWidget(self.end_date_edit)
        controls_layout.addSpacing(20)
        controls_layout.addWidget(cond_label)
        controls_layout.addWidget(self.condition_combo)
        controls_layout.addStretch()
        controls_layout.addWidget(self.search_btn)
        controls_layout.addWidget(self.download_btn)
        
        layout.addWidget(controls_frame)
        
        # Table Area
        self.table = QTableWidget(0, 7)
        setup_standard_table(self.table)
        layout.addWidget(self.table, 1) # Give stretch factor 1 to take remaining space

    def load_data(self):
        start = self.start_date_edit.date().toString("yyyy-MM-dd")
        end = self.end_date_edit.date().toString("yyyy-MM-dd")
        
        self.search_btn.setEnabled(False)
        self.main_win.statusBar().showMessage("데이터 조회 중...", 3000)
        
        # Get raw data for the range
        self.loader = DataLoader(self.api.get_raw_data, "", start, end)
        self.loader.finished.connect(self.on_data_loaded)
        self.loader.start()

    def on_data_loaded(self, data):
        self.search_btn.setEnabled(True)
        if not isinstance(data, list): 
            QMessageBox.warning(self, "오류", "데이터를 가져오는데 실패했습니다.")
            return
            
        # Filter out voided logs
        self.full_data = [d for d in data if not d.get("is_void")]
        self.display_data()

    def display_data(self):
        condition = self.condition_combo.currentText()
        self.table.setUpdatesEnabled(False)
        self.table.clearSelection()
        
        # Aggregation Logic
        # Result structure: { "id_or_name": { "cnt": 0, "guest": 0, "total": 0, "amount": 0, "meta": {} } }
        agg = {}
        
        for log in self.full_data:
            u = log.get("user", {})
            p = log.get("policy", {})
            
            # Identify grouping key
            if condition == "개인별":
                key = u.get("id")
                meta = {"no": u.get("emp_no"), "name": u.get("name"), "dept": u.get("department_name")}
            elif condition == "부서별":
                key = u.get("department_id") or "UNKNOWN_DEPT"
                meta = {"name": u.get("department_name") or "미지정"}
            elif condition == "전체": # 전체 (식사 종류별)
                key = p.get("id") or "EXTRA"
                meta = {"name": p.get("meal_type") or "번외"}
            else: # 상세 내역
                pass # Will handle separately
                
            if condition != "상세 내역":
                if key not in agg:
                    agg[key] = {"cnt": 0, "guest": 0, "total": 0, "amount": 0, "meta": meta}
                
                guest = log.get("guest_count", 0)
                price = log.get("final_price", 0)
                
                agg[key]["cnt"] += 1
                agg[key]["guest"] += guest
                agg[key]["total"] += (1 + guest)
                agg[key]["amount"] += (price * (1 + guest))
            
        # Update Table Headers and Rows
        if condition == "개인별":
            self.table.setColumnCount(7)
            self.table.setHorizontalHeaderLabels(["사번", "성명", "부서", "식사 횟수", "게스트", "합계 식수", "총 금액"])
        elif condition == "부서별":
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(["부서명", "식사 횟수", "게스트", "합계 식수", "총 금액"])
        elif condition == "전체":
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(["식사 종류", "식사 횟수", "게스트", "합계 식수", "총 금액"])
        else: # 상세 내역
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels(["사번", "이름", "부서", "식사종류", "날짜"])
            
        if condition == "상세 내역":
            self.table.setRowCount(len(self.full_data))
            # Sort full data by date descending for detailed view
            sorted_logs = sorted(self.full_data, key=lambda x: x.get("created_at", ""), reverse=True)
            for i, log in enumerate(sorted_logs):
                u = log.get("user", {})
                p = log.get("policy", {})
                dt_str = log.get("created_at", "").replace("T", " ")[:16]
                
                self.table.setItem(i, 0, QTableWidgetItem(str(u.get("emp_no", ""))))
                self.table.setItem(i, 1, QTableWidgetItem(str(u.get("name", ""))))
                self.table.setItem(i, 2, QTableWidgetItem(str(u.get("department_name", ""))))
                self.table.setItem(i, 3, QTableWidgetItem(str(p.get("meal_type", "번외"))))
                self.table.setItem(i, 4, QTableWidgetItem(dt_str))
        else:
            self.table.setRowCount(len(agg))
            # Sort keys by name for consistency
            sorted_keys = sorted(agg.keys(), key=lambda k: str(agg[k]["meta"].get("name", "")))
            
            for i, key in enumerate(sorted_keys):
                item = agg[key]
                meta = item["meta"]
                
                col = 0
                if condition == "개인별":
                    self.table.setItem(i, col, QTableWidgetItem(str(meta.get("no", "")))); col += 1
                    self.table.setItem(i, col, QTableWidgetItem(str(meta.get("name", "")))); col += 1
                    self.table.setItem(i, col, QTableWidgetItem(str(meta.get("dept", "")))); col += 1
                else:
                    self.table.setItem(i, col, QTableWidgetItem(str(meta.get("name", "")))); col += 1
                    
                self.table.setItem(i, col, QTableWidgetItem(f"{item['cnt']:,}")); col += 1
                self.table.setItem(i, col, QTableWidgetItem(f"{item['guest']:,}")); col += 1
                self.table.setItem(i, col, QTableWidgetItem(f"{item['total']:,}")); col += 1
                
                amount_item = QTableWidgetItem(f"{item['amount']:,}원")
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, col, amount_item)

        self.table.setUpdatesEnabled(True)

    def update_meal_type_summary(self):
        # Removed as requested
        pass

    def on_download_excel(self):
        # Specific year/month download for official reports
        curr_date = self.end_date_edit.date()
        year = curr_date.year()
        month = curr_date.month()
        
        from PyQt5.QtWidgets import QFileDialog
        save_path, _ = QFileDialog.getSaveFileName(self, "보고서 저장", f"MealReport_{year}{month:02d}.xlsx", "Excel Files (*.xlsx)")
        if not save_path: return
        
        self.download_btn.setEnabled(False)
        self.dl_loader = DataLoader(self.api.get_excel_report_data, year, month)
        self.dl_loader.finished.connect(lambda data: self.on_download_finished(data, save_path))
        self.dl_loader.start()

    def on_download_finished(self, data, save_path):
        self.download_btn.setEnabled(True)
        if data:
            with open(save_path, "wb") as f:
                f.write(data)
            QMessageBox.information(self, "성공", f"Excel 보고서가 저장되었습니다.\n{save_path}")
        else:
            QMessageBox.warning(self, "오류", "Excel 보고서 다운로드에 실패했습니다.")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = APIClient()
        self.companies_data = []
        self.departments_data = []
        self.setWindowTitle("Meal Auth - Admin Management System")
        self.resize(1280, 850)
        self.setStyleSheet(QSS)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        logo = QLabel("Meal Admin")
        logo.setObjectName("Logo")
        sidebar_layout.addWidget(logo)
        self.nav_btns = []
        menus = [
            ("대시보드", 0), ("회사 관리", 1), ("부서 관리", 2), 
            ("사원 관리", 3), ("원시 데이터", 4), ("식사 정책", 5), ("보고서", 6)
        ]
        for name, idx in menus:
            btn = QPushButton(name)
            btn.setObjectName("MenuBtn")
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda chk, i=idx: self.switch_screen(i))
            sidebar_layout.addWidget(btn)
            self.nav_btns.append(btn)
        sidebar_layout.addStretch()
        main_layout.addWidget(self.sidebar)
        content_container = QWidget()
        content_container.setObjectName("ContentArea")
        self.content_layout = QVBoxLayout(content_container)
        self.stack = QStackedWidget()
        self.dashboard = DashboardScreen()
        self.companies = CompanyScreen(self.api, self)
        self.departments = DepartmentScreen(self.api, self)
        self.employees = EmployeeScreen(self.api, self)
        self.raw_data = RawDataScreen(self.api, self)
        self.policies = PolicyScreen(self.api, self)
        self.reports = ReportScreen(self.api, self)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.companies)
        self.stack.addWidget(self.departments)
        self.stack.addWidget(self.employees)
        self.stack.addWidget(self.raw_data)
        self.stack.addWidget(self.policies)
        self.stack.addWidget(self.reports)
        self.content_layout.addWidget(self.stack)
        main_layout.addWidget(content_container)
        self.switch_screen(0)
        self.on_company_changed() # Initial load of companies
        self.refresh_stats()
        
        # Obsolete Auto-refresh timer removed in favor of WebSockets
        
        # Start WebSocket Client
        self.ws_client = WSClient()
        self.ws_client.message_received.connect(self.on_ws_message)
        self.ws_client.start()

    def on_ws_message(self, data):
        msg_type = data.get("type")
        if msg_type in ["USER_VERIFIED", "MEAL_LOG_CREATED"]:
            self.refresh_stats() # refresh active screen and dashboard

    def on_company_changed(self):
        self.company_sync_loader = DataLoader(self.api.get_companies)
        self.company_sync_loader.finished.connect(self.on_company_sync_finished)
        self.company_sync_loader.start()

    def on_company_sync_finished(self, data):
        if isinstance(data, list):
            self.companies_data = data
            self.departments.update_company_combo(self.companies_data)
            self.employees.update_company_combo(self.companies_data)
            self.sync_departments()

    def sync_departments(self):
        self.dept_sync_loader = DataLoader(self.api.get_departments)
        self.dept_sync_loader.finished.connect(self.on_dept_sync_finished)
        self.dept_sync_loader.start()

    def on_dept_sync_finished(self, data):
        if isinstance(data, list):
            self.departments_data = data
            # Update screens using departments
            if self.stack.currentIndex() == 2:
                self.departments.load_data()
            if self.stack.currentIndex() == 3:
                self.employees.update_dept_combo()

    def refresh_stats(self):
        self.refresh_active_screen()
        if hasattr(self, 'stat_loader') and self.stat_loader.isRunning():
            return
        self.stat_loader = DataLoader(self.api.get_stats)
        self.stat_loader.finished.connect(self.display_stats)
        self.stat_loader.start()
        
    def refresh_active_screen(self):
        idx = self.stack.currentIndex()
        if idx == 3: # EmployeeScreen
            if not hasattr(self.employees, 'loader') or not self.employees.loader.isRunning():
                self.employees.load_data()
        elif idx == 4: # RawDataScreen
            pass # Explicit search only
    def display_stats(self, stats):
        if stats and isinstance(stats, dict):
            # Dynamic stats update
            self.dashboard.update_stats(stats)
            # 테이블도 서버가 통계 낸 날짜로 조회 (타임존/날짜 불일치 방지)
            self.load_recent_logs(stats.get("date"))

    def load_recent_logs(self, date_value=None):
        if hasattr(self, 'recent_loader') and self.recent_loader.isRunning():
            return
        # 서버 stats의 date 사용 (없으면 로컬 오늘)
        if date_value:
            if hasattr(date_value, 'strftime'):
                day_str = date_value.strftime("%Y-%m-%d")
            else:
                day_str = str(date_value)[:10]
        else:
            day_str = date.today().strftime("%Y-%m-%d")
        self.recent_loader = DataLoader(self.api.get_raw_data, "", day_str, day_str)
        self.recent_loader.finished.connect(self.on_recent_logs_finished)
        self.recent_loader.start()

    def on_recent_logs_finished(self, data):
        if isinstance(data, list):
            # Show all logs for today on dashboard
            self.dashboard.update_recent(data)
    def switch_screen(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.nav_btns):
            btn.setProperty("active", "true" if i == idx else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if idx == 1: self.companies.load_data()
        if idx == 2: self.departments.load_data()  # refresh table when opening tab (filters by selected company)
        if idx == 3: self.employees.load_data()
        if idx == 4: pass # Explicit search only
        if idx == 5: self.policies.load_data()
        if idx == 6: self.reports.load_data()

    def closeEvent(self, event):
        if hasattr(self, 'ws_client'):
            self.ws_client.stop()
        self.api.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
