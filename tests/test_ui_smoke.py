import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

import app as qapp
import calccore as cc


@pytest.fixture(scope="module")
def qt():
    a = QApplication.instance() or QApplication([])
    qapp.apply_palette(a)
    a.setStyleSheet(qapp.STYLE)
    return a


@pytest.fixture()
def win(qt, tmp_path):
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    w = qapp.MainWindow()
    w.show()
    yield w
    w.close()


def fill(w, **kw):
    w.item.setText(kw.get("item", "매출"))
    w.prev_label.setText(kw.get("prev_label", "2025년 3분기"))
    w.prev.setText(kw.get("prev", "1250"))
    w.cur_label.setText(kw.get("cur_label", "2026년 3분기"))
    w.cur.setText(kw.get("cur", "1380"))


def sentences(w):
    return [w.sent_box.itemAt(i).widget()._text for i in range(w.sent_box.count())]


def test_growth_flow(win):
    fill(win)
    assert win.card_main.value.text() == "↗ +10.4%"
    assert sentences(win)[0] == "매출은 1380억원으로 전년 동기 대비 10.4% 증가했다."
    assert win.card2.value.text() == "+130억원"


def test_down_and_plain_color_mode(win):
    win.color_mode = "plain"
    fill(win, prev="820", cur="640", item="영업이익")
    assert win.card_main.value.text() == "↘ -22.0%"
    assert win.card_main.value.styleSheet() == ""


def test_rate_type_switches_to_pp(win):
    win.type.setCurrentText(cc.TYPE_RATE)
    assert win.kind.index() == 1
    assert win.unit.isEnabled() is False
    fill(win, item="기준금리", prev="3.00", cur="3.25", prev_label="", cur_label="")
    win.decimals.setCurrentIndex(2)
    assert sentences(win)[0] == "기준금리는 3.25%로 전년 동기 대비 0.25%p 인상됐다."
    win.kind.set_index(0)
    win._on_kind(0)
    assert win.unit.isEnabled() is True


def test_forecast_shows_agent(win):
    win.fc.set_index(1)
    win._on_forecast(1)
    assert win.agent.isHidden() is False
    fill(win)
    win.agent.setText("○○증권")
    assert sentences(win)[0].startswith("○○증권은 매출이")


def test_copy_records_history_and_restores(win, qt):
    fill(win)
    win.copy_text(sentences(win)[0])
    assert qt.clipboard().text() == "매출은 1380억원으로 전년 동기 대비 10.4% 증가했다."
    assert win.history and win.history[0]["summary"] == "매출 1250억원 → 1380억원 · +10.4%"
    win.clear_inputs()
    assert sentences(win) == []
    win.apply_input(cc.CalcInput.from_dict(win.history[0]["input"]))
    assert win.cur.text() == "1380" and win.item.text() == "매출"


def test_invalid_input_message(win):
    win.item.setText("매출")
    win.prev.setText("abc")
    win.cur.setText("100")
    assert sentences(win) == []
    assert "숫자" in win.empty_lbl.text()


def test_unit_tab(win):
    t = win.unit_tab
    assert t.big_res.text() == "1조2345억원"
    assert t.area_res.text() == "84㎡(약 25.4평)"
    assert t.fx_res.text() == "1000만 달러(약 138억원)"
    t.big_in.setText("1조2345억")
    assert t.big_res.text() == "1,234,500,000,000"


def test_bulk_dialog(win):
    d = qapp.BulkDialog(win, win.read_input(), win.copy_text)
    d.box.setPlainText("항목\t기준값\t현재값\n매출\t1250\t1380\n영업이익\t820\t640")
    d.run()
    assert d.table.rowCount() == 2
    assert d.table.item(0, 3).text() == "+10.4%"


def _wait(t):
    import time
    from PySide6.QtWidgets import QApplication as A
    for _ in range(200):
        A.processEvents()
        if t._worker is None:
            return
        time.sleep(0.01)


def test_fx_fetch_success_and_notice_skip(win):
    from datetime import datetime
    t = win.unit_tab
    win.qs.setValue("fx_notice_skip", True)  # 안내 창 건너뛰기 설정
    t.fetch_fn = lambda cur: cc.FxRate(cc.Decimal("1468.50"), datetime(2026, 11, 11, 14, 20))
    t.fx_amt.setText("1000만")
    t.on_fetch_clicked()
    _wait(t)
    assert t.fx_rate.text() == "1468.5"
    assert t.fx_date.text() == "2026년 11월 11일"
    assert "11월 11일 14:20 기준" in t.fx_stamp.text()
    assert t.fx_res.text() == "1000만 달러(약 147억원)"
    assert t.fx_fetch.isEnabled()


def test_fx_fetch_failure_keeps_input(win):
    t = win.unit_tab
    win.qs.setValue("fx_notice_skip", True)

    def boom(cur):
        raise cc.FxFetchError("환율을 가져오지 못했어요. 인터넷 연결을 확인하거나 환율을 직접 입력하세요")

    t.fetch_fn = boom
    t.fx_rate.setText("1380")
    t.on_fetch_clicked()
    _wait(t)
    assert t.fx_rate.text() == "1380"
    assert "직접 입력" in t.fx_stamp.text()
    assert t.fx_fetch.isEnabled()


def test_fx_notice_dialog_cancel_does_not_fetch(win, monkeypatch):
    t = win.unit_tab
    win.qs.setValue("fx_notice_skip", False)
    called = []
    t.fetch_fn = lambda cur: called.append(cur)
    monkeypatch.setattr(qapp.FxNoticeDialog, "exec", lambda self: qapp.QDialog.Rejected)
    t.on_fetch_clicked()
    assert t._worker is None and not called
