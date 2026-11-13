"""Q 수치 계산기 - 기자용 증감률·단위 계산기 (PySide6).

표기 기준은 아주경제 스타일북(2021년판)이며, 계산과 문장 만들기는 calccore.py가 맡는다.
"""
from __future__ import annotations

import base64
import json
import sys
from datetime import date, datetime

from PySide6.QtCore import QSettings, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QPlainTextEdit, QPushButton,
    QCheckBox, QRadioButton, QScrollArea, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

import calccore as cc

APP_NAME = "Q 수치 계산기"
APP_VERSION = "1.0.0"
SETTINGS_ORG = "QNumberCalc"

C_BG = "#f4f5f8"
C_PANEL = "#ffffff"
C_LINE = "#dcdfe7"
C_TEXT = "#1d1f26"
C_MUTED = "#6b7080"
C_ACCENT = "#ff4949"
C_ACCENT_TEXT = "#d93636"
C_UP = "#e03131"
C_DOWN = "#2f6fed"
C_WARN = "#b7791f"
C_HOVER = "#eef0f5"

STYLE = f"""
* {{ font-family: 'Segoe UI', 'Malgun Gothic', 'Noto Sans CJK KR', 'Noto Sans CJK SC', sans-serif; font-size: 13px; }}
QMainWindow, QDialog {{ background: {C_BG}; }}
QLabel {{ background: transparent; color: {C_TEXT}; }}
QLabel#cap {{ color: {C_MUTED}; font-size: 12px; }}
QLabel#title {{ font-size: 15px; font-weight: bold; }}
QLabel#badge {{ color: {C_MUTED}; font-size: 11px; border: 1px solid {C_LINE}; border-radius: 10px; padding: 2px 9px; }}
QLabel#toast {{ color: {C_ACCENT_TEXT}; font-size: 12px; font-weight: bold; padding-right: 8px; }}
QLabel#logo {{ background: {C_ACCENT}; color: white; border-radius: 5px; font-weight: bold; font-size: 12px; }}
QLabel#big {{ font-size: 24px; font-weight: bold; }}
QLabel#val {{ font-size: 16px; font-weight: bold; }}
QLabel#rowname {{ font-weight: bold; }}
QFrame#header, QFrame#footer {{ background: {C_PANEL}; }}
QFrame#header {{ border-bottom: 1px solid {C_LINE}; }}
QFrame#footer {{ border-top: 1px solid {C_LINE}; }}
QFrame#panel {{ background: {C_PANEL}; border-right: 1px solid {C_LINE}; }}
QFrame#card {{ background: {C_PANEL}; border: 1px solid {C_LINE}; border-radius: 6px; }}
QFrame#row {{ background: {C_PANEL}; border-bottom: 1px solid {C_LINE}; }}
QFrame#sent {{ background: {C_PANEL}; border: 1px solid {C_LINE}; border-radius: 6px; }}
QFrame#sent[primary="true"] {{ border: 1px solid {C_ACCENT}; }}
QFrame#sent:hover {{ background: #fff5f5; }}
QFrame#notice {{ border-radius: 6px; border: 1px solid {C_LINE}; }}
QFrame#notice[level="warn"] {{ background: #fff8e6; border: 1px solid #e3b04b; }}
QFrame#segwrap {{ border: 1px solid {C_LINE}; border-radius: 6px; }}
QLineEdit, QComboBox, QPlainTextEdit, QTableWidget, QListWidget {{
  background: {C_PANEL}; border: 1px solid {C_LINE}; border-radius: 6px; padding: 5px 8px; color: {C_TEXT};
  selection-background-color: {C_ACCENT}; selection-color: white; }}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{ border: 1px solid {C_ACCENT}; }}
QLineEdit:disabled, QComboBox:disabled {{ color: {C_MUTED}; }}
QLineEdit[readOnly="true"] {{ background: {C_BG}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {C_PANEL}; border: 1px solid {C_LINE}; selection-background-color: rgba(255,73,73,45); selection-color: {C_TEXT}; color: {C_TEXT}; }}
QPushButton {{ background: transparent; color: {C_TEXT}; border: 1px solid {C_LINE}; border-radius: 6px; padding: 6px 12px; }}
QPushButton:hover {{ background: {C_HOVER}; }}
QPushButton#primary {{ background: {C_ACCENT}; border: 1px solid {C_ACCENT}; color: white; font-weight: bold; }}
QPushButton#primary:hover {{ background: #ff5c5c; }}
QPushButton#seg {{ border: none; border-radius: 0; color: {C_MUTED}; padding: 6px 0; }}
QPushButton#seg:checked {{ background: rgba(255,73,73,32); color: {C_ACCENT_TEXT}; font-weight: bold; }}
QPushButton#chip {{ border-radius: 12px; padding: 3px 10px; font-size: 12px; color: {C_MUTED}; }}
QPushButton#copy {{ padding: 5px 10px; }}
QPushButton#gear {{ border: none; color: {C_MUTED}; padding: 4px 8px; }}
QPushButton:disabled {{ color: #a4a8b5; }}
QRadioButton {{ spacing: 8px; padding: 3px 0; }}
QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 8px; border: 1px solid #a4a8b5; background: {C_PANEL}; }}
QRadioButton::indicator:checked {{ background: {C_ACCENT}; border: 1px solid {C_ACCENT}; }}
QTabWidget::pane {{ border: none; }}
QTabBar {{ background: {C_PANEL}; }}
QTabBar::tab {{ background: transparent; color: {C_MUTED}; padding: 8px 18px; border: none; border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {C_TEXT}; font-weight: bold; border-bottom: 2px solid {C_ACCENT}; }}
QHeaderView::section {{ background: {C_PANEL}; color: {C_MUTED}; border: none; border-bottom: 1px solid {C_LINE}; padding: 5px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {C_LINE}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


def _icon_from_embedded() -> QIcon:
    icon = QIcon()
    try:
        from icon_data import ICON_PNG_B64
    except ImportError:
        return icon
    for size, b64 in ICON_PNG_B64.items():
        pm = QPixmap()
        pm.loadFromData(base64.b64decode(b64), "PNG")
        icon.addPixmap(pm)
    return icon


def cap(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("cap")
    return lb


def apply_palette(app: QApplication) -> None:
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window, QColor(C_BG))
    p.setColor(QPalette.WindowText, QColor(C_TEXT))
    p.setColor(QPalette.Base, QColor(C_BG))
    p.setColor(QPalette.AlternateBase, QColor(C_PANEL))
    p.setColor(QPalette.Text, QColor(C_TEXT))
    p.setColor(QPalette.Button, QColor(C_PANEL))
    p.setColor(QPalette.ButtonText, QColor(C_TEXT))
    p.setColor(QPalette.Highlight, QColor(C_ACCENT))
    p.setColor(QPalette.HighlightedText, QColor("white"))
    p.setColor(QPalette.PlaceholderText, QColor("#9a9eab"))
    p.setColor(QPalette.ToolTipBase, QColor(C_PANEL))
    p.setColor(QPalette.ToolTipText, QColor(C_TEXT))
    app.setPalette(p)


# ------------------------------------------------------------------ 작은 부품
class Segmented(QFrame):
    changed = Signal(int)

    def __init__(self, labels, parent=None):
        super().__init__(parent)
        self.setObjectName("segwrap")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = []
        for i, text in enumerate(labels):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setObjectName("seg")
            b.setCursor(Qt.PointingHandCursor)
            self.group.addButton(b, i)
            lay.addWidget(b, 1)
            self.buttons.append(b)
        self.buttons[0].setChecked(True)
        self.group.idClicked.connect(self.changed.emit)

    def index(self) -> int:
        return self.group.checkedId()

    def set_index(self, i: int) -> None:
        self.buttons[i].setChecked(True)


class StatCard(QFrame):
    def __init__(self, big: bool = False):
        super().__init__()
        self.setObjectName("card")
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(2)
        self.label = cap("")
        self.value = QLabel("—")
        self.value.setObjectName("big" if big else "val")
        v.addWidget(self.label)
        v.addWidget(self.value)

    def set(self, label: str, text: str, color: str | None = None, border: str | None = None) -> None:
        self.label.setText(label)
        self.value.setText(text)
        self.value.setStyleSheet(f"color:{color};" if color else "")
        self.setStyleSheet(f"QFrame#card{{border:1px solid {border};}}" if border else "")


class SentenceRow(QFrame):
    clicked = Signal(str)

    def __init__(self, text: str, primary: bool):
        super().__init__()
        self.setObjectName("sent")
        self.setProperty("primary", "true" if primary else "false")
        self.setCursor(Qt.PointingHandCursor)
        self._text = text
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)
        self.lbl = QLabel(text)
        self.lbl.setWordWrap(True)
        n = len(text)
        self.cnt = QLabel(f"{n}자")
        self.cnt.setObjectName("cap")
        if n > 60:
            self.cnt.setStyleSheet(f"color:{C_WARN};")
            self.cnt.setToolTip("한 문장은 60자 이하를 권장해요")
        self.tag = cap("복사")
        for w in (self.lbl, self.cnt, self.tag):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(self.lbl, 1)
        lay.addWidget(self.cnt)
        lay.addWidget(self.tag)

    def mousePressEvent(self, e):  # noqa: N802
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self._text)
        super().mousePressEvent(e)


# ------------------------------------------------------------------ 대화상자
class SettingsDialog(QDialog):
    def __init__(self, parent, color_mode: str, decimals: int):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setMinimumWidth(360)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)
        lay.addWidget(cap("증감 숫자 표시"))
        self.r_color = QRadioButton("상승 빨강 · 하락 파랑 (화살표와 함께)")
        self.r_plain = QRadioButton("색 없이 화살표만")
        (self.r_color if color_mode == "color" else self.r_plain).setChecked(True)
        lay.addWidget(self.r_color)
        lay.addWidget(self.r_plain)
        note = cap("부서나 기사에 따라 오르내림 색 관례가 다르면 '색 없이'를 고르세요.")
        note.setWordWrap(True)
        lay.addWidget(note)
        lay.addSpacing(6)
        lay.addWidget(cap("기본 소수점 자리"))
        self.dec = QComboBox()
        self.dec.addItems(["0자리", "1자리", "2자리"])
        self.dec.setCurrentIndex(max(0, min(2, decimals)))
        lay.addWidget(self.dec)
        lay.addSpacing(10)
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("취소")
        ok = QPushButton("저장")
        ok.setObjectName("primary")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)

    def values(self) -> tuple[str, int]:
        return ("color" if self.r_color.isChecked() else "plain"), self.dec.currentIndex()


class HistoryDialog(QDialog):
    def __init__(self, parent, history: list[dict]):
        super().__init__(parent)
        self.setWindowTitle("계산 기록")
        self.resize(520, 420)
        self.chosen: dict | None = None
        self.cleared = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(cap("복사한 계산이 최근 순으로 쌓여요. 더블클릭하면 다시 불러와요. 이 PC에만 저장돼요."))
        self.list = QListWidget()
        for h in history:
            it = QListWidgetItem(f"{h.get('summary', '')}    ({h.get('at', '')})")
            it.setData(Qt.UserRole, h)
            self.list.addItem(it)
        self.list.itemDoubleClicked.connect(self._choose)
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        clear = QPushButton("기록 모두 지우기")
        clear.clicked.connect(self._clear)
        load = QPushButton("불러오기")
        load.setObjectName("primary")
        load.clicked.connect(lambda: self._choose(self.list.currentItem()))
        close = QPushButton("닫기")
        close.clicked.connect(self.reject)
        row.addWidget(clear)
        row.addStretch(1)
        row.addWidget(close)
        row.addWidget(load)
        lay.addLayout(row)

    def _choose(self, item) -> None:
        if item is not None:
            self.chosen = item.data(Qt.UserRole)
            self.accept()

    def _clear(self) -> None:
        self.cleared = True
        self.list.clear()


class BulkDialog(QDialog):
    def __init__(self, parent, base: cc.CalcInput, copy_cb):
        super().__init__(parent)
        self.setWindowTitle("여러 건 한꺼번에 계산")
        self.resize(820, 560)
        self.base = base
        self.copy_cb = copy_cb
        self.rows: list[dict] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)
        info = cap("엑셀에서 '항목 / 기준값 / 현재값' 세 칸을 복사해 붙이세요. 비교 기준, 단위, 소수점, 유형은 메인 화면 설정을 따라요.")
        info.setWordWrap(True)
        lay.addWidget(info)
        self.box = QPlainTextEdit()
        self.box.setPlaceholderText("매출\t1250\t1380\n영업이익\t820\t640")
        self.box.setFixedHeight(120)
        lay.addWidget(self.box)
        row = QHBoxLayout()
        paste = QPushButton("클립보드에서 붙여넣기")
        paste.clicked.connect(self._paste)
        go = QPushButton("계산")
        go.setObjectName("primary")
        go.clicked.connect(self.run)
        row.addWidget(paste)
        row.addWidget(go)
        row.addStretch(1)
        lay.addLayout(row)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["항목", "기준값", "현재값", "증감", "첫 문장"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.table, 1)
        row2 = QHBoxLayout()
        copy_all = QPushButton("결과 복사 (엑셀에 붙여넣기용)")
        copy_all.setObjectName("primary")
        copy_all.clicked.connect(self._copy_all)
        close = QPushButton("닫기")
        close.clicked.connect(self.accept)
        row2.addStretch(1)
        row2.addWidget(close)
        row2.addWidget(copy_all)
        lay.addLayout(row2)

    def _paste(self) -> None:
        self.box.setPlainText(QGuiApplication.clipboard().text())
        self.run()

    def run(self) -> None:
        self.rows = cc.bulk_compute(self.box.toPlainText(), self.base)
        self.table.setRowCount(len(self.rows))
        for r, d in enumerate(self.rows):
            vals = [d["item"], d["prev"], d["cur"], d["change"] or "—", d["sentence"] or d["error"]]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c == 4 and d["error"]:
                    it.setForeground(QColor(C_WARN))
                self.table.setItem(r, c, it)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

    def _copy_all(self) -> None:
        if not self.rows:
            self.run()
        lines = ["\t".join([d["item"], d["change"], d["sentence"] or d["error"]]) for d in self.rows]
        self.copy_cb("\n".join(lines), record=False)


# ------------------------------------------------------------------ 단위·환율 탭
class FxNoticeDialog(QDialog):
    """환율을 가져오기 전에 보여 주는 안내 창."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("현재 환율 가져오기")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)
        t = QLabel("현재 환율을 가져올까요?")
        t.setObjectName("title")
        lay.addWidget(t)
        lay.addWidget(QLabel("인터넷에 연결해 최신 환율을 받아 옵니다."))
        box = QFrame()
        box.setObjectName("notice")
        box.setProperty("level", "warn")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(12, 10, 12, 10)
        bl.setSpacing(4)
        h = QLabel("기사에 쓰기 전에 확인하세요")
        h.setStyleSheet(f"color:{C_WARN}; font-weight:bold; font-size:12px;")
        body = QLabel("시장 기준 참고 환율이라 서울외환시장 마감 환율이나 매매기준율과 몇 원 차이가 날 수 있습니다. "
                      "기사에 쓰는 기준일과 환율은 직접 확인해 주세요.")
        body.setWordWrap(True)
        bl.addWidget(h)
        bl.addWidget(body)
        lay.addWidget(box)
        sub = cap("입력한 금액이나 기사 내용은 전송되지 않고, 환율만 받아 옵니다.")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        self.skip = QCheckBox("다시 보지 않기")
        lay.addWidget(self.skip)
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("취소")
        ok = QPushButton("가져오기")
        ok.setObjectName("primary")
        ok.setDefault(True)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)


