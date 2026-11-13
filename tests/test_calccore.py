import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from decimal import Decimal as D

import pytest

import calccore as c


# ---- 숫자 표기 (스타일북) ----
@pytest.mark.parametrize("value,unit,expected", [
    (D(1380), "억원", "1380억원"),
    (D(12345), "억원", "1조2345억원"),
    (D(34), "만명", "34만명"),
    (D(12345), "명", "1만2345명"),
    (D(253745), "명", "25만3745명"),
    (D(23765452826), "원", "237억6545만2826원"),
    (D(10000000), "달러", "1000만 달러"),
    (D(100), "달러", "100 달러"),
    (D(500), "엔", "500엔"),
    (D("21.5"), "%", "21.5%"),
    (D(84), "㎡", "84㎡"),
    (D(12000), "㎡", "1만2000㎡"),
    (D("12.5"), "억원", "12억5000만원"),
    (D("12.55"), "%", "12.55%"),
    (D(9500), "원", "9500원"),
    (D(3), "분기", "3분기"),
    (D(0), "억원", "0억원"),
])
def test_format_quantity(value, unit, expected):
    assert c.format_quantity(value, unit) == expected


def test_format_quantity_sign_and_negative():
    assert c.format_quantity(D(130), "억원", sign=True) == "+130억원"
    assert c.format_quantity(D(-130), "억원", sign=True) == "-130억원"
    assert c.format_quantity(D(0), "억원", sign=True) == "0억원"


def test_stylebook_example():
    assert c.format_quantity(D(2_3765_4528_2654), "원") == "2조3765억4528만2654원"


# ---- 숫자 읽기 ----
def test_parse_number():
    assert c.parse_number("1,380") == D(1380)
    assert c.parse_number("-640") == D(-640)
    assert c.parse_number("△640") == D(-640)
    assert c.parse_number("(640)") == D(-640)
    assert c.parse_number("12.5") == D("12.5")
    for bad in ("", "abc", "1e5", "12억", "1.2.3"):
        with pytest.raises(ValueError):
            c.parse_number(bad)


def test_parse_amount():
    assert c.parse_amount("1000만") == D(10_000_000)
    assert c.parse_amount("1조2345억") == D(1_234_500_000_000)
    assert c.parse_amount("1,234,500") == D(1_234_500)
    assert c.parse_amount("12.5억") == D(1_250_000_000)
    assert c.parse_amount("3억4000만") == D(340_000_000)
    with pytest.raises(ValueError):
        c.parse_amount("억억")


# ---- 조사 ----
@pytest.mark.parametrize("word,kind,expected", [
    ("매출", "은/는", "매출은"),
    ("금리", "은/는", "금리는"),
    ("점유율", "은/는", "점유율은"),
    ("1380억원", "으로/로", "1380억원으로"),
    ("10.4%", "으로/로", "10.4%로"),
    ("3.3%p", "으로/로", "3.3%p로"),
    ("2000", "으로/로", "2000으로"),
    ("1250", "으로/로", "1250으로"),
    ("1천", "으로/로", "1천으로"),
    ("전년 동기", "과/와", "전년 동기와"),
    ("전월", "과/와", "전월과"),
    ("매출", "이/가", "매출이"),
    ("금리", "이/가", "금리가"),
    ("영업이익", "은/는", "영업이익은"),
])
def test_josa(word, kind, expected):
    assert c.with_josa(word, kind) == expected


# ---- 증감률 ----
def base_input(**kw):
    d = dict(item="매출", prev="1250", cur="1380", unit="억원", decimals=1,
             prev_label="2025년 3분기", cur_label="2026년 3분기")
    d.update(kw)
    return c.CalcInput(**d)


def test_growth_up():
    r = c.compute(base_input())
    assert r.ok and r.direction == "up"
    assert r.main_text == "+10.4%"
    assert r.card2_text == "+130억원"
    assert r.card3_text == "1.10배"
    assert r.sentences[0] == "매출은 1380억원으로 전년 동기 대비 10.4% 증가했다."
    assert r.sentences[1] == "2026년 3분기 매출은 1380억원으로 전년 동기(1250억원)보다 130억원 늘었다."
    assert r.sentences[2] == "매출은 1250억원에서 1380억원으로 10.4% 늘었다."
    assert all(len(s) <= 60 for s in r.sentences)
    assert r.summary == "매출 1250억원 → 1380억원 · +10.4%"