class FxWorker(QThread):
    """화면이 멈추지 않도록 환율을 따로 받아 오는 작업자."""

    done = Signal(object, str)  # (FxRate | None, 오류 문구)

    def __init__(self, currency: str, fetch_fn):
        super().__init__()
        self.currency = currency
        self.fetch_fn = fetch_fn

    def run(self) -> None:
        try:
            self.done.emit(self.fetch_fn(self.currency), "")
        except cc.FxFetchError as e:
            self.done.emit(None, str(e))
        except Exception:  # 예상 못 한 오류도 화면에는 같은 안내만 보여 준다
            self.done.emit(None, "환율을 가져오지 못했어요. 환율을 직접 입력하세요")


class UnitTab(QWidget):
    def __init__(self, copy_cb, qs: QSettings | None = None):
        super().__init__()
        self.copy_cb = copy_cb
        self.qs = qs
        self.fetch_fn = cc.fetch_fx_rate
        self._worker: FxWorker | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._row_big())
        lay.addWidget(self._row_area())
        lay.addWidget(self._row_fx())
        note = cap("만·억·조는 숫자 뒤에 붙여 쓰고 쉼표는 쓰지 않아요. 환산액은 어림수에 '약'을 붙이고, 환율은 직접 입력한 값을 그대로 기사에 적을 수 있게 보여 줘요.")
        note.setWordWrap(True)
        note.setContentsMargins(16, 12, 16, 0)
        lay.addWidget(note)
        lay.addStretch(1)
        self.update_big()
        self.update_area()
        self.update_fx()

    # -- 공통
    def _result_box(self):
        res = QLineEdit()
        res.setReadOnly(True)
        res.setPlaceholderText("결과")
        btn = QPushButton("복사")
        btn.setObjectName("copy")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: res.text() and self.copy_cb(res.text(), record=False))
        h = QHBoxLayout()
        h.setSpacing(6)
        h.addWidget(res, 1)
        h.addWidget(btn)
        return res, h

    def _frame(self, name: str, sub: str, inputs: QVBoxLayout, res_layout, extra=None) -> QFrame:
        f = QFrame()
        f.setObjectName("row")
        h = QHBoxLayout(f)
        h.setContentsMargins(16, 14, 16, 14)
        h.setSpacing(14)
        left = QVBoxLayout()
        n = QLabel(name)
        n.setObjectName("rowname")
        left.addWidget(n)
        left.addWidget(cap(sub))
        left.addStretch(1)
        lw = QWidget()
        lw.setFixedWidth(104)
        lw.setLayout(left)
        h.addWidget(lw, 0, Qt.AlignTop)
        iw = QWidget()
        iw.setLayout(inputs)
        h.addWidget(iw, 3)
        arrow = QLabel("→")
        arrow.setObjectName("cap")
        h.addWidget(arrow, 0, Qt.AlignTop)
        rv = QVBoxLayout()
        rv.setSpacing(4)
        rv.addLayout(res_layout)
        if extra is not None:
            rv.addWidget(extra)
        rv.addStretch(1)
        rw = QWidget()
        rw.setLayout(rv)
        h.addWidget(rw, 4)
        return f

    # -- 큰 숫자 읽기
    def _row_big(self) -> QFrame:
        self.big_in = QLineEdit("1234500000000")
        self.big_in.setPlaceholderText("1234500000000 또는 1조2345억")
        self.big_base = QComboBox()
        self.big_base.addItems(["원", "명", "달러", "건", "개"])
        self.big_base.setFixedWidth(76)
        v = QVBoxLayout()
        h = QHBoxLayout()
        h.addWidget(self.big_in, 1)
        h.addWidget(self.big_base)
        v.addLayout(h)
        self.big_res, rl = self._result_box()
        self.big_in.textChanged.connect(self.update_big)
        self.big_base.currentIndexChanged.connect(self.update_big)
        return self._frame("큰 숫자 읽기", "원 → 만·억·조", v, rl)

    def update_big(self) -> None:
        t = self.big_in.text()
        if not t.strip():
            self.big_res.setText("")
            return
        try:
            self.big_res.setText(cc.big_number(t, self.big_base.currentText()))
        except ValueError:
            self.big_res.setText("")
            self.big_res.setPlaceholderText("숫자를 확인하세요")

    # -- 면적
    def _row_area(self) -> QFrame:
        self.area_in = QLineEdit("84")
        self.area_in.setPlaceholderText("면적")
        self.area_dir = QComboBox()
        self.area_dir.addItems(["㎡ → 평", "평 → ㎡"])
        self.area_dir.setFixedWidth(96)
        v = QVBoxLayout()
        h = QHBoxLayout()
        h.addWidget(self.area_in, 1)
        h.addWidget(self.area_dir)
        v.addLayout(h)
        self.area_res, rl = self._result_box()
        self.area_in.textChanged.connect(self.update_area)
        self.area_dir.currentIndexChanged.connect(self.update_area)
        return self._frame("면적", "㎡ ↔ 평", v, rl)

    def update_area(self) -> None:
        t = self.area_in.text()
        if not t.strip():
            self.area_res.setText("")
            return
        try:
            self.area_res.setText(cc.convert_area(t, self.area_dir.currentIndex() == 0))
        except ValueError:
            self.area_res.setText("")
            self.area_res.setPlaceholderText("숫자를 확인하세요")

    # -- 외화 환산
    def _row_fx(self) -> QFrame:
        self.fx_amt = QLineEdit("1000만")
        self.fx_amt.setPlaceholderText("금액 (예: 1000만)")
        self.fx_cur = QComboBox()
        self.fx_cur.setEditable(True)
        self.fx_cur.addItems(list(cc.FX_CURRENCIES))
        self.fx_cur.setFixedWidth(96)
        self.fx_rate = QLineEdit("1380")
        self.fx_rate.setPlaceholderText("환율 (원)")
        today = date.today()
        self.fx_date = QLineEdit(f"{today.year}년 {today.month}월 {today.day}일")
        self.fx_date.setPlaceholderText("기준일")
        v = QVBoxLayout()
        v.setSpacing(6)
        h1 = QHBoxLayout()
        h1.addWidget(self.fx_amt, 1)
        h1.addWidget(self.fx_cur)
        v.addLayout(h1)
        h2 = QHBoxLayout()
        h2.addWidget(cap("1단위 ="))
        h2.addWidget(self.fx_rate, 1)
        h2.addWidget(cap("원"))
        self.fx_fetch = QPushButton("현재 환율 가져오기")
        self.fx_fetch.setCursor(Qt.PointingHandCursor)
        self.fx_fetch.clicked.connect(self.on_fetch_clicked)
        h2.addWidget(self.fx_fetch)
        v.addLayout(h2)
        self.fx_stamp = cap("")
        self.fx_stamp.setWordWrap(True)
        v.addWidget(self.fx_stamp)
        h3 = QHBoxLayout()
        h3.addWidget(cap("기준일"))
        h3.addWidget(self.fx_date, 1)
        v.addLayout(h3)
        self.fx_res, rl = self._result_box()
        self.fx_note = cap("")
        self.fx_note.setWordWrap(True)
        for w in (self.fx_amt, self.fx_rate, self.fx_date):
            w.textChanged.connect(self.update_fx)
        self.fx_cur.currentTextChanged.connect(self.update_fx)
        return self._frame("외화 환산", "금액 × 환율", v, rl, self.fx_note)

    def update_fx(self) -> None:
        if not self.fx_amt.text().strip() or not self.fx_rate.text().strip():
            self.fx_res.setText("")
            self.fx_note.setText("")
            return
        try:
            r = cc.convert_fx(self.fx_amt.text(), self.fx_cur.currentText(), self.fx_rate.text(), self.fx_date.text())
        except ValueError:
            self.fx_res.setText("")
            self.fx_note.setText("금액과 환율에 숫자를 입력하세요")
            return
        self.fx_res.setText(r.text)
        self.fx_note.setText(r.note + (f"\n{r.hint}" if r.hint else ""))

    # -- 현재 환율 가져오기
    def on_fetch_clicked(self) -> None:
        if self._worker is not None:
            return
        skip = bool(self.qs and self.qs.value("fx_notice_skip", False, type=bool))
        if not skip:
            dlg = FxNoticeDialog(self)
            if dlg.exec() != QDialog.Accepted:
                return
            if dlg.skip.isChecked() and self.qs:
                self.qs.setValue("fx_notice_skip", True)
        self.start_fetch()

    def start_fetch(self) -> None:
        self.fx_fetch.setEnabled(False)
        self.fx_fetch.setText("가져오는 중…")
        self.fx_stamp.setStyleSheet("")
        self.fx_stamp.setText("")
        self._worker = FxWorker(self.fx_cur.currentText(), self.fetch_fn)
        self._worker.done.connect(self._on_fetched)
        self._worker.start()

    def _on_fetched(self, fx, err: str) -> None:
        w, self._worker = self._worker, None
        if w is not None:
            w.wait()
            w.deleteLater()
        self.fx_fetch.setEnabled(True)
        self.fx_fetch.setText("현재 환율 가져오기")
        if fx is None:
            self.fx_stamp.setStyleSheet(f"color:{C_WARN};")
            self.fx_stamp.setText(err)
            return
        self.fx_stamp.setStyleSheet("")
        self.fx_rate.setText(format(fx.rate, "f").rstrip("0").rstrip("."))
        d = fx.as_of
        self.fx_date.setText(f"{d.year}년 {d.month}월 {d.day}일")
        self.fx_stamp.setText(f"{cc.format_fx_stamp(d)} · 시장 참고 환율 (직접 수정 가능)")