def test_growth_down_and_half_up():
    r = c.compute(base_input(item="영업이익", prev="820", cur="640"))
    assert r.direction == "down" and r.main_text == "-22.0%"
    assert r.sentences[0] == "영업이익은 640억원으로 전년 동기 대비 22.0% 감소했다."
    # 반올림은 사사오입 (은행가 반올림 아님): 2.25 -> 2.3
    r2 = c.compute(base_input(prev="1000", cur="1022.5"))
    assert r2.main_text == "+2.3%"


def test_growth_rounds_to_zero_notice():
    r = c.compute(base_input(prev="10000", cur="10001", decimals=1))
    assert r.main_text == "0.0%"
    assert any("반올림하면 0%" in n for n in r.notices)


def test_growth_flat():
    r = c.compute(base_input(prev="100", cur="100"))
    assert r.direction == "flat"
    assert r.sentences[0] == "매출은 100억원으로 전년 동기와 같았다."


def test_growth_unit_people_and_scale():
    r = c.compute(base_input(item="방문객", prev="34", cur="41", unit="만명"))
    assert r.main_text == "+20.6%"
    assert r.sentences[0] == "방문객은 41만명으로 전년 동기 대비 20.6% 증가했다."


def test_growth_verbs_by_type():
    r = c.compute(base_input(item="코스피", type=c.TYPE_PRICE, prev="2500", cur="2650", unit="포인트"))
    assert "상승했다" in r.sentences[0]
    assert "올랐다" in r.sentences[1]
    r = c.compute(base_input(item="코스피", type=c.TYPE_PRICE, prev="2650", cur="2500", unit="포인트"))
    assert "하락했다" in r.sentences[0]


def test_zero_base():
    r = c.compute(base_input(prev="0", cur="50"))
    assert r.main_text == "계산 불가"
    assert any("기준값이 0" in n for n in r.notices)


def test_loss_cases():
    r = c.compute(base_input(item="영업이익", prev="-120", cur="80"))
    assert r.main_text == "흑자전환"
    assert r.sentences[0] == "영업이익은 80억원으로 전년 동기 적자에서 흑자전환했다."
    r = c.compute(base_input(item="영업이익", prev="120", cur="-80"))
    assert r.main_text == "적자전환"
    assert "80억원의 적자를 기록했다" in r.sentences[0]
    r = c.compute(base_input(item="영업이익", prev="-100", cur="-150"))
    assert r.main_text == "적자지속" and r.card3_label == "적자 확대율" and r.card3_text == "+50.0%"
    assert r.sentences[0] == "영업이익은 전년 동기에 이어 150억원의 적자를 냈다."
    r = c.compute(base_input(item="영업이익", prev="-100", cur="-60"))
    assert r.main_text == "적자지속" and r.card3_label == "적자 축소율" and r.card3_text == "-40.0%"


def test_pp_mode():
    r = c.compute(base_input(kind=c.KIND_PP, item="점유율", prev="18.2", cur="21.5", type=c.TYPE_PRICE))
    assert r.main_text == "+3.3%p"
    assert r.card2_text == "+18.1%"
    assert r.sentences[0] == "점유율은 21.5%로 전년 동기 대비 3.3%p 상승했다."
    assert r.sentences[1] == "점유율은 18.2%에서 21.5%로 3.3%p 올랐다."


def test_rate_example():
    # 기준금리 3.00 -> 3.25 는 0.25퍼센트포인트 인상
    r = c.compute(base_input(kind=c.KIND_PP, item="기준금리", prev="3.00", cur="3.25",
                             type=c.TYPE_RATE, decimals=2, basis="직전 회의 대비"))
    assert r.sentences[0] == "기준금리는 3.25%로 직전 회의 대비 0.25%p 인상됐다."


def test_forecast_sentences():
    r = c.compute(base_input(forecast=True, agent="○○증권"))
    assert r.sentences[0] == "○○증권은 매출이 1380억원으로 전년 동기 대비 10.4% 증가할 것으로 전망했다."
    assert "내다봤다" in r.sentences[1]
    assert not r.notices or all("전망 주체" not in n for n in r.notices)
    r = c.compute(base_input(forecast=True))
    assert any("전망 주체" in n for n in r.notices)


def test_notices():
    r = c.compute(base_input(cur_label="올해 3분기"))
    assert any("절대 날짜" in n for n in r.notices)
    r = c.compute(base_input(basis=""))
    assert any("비교 기준이 비어" in n for n in r.notices)
    assert "(비교 기준 확인 필요)" in r.sentences[0]
    r = c.compute(base_input(unit="%"))
    assert any("%p" in n for n in r.notices)
    r = c.compute(base_input(type=c.TYPE_RATE))
    assert any("퍼센트포인트" in n for n in r.notices)


def test_invalid_input():
    r = c.compute(base_input(cur=""))
    assert not r.ok and r.error


# ---- 단위·환율 ----
def test_big_number():
    assert c.big_number("1234500000000") == "1조2345억원"
    assert c.big_number("1,234,500") == "123만4500원"
    assert c.big_number("1조2345억") == "1,234,500,000,000"
    assert c.big_number("34000", "명") == "3만4000명"
    with pytest.raises(ValueError):
        c.big_number("")


def test_area():
    assert c.convert_area("84") == "84㎡(약 25.4평)"
    assert c.convert_area("25", to_pyeong=False) == "25평(약 82.6㎡)"
    assert c.convert_area("100") == "100㎡(약 30.3평)"


def test_fx():
    r = c.convert_fx("1000만", "달러", "1380", "2026년 11월 11일")
    assert r.text == "1000만 달러(약 138억원)"
    assert r.note == "환산 기준: 1달러=1380원, 2026년 11월 11일"
    assert "미국 달러" in r.hint
    r = c.convert_fx("500", "엔", "9.2")
    assert r.text == "500엔(약 4600원)"
    r = c.convert_fx("1234", "달러", "1380")
    assert r.text == "1234 달러(약 170만원)"
    with pytest.raises(ValueError):
        c.convert_fx("1000", "달러", "0")


def test_bulk_compute():
    base = base_input()
    text = "항목\t기준값\t현재값\n매출\t1250\t1380\n영업이익\t820\t640\n잘못\tabc\t10\n"
    rows = c.bulk_compute(text, base)
    assert [r["item"] for r in rows] == ["매출", "영업이익", "잘못"]
    assert rows[0]["change"] == "+10.4%"
    assert rows[0]["sentence"] == "매출은 1380억원으로 전년 동기 대비 10.4% 증가했다."
    assert rows[1]["change"] == "-22.0%"
    assert rows[2]["error"]
    # 탭이 없어도 뒤에서 두 덩어리를 숫자로 읽는다
    rows = c.bulk_compute("총 매출 100 120", base)
    assert rows[0]["item"] == "총 매출" and rows[0]["change"] == "+20.0%"


# ---- 현재 환율 가져오기
import io
import json as _json

import pytest as _pytest

FX_PAYLOAD = {
    "result": "success",
    "time_last_update_unix": 1762822800,
    "rates": {"USD": 1, "KRW": 1468.5, "JPY": 154.0, "EUR": 0.86, "CNY": 7.1, "GBP": 0.76},
}


def test_parse_fx_payload_usd_and_jpy():
    r = c.parse_fx_payload(FX_PAYLOAD, "달러")
    assert str(r.rate) == "1468.50"
    j = c.parse_fx_payload(FX_PAYLOAD, "엔")
    assert str(j.rate) == "9.54"  # 1468.5 / 154


def test_parse_fx_payload_errors():
    with _pytest.raises(c.FxFetchError):
        c.parse_fx_payload(FX_PAYLOAD, "루피")
    with _pytest.raises(c.FxFetchError):
        c.parse_fx_payload({"result": "error"}, "달러")
    with _pytest.raises(c.FxFetchError):
        c.parse_fx_payload({"result": "success", "rates": {"USD": 1}, "time_last_update_unix": 1}, "달러")


class _FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_fetch_fx_rate_with_fake_opener():
    def opener(req, timeout=0):
        return _FakeResp(_json.dumps(FX_PAYLOAD).encode("utf-8"))

    r = c.fetch_fx_rate("달러", opener=opener)
    assert str(r.rate) == "1468.50"
    assert "기준" in c.format_fx_stamp(r.as_of)


def test_fetch_fx_rate_network_failure_message():
    def opener(req, timeout=0):
        raise OSError("offline")

    with _pytest.raises(c.FxFetchError) as e:
        c.fetch_fx_rate("달러", opener=opener)
    assert "직접 입력" in str(e.value)