# ------------------------------------------------------------------ 메인 창
class MainWindow(QMainWindow):
    HISTORY_MAX = 30

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(900, 700)
        self.setMinimumSize(820, 640)
        self.qs = QSettings(SETTINGS_ORG, SETTINGS_ORG)
        self.color_mode = str(self.qs.value("color_mode", "color"))
        self.default_decimals = int(self.qs.value("decimals", 1))
        self.history: list[dict] = self._load_history()
        self._saved_unit = "억원"
        self._loading = False
        self.last_result: cc.CalcResult | None = None
        self.last_input: cc.CalcInput | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_growth_tab(), "증감률")
        self.unit_tab = UnitTab(self.copy_text, self.qs)
        self.tabs.addTab(self.unit_tab, "단위·환율 변환")
        root.addWidget(self.tabs, 1)
        self.decimals.setCurrentIndex(max(0, min(2, self.default_decimals)))
        self.recalc()

    # -- 구성
    def _build_header(self) -> QFrame:
        h = QFrame()
        h.setObjectName("header")
        h.setFixedHeight(40)
        lay = QHBoxLayout(h)
        lay.setContentsMargins(12, 0, 8, 0)
        lay.setSpacing(8)
        logo = QLabel("Q")
        logo.setObjectName("logo")
        logo.setFixedSize(20, 20)
        logo.setAlignment(Qt.AlignCenter)
        title = QLabel(APP_NAME)
        title.setObjectName("title")
        self.toast_lbl = QLabel("")
        self.toast_lbl.setObjectName("toast")
        badge = QLabel("표기 기준: 아주경제 스타일북 2021년판")
        badge.setObjectName("badge")
        badge.setFixedHeight(22)
        gear = QPushButton("설정")
        gear.setObjectName("gear")
        gear.setCursor(Qt.PointingHandCursor)
        gear.clicked.connect(self.open_settings)
        lay.addWidget(logo)
        lay.addWidget(title)
        lay.addStretch(1)
        lay.addWidget(self.toast_lbl)
        lay.addWidget(badge, 0, Qt.AlignVCenter)
        lay.addWidget(gear)
        return h

    def _build_growth_tab(self) -> QWidget:
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._build_left())
        body.addWidget(self._build_right(), 1)
        outer.addLayout(body, 1)
        outer.addWidget(self._build_footer())
        return tab

    def _build_left(self) -> QFrame:
        p = QFrame()
        p.setObjectName("panel")
        p.setFixedWidth(262)
        v = QVBoxLayout(p)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(5)

        v.addWidget(cap("계산 종류"))
        self.kind = Segmented(["금액·수량", "비율(%p)"])
        v.addWidget(self.kind)
        v.addSpacing(5)

        row = QHBoxLayout()
        c1 = QVBoxLayout()
        c1.setSpacing(4)
        c1.addWidget(cap("항목명"))
        self.item = QLineEdit()
        self.item.setPlaceholderText("예: 매출")
        c1.addWidget(self.item)
        c2 = QVBoxLayout()
        c2.setSpacing(4)
        c2.addWidget(cap("서술어 유형"))
        self.type = QComboBox()
        self.type.addItems(list(cc.TYPES))
        c2.addWidget(self.type)
        row.addLayout(c1, 4)
        row.addLayout(c2, 5)
        v.addLayout(row)
        v.addSpacing(5)

        v.addWidget(cap("비교 기준"))
        self.basis = QComboBox()
        self.basis.setEditable(True)
        self.basis.addItems(list(cc.BASIS_PRESETS))
        v.addWidget(self.basis)
        v.addSpacing(5)

        v.addWidget(cap("기준값 (이전)"))
        self.prev_label, self.prev = QLineEdit(), QLineEdit()
        self.prev_label.setPlaceholderText("예: 2025년 3분기")
        self.prev.setPlaceholderText("기준값")
        self.prev.setAlignment(Qt.AlignRight)
        v.addLayout(self._pair(self.prev_label, self.prev))
        v.addSpacing(5)

        v.addWidget(cap("현재값"))
        self.cur_label, self.cur = QLineEdit(), QLineEdit()
        self.cur_label.setPlaceholderText("예: 2026년 3분기")
        self.cur.setPlaceholderText("현재값")
        self.cur.setAlignment(Qt.AlignRight)
        v.addLayout(self._pair(self.cur_label, self.cur))
        self.fc = Segmented(["확정", "전망"])
        v.addWidget(self.fc)
        self.agent = QLineEdit()
        self.agent.setPlaceholderText("전망 주체 (예: ○○증권)")
        self.agent.setVisible(False)
        v.addWidget(self.agent)
        v.addSpacing(5)

        row2 = QHBoxLayout()
        u1 = QVBoxLayout()
        u1.setSpacing(4)
        u1.addWidget(cap("단위"))
        self.unit = QComboBox()
        self.unit.setEditable(True)
        self.unit.addItems(list(cc.UNIT_PRESETS))
        u1.addWidget(self.unit)
        u2 = QVBoxLayout()
        u2.setSpacing(4)
        u2.addWidget(cap("소수점"))
        self.decimals = QComboBox()
        self.decimals.addItems(["0자리", "1자리", "2자리"])
        u2.addWidget(self.decimals)
        row2.addLayout(u1, 1)
        row2.addLayout(u2, 1)
        v.addLayout(row2)
        v.addSpacing(8)

        row3 = QHBoxLayout()
        bulk = QPushButton("여러 건 붙여넣기")
        bulk.setCursor(Qt.PointingHandCursor)
        bulk.clicked.connect(self.open_bulk)
        clear = QPushButton("지우기")
        clear.setCursor(Qt.PointingHandCursor)
        clear.clicked.connect(self.clear_inputs)
        row3.addWidget(bulk, 1)
        row3.addWidget(clear)
        v.addLayout(row3)
        v.addStretch(1)

        # 신호 연결
        self.kind.changed.connect(self._on_kind)
        self.type.currentIndexChanged.connect(self._on_type)
        self.fc.changed.connect(self._on_forecast)
        for w in (self.item, self.prev_label, self.prev, self.cur_label, self.cur, self.agent):
            w.textChanged.connect(self.recalc)
        for w in (self.basis, self.unit):
            w.currentTextChanged.connect(self.recalc)
        self.decimals.currentIndexChanged.connect(self.recalc)
        return p

    def _pair(self, label_edit: QLineEdit, value_edit: QLineEdit) -> QHBoxLayout:
        h = QHBoxLayout()
        h.setSpacing(6)
        h.addWidget(label_edit, 3)
        h.addWidget(value_edit, 2)
        return h

    def _build_right(self) -> QScrollArea:
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        w = QWidget()
        sc.setWidget(w)
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 12)
        v.setSpacing(8)
        cards = QHBoxLayout()
        cards.setSpacing(8)
        self.card_main, self.card2, self.card3 = StatCard(big=True), StatCard(), StatCard()
        cards.addWidget(self.card_main, 14)
        cards.addWidget(self.card2, 10)
        cards.addWidget(self.card3, 10)
        v.addLayout(cards)
        v.addSpacing(4)
        v.addWidget(cap("기사 문장 (클릭해서 복사)"))
        self.sent_box = QVBoxLayout()
        self.sent_box.setSpacing(6)
        v.addLayout(self.sent_box)
        self.empty_lbl = cap("")
        self.empty_lbl.setWordWrap(True)
        v.addWidget(self.empty_lbl)
        hint = cap("한 문장은 60자 이하를 권장해요. 서술어는 유형에 따라 바뀌어요: 실적·수량은 증가·감소, 금리는 인상·인하, 가격·지수는 상승·하락")
        hint.setWordWrap(True)
        v.addWidget(hint)
        self.notice = QFrame()
        self.notice.setObjectName("notice")
        nl = QVBoxLayout(self.notice)
        nl.setContentsMargins(10, 7, 10, 7)
        self.notice_lbl = QLabel("")
        self.notice_lbl.setWordWrap(True)
        nl.addWidget(self.notice_lbl)
        v.addWidget(self.notice)
        v.addSpacing(4)
        v.addWidget(cap("최근 계산"))
        self.chips = QHBoxLayout()
        self.chips.setSpacing(6)
        v.addLayout(self.chips)
        v.addStretch(1)
        return sc

    def _build_footer(self) -> QFrame:
        f = QFrame()
        f.setObjectName("footer")
        f.setFixedHeight(46)
        lay = QHBoxLayout(f)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.addWidget(cap("복사한 계산은 이 PC에만 기록돼요"))
        lay.addStretch(1)
        hist = QPushButton("기록 보기")
        hist.setCursor(Qt.PointingHandCursor)
        hist.clicked.connect(self.open_history)
        self.copy_first = QPushButton("첫 문장 복사")
        self.copy_first.setObjectName("primary")
        self.copy_first.setCursor(Qt.PointingHandCursor)
        self.copy_first.clicked.connect(self._copy_first)
        lay.addWidget(hist)
        lay.addWidget(self.copy_first)
        return f

    # -- 입력 읽기/쓰기
    def read_input(self) -> cc.CalcInput:
        return cc.CalcInput(
            kind=cc.KIND_PP if self.kind.index() == 1 else cc.KIND_AMOUNT,
            item=self.item.text(),
            type=self.type.currentText(),
            basis=self.basis.currentText(),
            prev_label=self.prev_label.text(),
            prev=self.prev.text(),
            cur_label=self.cur_label.text(),
            cur=self.cur.text(),
            unit="%" if self.kind.index() == 1 else self.unit.currentText(),
            decimals=self.decimals.currentIndex(),
            forecast=self.fc.index() == 1,
            agent=self.agent.text(),
        )

    def apply_input(self, inp: cc.CalcInput) -> None:
        self._loading = True
        try:
            self.kind.set_index(1 if inp.kind == cc.KIND_PP else 0)
            self._apply_kind(1 if inp.kind == cc.KIND_PP else 0, keep_unit=inp.unit)
            self.item.setText(inp.item)
            i = self.type.findText(inp.type)
            self.type.setCurrentIndex(max(0, i))
            self.basis.setEditText(inp.basis)
            self.prev_label.setText(inp.prev_label)
            self.prev.setText(inp.prev)
            self.cur_label.setText(inp.cur_label)
            self.cur.setText(inp.cur)
            if inp.kind != cc.KIND_PP:
                self.unit.setEditText(inp.unit)
            self.decimals.setCurrentIndex(max(0, min(2, inp.decimals)))
            self.fc.set_index(1 if inp.forecast else 0)
            self.agent.setText(inp.agent)
            self.agent.setVisible(inp.forecast)
        finally:
            self._loading = False
        self.recalc()

    def clear_inputs(self) -> None:
        self._loading = True
        for w in (self.item, self.prev_label, self.prev, self.cur_label, self.cur, self.agent):
            w.clear()
        self._loading = False
        self.recalc()
        self.item.setFocus()

    def _apply_kind(self, idx: int, keep_unit: str | None = None) -> None:
        if idx == 1:
            if self.unit.isEnabled():
                self._saved_unit = self.unit.currentText() or "억원"
            self.unit.setEditText("%")
            self.unit.setEnabled(False)
        else:
            self.unit.setEnabled(True)
            self.unit.setEditText(keep_unit or self._saved_unit or "억원")

    def _on_kind(self, idx: int) -> None:
        self._apply_kind(idx)
        self.recalc()

    def _on_type(self) -> None:
        if self._loading:
            return
        if self.type.currentText() == cc.TYPE_RATE and self.kind.index() == 0:
            self.kind.set_index(1)
            self._apply_kind(1)
        self.recalc()

    def _on_forecast(self, idx: int) -> None:
        self.agent.setVisible(idx == 1)
        self.recalc()

    # -- 계산과 표시
    def recalc(self, *_args) -> None:
        if self._loading:
            return
        inp = self.read_input()
        res = cc.compute(inp)
        self.last_input, self.last_result = inp, res
        self._show(res)

    def _dir_color(self, d: str) -> str | None:
        if self.color_mode != "color":
            return None
        return {"up": C_UP, "down": C_DOWN}.get(d)

    def _show(self, res: cc.CalcResult) -> None:
        # 증감 카드
        if not res.ok:
            self.card_main.set("증감률", "—")
            self.card2.set("증감액", "—")
            self.card3.set("배율", "—")
        else:
            arrow = {"up": "↗ ", "down": "↘ "}.get(res.direction, "")
            if res.main_text in ("계산 불가", "확인 필요"):
                arrow = ""
            color = self._dir_color(res.direction) if arrow else None
            self.card_main.set(res.main_label, arrow + res.main_text, color, color)
            self.card2.set(res.card2_label, res.card2_text)
            self.card3.set(res.card3_label, res.card3_text)
        # 문장
        self._clear_layout(self.sent_box)
        for i, s in enumerate(res.sentences):
            row = SentenceRow(s, primary=(i == 0))
            row.clicked.connect(self.copy_text)
            self.sent_box.addWidget(row)
        self.empty_lbl.setText(res.error if not res.ok else "")
        self.empty_lbl.setVisible(not res.ok)
        # 안내
        if res.notices:
            self.notice_lbl.setText("\n".join(res.notices))
            self.notice.setProperty("level", "warn")
            self.notice_lbl.setStyleSheet(f"color:{C_WARN};")
        else:
            self.notice_lbl.setText("기준값이 0이거나 음수면 흑자전환, 적자전환, 적자지속 같은 표현을 안내해요")
            self.notice.setProperty("level", "soft")
            self.notice_lbl.setStyleSheet(f"color:{C_MUTED};")
        self.notice.style().unpolish(self.notice)
        self.notice.style().polish(self.notice)
        self.copy_first.setEnabled(bool(res.sentences))
        self._refresh_chips()

    @staticmethod
    def _clear_layout(layout) -> None:
        """레이아웃 안 위젯을 즉시 화면에서 떼어 내고 지운다 (지운 줄의 잔상 방지)."""
        while layout.count():
            it = layout.takeAt(0)
            w = it.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def _refresh_chips(self) -> None:
        self._clear_layout(self.chips)
        for h in self.history[:3]:
            full = h.get("summary", "")
            text = h.get("chip") or (full if len(full) <= 18 else full[:17] + "…")
            b = QPushButton(text)
            b.setObjectName("chip")
            b.setToolTip(full)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, hh=h: self.apply_input(cc.CalcInput.from_dict(hh["input"])))
            self.chips.addWidget(b)
        self.chips.addStretch(1)

    # -- 복사와 기록
    def copy_text(self, text: str, record: bool = True) -> None:
        QGuiApplication.clipboard().setText(text)
        self.toast("복사했어요")
        if record and self.tabs.currentIndex() == 0 and self.last_result and self.last_result.ok:
            self._record(self.last_input, self.last_result)

    def _copy_first(self) -> None:
        if self.last_result and self.last_result.sentences:
            self.copy_text(self.last_result.sentences[0])

    def toast(self, msg: str) -> None:
        self.toast_lbl.setText(msg)
        QTimer.singleShot(1800, lambda: self.toast_lbl.setText(""))

    def _record(self, inp: cc.CalcInput, res: cc.CalcResult) -> None:
        entry = {
            "input": inp.to_dict(),
            "summary": res.summary,
            "chip": f"{(inp.item or '수치').strip()} {res.main_text}",
            "at": datetime.now().strftime("%m-%d %H:%M"),
        }
        if self.history and self.history[0].get("summary") == entry["summary"]:
            self.history[0] = entry
        else:
            self.history.insert(0, entry)
        del self.history[self.HISTORY_MAX:]
        self.qs.setValue("history", json.dumps(self.history, ensure_ascii=False))
        self._refresh_chips()

    def _load_history(self) -> list[dict]:
        try:
            data = json.loads(str(self.qs.value("history", "[]")))
            return [h for h in data if isinstance(h, dict) and "input" in h][: self.HISTORY_MAX]
        except (ValueError, TypeError):
            return []

    # -- 대화상자
    def open_settings(self) -> None:
        dlg = SettingsDialog(self, self.color_mode, self.default_decimals)
        if dlg.exec():
            self.color_mode, self.default_decimals = dlg.values()
            self.qs.setValue("color_mode", self.color_mode)
            self.qs.setValue("decimals", self.default_decimals)
            self.decimals.setCurrentIndex(self.default_decimals)
            self.recalc()

    def open_history(self) -> None:
        dlg = HistoryDialog(self, self.history)
        dlg.exec()
        if dlg.cleared:
            self.history = []
            self.qs.setValue("history", "[]")
            self._refresh_chips()
        if dlg.chosen:
            self.apply_input(cc.CalcInput.from_dict(dlg.chosen["input"]))
            self.tabs.setCurrentIndex(0)

    def open_bulk(self) -> None:
        BulkDialog(self, self.read_input(), self.copy_text).exec()


def main() -> int:
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("QNumberCalc.App")
    except Exception:  # 윈도우가 아니면 건너뜀
        pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_palette(app)
    app.setStyleSheet(STYLE)
    icon = _icon_from_embedded()
    app.setWindowIcon(icon)
    win = MainWindow()
    win.setWindowIcon(icon)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
