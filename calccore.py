"""Q 수치 계산기 계산 로직. 화면과 무관한 순수 함수 모음.

표기는 아주경제 스타일북(2021년판)과 교열 기준을 따른다.
- 만·억·조는 한글로 숫자 뒤에 붙여 쓰고 쉼표는 쓰지 않는다 (2조3765억4528만2654원)
- 원·명 같은 한 글자 단위는 붙이고, 달러처럼 두 글자 이상 단위는 띄운다
- 증감률에는 비교 기준을 붙이고, 비율끼리의 차이는 %p로 쓴다
- 외화는 어림수에 '약'을 붙여 원화 환산액을 괄호로 적는다
"""
from __future__ import annotations

import re
from datetime import datetime
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

SCALE_MULT = {"": 10**0, "만": 10**4, "억": 10**8, "조": 10**12}
SCALE_CHARS = "만억조"

TYPE_REAL = "실적·수량"
TYPE_RATE = "금리"
TYPE_PRICE = "가격·지수"
TYPES = (TYPE_REAL, TYPE_RATE, TYPE_PRICE)

KIND_AMOUNT = "amount"
KIND_PP = "pp"

BASIS_PRESETS = (
    "전년 동기 대비",
    "전분기 대비",
    "전월 대비",
    "전년 대비",
    "전 거래일 대비",
    "연초 대비",
)

UNIT_PRESETS = (
    "억원", "만원", "원", "조원", "명", "만명", "건", "개", "가구", "대", "곳",
    "달러", "억 달러", "%", "포인트",
)

FX_CURRENCIES = ("달러", "엔", "유로", "위안", "파운드")

M2_TO_PYEONG = Decimal("0.3025")
FX_SIG_DIGITS = 3

RELATIVE_TIME = re.compile(r"(올해|금년|내년|작년|지난|이번|최근|어제|오늘|올 )")

# 서술어 (유형별). 금리는 인상·인하, 주가·지수는 상승·하락을 쓴다
VERBS = {
    TYPE_REAL: {
        "up": {"past": "증가했다", "short": "늘었다", "future": "증가할", "noun": "증가"},
        "down": {"past": "감소했다", "short": "줄었다", "future": "감소할", "noun": "감소"},
    },
    TYPE_RATE: {
        "up": {"past": "인상됐다", "short": "인상됐다", "future": "인상될", "noun": "인상"},
        "down": {"past": "인하됐다", "short": "인하됐다", "future": "인하될", "noun": "인하"},
    },
    TYPE_PRICE: {
        "up": {"past": "상승했다", "short": "올랐다", "future": "상승할", "noun": "상승"},
        "down": {"past": "하락했다", "short": "내렸다", "future": "하락할", "noun": "하락"},
    },
}


# ---------------------------------------------------------------- 숫자 읽기
_PLAIN_RE = re.compile(r"\d*\.?\d+")
_SCALED_RE = re.compile(r"(\d+(?:\.\d+)?)(조|억|만)?")


def _clean(text: str) -> tuple[str, bool]:
    """공백과 쉼표를 지우고 음수 표시(-, −, △, 괄호)를 읽어 (본문, 음수 여부)를 돌려준다."""
    s = (text or "").strip().replace(",", "").replace(" ", "").replace(" ", "")
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    if s[:1] in ("-", "−", "△"):
        neg, s = (not neg), s[1:]
    return s, neg


def parse_number(text: str) -> Decimal:
    """일반 숫자 입력(1,380 / -640 / △640 / 12.5). 잘못된 입력이면 ValueError."""
    s, neg = _clean(text)
    if not _PLAIN_RE.fullmatch(s):
        raise ValueError("숫자가 아니에요")
    d = Decimal(s)
    return -d if neg else d


def parse_amount(text: str) -> Decimal:
    """만·억·조가 섞인 금액 입력(1조2345억, 1000만, 1,234,500). 잘못된 입력이면 ValueError."""
    s, neg = _clean(text)
    s = re.sub(r"(원|달러|엔|유로|위안|명|건|개)$", "", s)
    if not s:
        raise ValueError("숫자가 아니에요")
    if _PLAIN_RE.fullmatch(s):
        d = Decimal(s)
        return -d if neg else d
    pos, total = 0, Decimal(0)
    for m in _SCALED_RE.finditer(s):
        if m.start() != pos:
            raise ValueError("숫자가 아니에요")
        pos = m.end()
        total += Decimal(m.group(1)) * SCALE_MULT[m.group(2) or ""]
    if pos != len(s):
        raise ValueError("숫자가 아니에요")
    return -total if neg else total


# ---------------------------------------------------------------- 숫자 쓰기
def plain(d: Decimal) -> str:
    """지수 표기 없이 입력한 자릿수 그대로 문자열로 만든다."""
    return format(d, "f")


def strip_zeros(d: Decimal) -> Decimal:
    """25.0 -> 25, 25.40 -> 25.4"""
    if d == d.to_integral_value():
        return d.quantize(Decimal(1))
    return d.normalize()


def quantize_half_up(d: Decimal, decimals: int) -> Decimal:
    return d.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def round_sig(d: Decimal, digits: int = FX_SIG_DIGITS) -> Decimal:
    """유효숫자 digits자리로 반올림(어림수). 외화 환산액에 쓴다."""
    if d == 0:
        return d
    exp = d.adjusted() - (digits - 1)
    r = d.quantize(Decimal(1).scaleb(exp), rounding=ROUND_HALF_UP)
    return Decimal(int(r)) if exp > 0 else r


def split_unit(unit: str) -> tuple[str, str]:
    """'억원' -> ('억', '원'), '억 달러' -> ('억', '달러'), '%' -> ('', '%')"""
    u = (unit or "").replace(" ", "").strip()
    if u and u[0] in SCALE_CHARS:
        return u[0], u[1:]
    return "", u


def _is_hangul(s: str) -> bool:
    return bool(s) and all("가" <= c <= "힣" for c in s)


ATTACHED_UNITS = {"분기"}  # 스타일북이 1분기, 2분기처럼 붙이도록 정한 단위


def base_needs_space(base: str) -> bool:
    """두 글자 이상의 한글 단위(달러, 포인트)는 띄어 쓰고, 한 글자 단위와 기호는 붙인다."""
    return len(base) >= 2 and _is_hangul(base) and base not in ATTACHED_UNITS


def _decompose(total: int) -> str:
    parts = []
    for mult, ch in ((10**12, "조"), (10**8, "억"), (10**4, "만")):
        q, total = divmod(total, mult)
        if q:
            parts.append(f"{q}{ch}")
    if total:
        parts.append(str(total))
    return "".join(parts) or "0"


def format_quantity(value: Decimal, unit: str = "", *, sign: bool = False) -> str:
    """값과 단위를 스타일북 표기로 합친다. 예) 1380억원, 1만2345명, 10만 달러, 21.5%"""
    scale, base = split_unit(unit)
    neg = value < 0
    v = abs(value)
    total = v * SCALE_MULT[scale]
    if base not in ("", "%") and total == total.to_integral_value() and total >= 10000:
        body = _decompose(int(total))
    else:
        body = plain(v) + scale
    sep = " " if base and base_needs_space(base) else ""
    prefix = "-" if neg else ("+" if sign and v != 0 else "")
    return f"{prefix}{body}{sep}{base}"


# ---------------------------------------------------------------- 조사
_JONG_RIEUL = 8


def _jong(word: str) -> int | None:
    """마지막 글자의 받침 번호. 받침이 없으면 0, 읽을 수 없으면 0으로 본다."""
    for ch in reversed(word.strip()):
        if "가" <= ch <= "힣":
            return (ord(ch) - 0xAC00) % 28
        if ch.isdigit():
            return {"0": 21, "1": _JONG_RIEUL, "3": 16, "6": 1, "7": _JONG_RIEUL, "8": _JONG_RIEUL}.get(ch, 0)
        if ch in "%pP㎡℃)]":
            return 0
        if ch in "lLmMnNrR":
            return 21
        if ch in "㎏":
            return 16
        if ch.isalpha():
            return 0
    return 0


def josa(word: str, kind: str) -> str:
    """kind: '은/는' '이/가' '을/를' '과/와' '으로/로'"""
    j = _jong(word) or 0
    if kind == "은/는":
        return "은" if j else "는"
    if kind == "이/가":
        return "이" if j else "가"
    if kind == "을/를":
        return "을" if j else "를"
    if kind == "과/와":
        return "과" if j else "와"
    if kind == "으로/로":
        return "으로" if j and j != _JONG_RIEUL else "로"
    raise ValueError(kind)


def with_josa(word: str, kind: str) -> str:
    return word + josa(word, kind)


# ---------------------------------------------------------------- 증감률 계산
@dataclass
class CalcInput:
    kind: str = KIND_AMOUNT
    item: str = ""
    type: str = TYPE_REAL
    basis: str = BASIS_PRESETS[0]
    prev_label: str = ""
    prev: str = ""
    cur_label: str = ""
    cur: str = ""
    unit: str = "억원"
    decimals: int = 1
    forecast: bool = False
    agent: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @staticmethod
    def from_dict(d: dict) -> "CalcInput":
        base = CalcInput()
        for k in base.__dict__:
            if k in d:
                setattr(base, k, d[k])
        return base


@dataclass
class CalcResult:
    ok: bool = False
    error: str = ""
    direction: str = "flat"  # up / down / flat
    main_label: str = "증감률"
    main_text: str = "—"
    card2_label: str = "증감액"
    card2_text: str = "—"
    card3_label: str = "배율"
    card3_text: str = "—"
    sentences: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    summary: str = ""


def _basis_parts(basis: str) -> tuple[str, str]:
    """비교 기준 문구와 명사형(대비를 뗀 것). 기준이 없으면 확인 필요 표시를 돌려준다."""
    b = (basis or "").strip()
    if not b:
        return "(비교 기준 확인 필요)", "(비교 기준)"
    noun = re.sub(r"\s*대비$", "", b).strip() or b
    return b, noun


def _dir(prev: Decimal, cur: Decimal) -> str:
    return "up" if cur > prev else ("down" if cur < prev else "flat")


def compute(inp: CalcInput) -> CalcResult:
    res = CalcResult()
    try:
        prev = parse_number(inp.prev)
        cur = parse_number(inp.cur)
    except ValueError:
        res.error = "기준값과 현재값에 숫자를 입력하세요"
        return res

    item = (inp.item or "").strip() or "수치"
    basis, basis_noun = _basis_parts(inp.basis)
    decimals = max(0, min(4, int(inp.decimals)))
    vt = VERBS.get(inp.type, VERBS[TYPE_REAL])
    notices: list[str] = []
    res.ok = True

    if not (inp.basis or "").strip():
        notices.append("비교 기준이 비어 있어요. 기준을 밝히지 않은 증감률은 확인이 필요해요")
    for lab in (inp.prev_label, inp.cur_label):
        if lab and RELATIVE_TIME.search(lab):
            notices.append("시점은 '2026년 3분기'처럼 절대 날짜로 쓰는 것이 좋아요")
            break
    if inp.forecast and not (inp.agent or "").strip():
        notices.append("전망치는 전망한 곳을 밝혀야 해요. 전망 주체를 입력하세요")
    agent = (inp.agent or "").strip() or "(전망 주체)"

    if inp.kind == KIND_PP:
        _compute_pp(inp, res, item, basis, basis_noun, prev, cur, decimals, vt, notices, agent)
    else:
        _compute_amount(inp, res, item, basis, basis_noun, prev, cur, decimals, vt, notices, agent)

    if inp.kind == KIND_AMOUNT and split_unit(inp.unit)[1] == "%":
        notices.append("단위가 %인 값끼리 비교하면 %p가 맞아요. '비율(%p)'로 바꿔 보세요")
    if inp.type == TYPE_RATE and inp.kind == KIND_AMOUNT:
        notices.append("금리처럼 비율 자체가 바뀐 경우는 퍼센트포인트(%p)로 써요")
    res.notices = notices
    return res


def _sign_text(d: Decimal, decimals: int, suffix: str) -> str:
    q = quantize_half_up(d, decimals)
    sign = "+" if q > 0 else ("-" if q < 0 else "")
    return f"{sign}{plain(abs(q))}{suffix}"


def _period_prefix(label: str) -> str:
    return f"{label.strip()} " if (label or "").strip() else ""


def _compute_amount(inp, res, item, basis, basis_noun, prev, cur, decimals, vt, notices, agent):
    unit = inp.unit
    topic = with_josa(item, "은/는")
    subj = with_josa(item, "이/가")
    cur_t = format_quantity(cur, unit)
    prev_t = format_quantity(prev, unit)
    diff = cur - prev
    d = _dir(prev, cur)
    res.direction = d
    res.card2_text = format_quantity(diff, unit, sign=True) if diff != 0 else format_quantity(Decimal(0), unit)
    res.main_label = f"증감률 ({basis_noun} 기준)" if (inp.basis or "").strip() else "증감률 (기준 확인 필요)"

    # 기준값이 0
    if prev == 0:
        res.main_text = "계산 불가"
        res.card3_label, res.card3_text = "배율", "—"
        notices.append("기준값이 0이라 증감률을 계산할 수 없어요. 증감액만 보여 드려요")
        res.sentences = [f"{topic} {cur_t}{josa(cur_t, '을/를')} 기록했다."]
        res.summary = f"{item} {prev_t} → {cur_t} · 기준값 0"
        return

    # 부호가 바뀌거나 적자가 이어지는 경우
    if prev < 0 or cur < 0:
        _compute_loss_cases(inp, res, item, basis_noun, prev, cur, decimals, unit, topic, notices, cur_t, prev_t)
        return

    rate = (cur - prev) / prev * 100
    rate_q = quantize_half_up(rate, decimals)
    rate_abs = plain(abs(rate_q))
    res.main_text = _sign_text(rate, decimals, "%")
    ratio = quantize_half_up(cur / prev, 2)
    res.card3_label, res.card3_text = "배율", f"{plain(ratio)}배"
    if rate_q == 0 and cur != prev:
        notices.append("반올림하면 0%예요. 소수점 자리를 늘려 보세요")
    res.summary = f"{item} {prev_t} → {cur_t} · {res.main_text}"

    if d == "flat":
        res.sentences = [
            f"{topic} {cur_t}{josa(cur_t, '으로/로')} {basis_noun}{josa(basis_noun, '과/와')} 같았다.",
            f"{topic} {cur_t}{josa(cur_t, '으로/로')} 변동이 없었다.",
        ]
        return

    v = vt[d]
    diff_abs = format_quantity(abs(diff), unit)
    if inp.forecast:
        a = with_josa(agent, "은/는")
        res.sentences = [
            f"{a} {subj} {cur_t}{josa(cur_t, '으로/로')} {basis} {rate_abs}% {v['future']} 것으로 전망했다.",
            f"{a} {subj} {prev_t}에서 {cur_t}{josa(cur_t, '으로/로')} {rate_abs}% {v['future']} 것으로 내다봤다.",
        ]
        return
    pre = _period_prefix(inp.cur_label)
    res.sentences = [
        f"{topic} {cur_t}{josa(cur_t, '으로/로')} {basis} {rate_abs}% {v['past']}.",
        f"{pre}{topic} {cur_t}{josa(cur_t, '으로/로')} {basis_noun}({prev_t})보다 {diff_abs} {v['short']}.",
        f"{topic} {prev_t}에서 {cur_t}{josa(cur_t, '으로/로')} {rate_abs}% {v['short']}.",
    ]


def _compute_loss_cases(inp, res, item, basis_noun, prev, cur, decimals, unit, topic, notices, cur_t, prev_t):
    """기준값이나 현재값이 음수일 때. 증감률 대신 흑자전환, 적자전환, 적자지속으로 안내한다."""
    notices.append("기준값이나 현재값이 음수예요. 증감률 대신 흑자·적자 표현으로 안내해요")
    res.card3_label, res.card3_text = "배율", "—"
    cur_abs_t = format_quantity(abs(cur), unit)
    prev_abs_t = format_quantity(abs(prev), unit)

    if prev < 0 < cur:
        res.direction = "up"
        res.main_label, res.main_text = "판정", "흑자전환"
        res.sentences = [f"{topic} {cur_t}{josa(cur_t, '으로/로')} {basis_noun} 적자에서 흑자전환했다."]
    elif prev > 0 > cur:
        res.direction = "down"
        res.main_label, res.main_text = "판정", "적자전환"
        res.sentences = [f"{topic} {basis_noun} 흑자에서 적자로 돌아서 {cur_abs_t}의 적자를 기록했다."]
    elif prev < 0 and cur < 0:
        wider = cur < prev
        res.direction = "down" if wider else "up"
        word = "확대" if wider else "축소"
        pct = (abs(cur) / abs(prev) - 1) * 100
        pct_q = quantize_half_up(pct, decimals)
        res.main_label, res.main_text = "판정", "적자지속"
        res.card3_label = f"적자 {word}율"
        res.card3_text = _sign_text(pct, decimals, "%")
        res.sentences = [
            f"{topic} {basis_noun}에 이어 {cur_abs_t}의 적자를 냈다.",
            f"{topic} 적자 규모가 {prev_abs_t}에서 {cur_abs_t}{josa(cur_abs_t, '으로/로')} {word}됐다.",
            f"{topic} 적자가 {basis_noun}보다 {plain(abs(pct_q))}% {word}됐다.",
        ]
        if inp.forecast:
            res.sentences = res.sentences[:2]
    else:  # 한쪽이 0이고 다른 쪽이 음수
        res.direction = _dir(prev, cur)
        res.main_label, res.main_text = "판정", "확인 필요"
        res.sentences = [f"{topic} {basis_noun}의 {prev_t}에서 {cur_t}{josa(cur_t, '으로/로')} 바뀌었다."]
    res.card2_text = format_quantity(cur - prev, unit, sign=True)
    res.summary = f"{item} {prev_t} → {cur_t} · {res.main_text}"


def _compute_pp(inp, res, item, basis, basis_noun, prev, cur, decimals, vt, notices, agent):
    topic = with_josa(item, "은/는")
    subj = with_josa(item, "이/가")
    prev_t = f"{plain(prev)}%"
    cur_t = f"{plain(cur)}%"
    diff = cur - prev
    d = _dir(prev, cur)
    res.direction = d
    res.main_label = "변동 폭 (%p)"
    res.main_text = _sign_text(diff, decimals, "%p")
    res.card2_label = "비율 변화율 (참고)"
    if prev > 0:
        rate = (cur - prev) / prev * 100
        res.card2_text = _sign_text(rate, decimals, "%")
        res.card3_label, res.card3_text = "배율", f"{plain(quantize_half_up(cur / prev, 2))}배"
    res.summary = f"{item} {plain(prev)} → {plain(cur)} · {res.main_text}"
    diff_q = quantize_half_up(diff, decimals)
    if diff_q == 0 and cur != prev:
        notices.append("반올림하면 0%p예요. 소수점 자리를 늘려 보세요")
    pp = plain(abs(diff_q))

    if d == "flat":
        res.sentences = [
            f"{topic} {cur_t}{josa(cur_t, '으로/로')} {basis_noun}{josa(basis_noun, '과/와')} 같았다.",
            f"{topic} {cur_t}{josa(cur_t, '으로/로')} 변동이 없었다.",
        ]
        return
    v = vt[d]
    if inp.forecast:
        a = with_josa(agent, "은/는")
        res.sentences = [
            f"{a} {subj} {cur_t}{josa(cur_t, '으로/로')} {basis} {pp}%p {v['future']} 것으로 전망했다.",
            f"{a} {subj} {prev_t}에서 {cur_t}{josa(cur_t, '으로/로')} {pp}%p {v['future']} 것으로 내다봤다.",
        ]
        return
    pre = _period_prefix(inp.cur_label)
    res.sentences = [
        f"{topic} {cur_t}{josa(cur_t, '으로/로')} {basis} {pp}%p {v['past']}.",
        f"{topic} {prev_t}에서 {cur_t}{josa(cur_t, '으로/로')} {pp}%p {v['short']}.",
        f"{pre}{topic} {cur_t}{josa(cur_t, '으로/로')} {basis_noun}({prev_t})보다 {pp}%p {v['short']}.",
    ]


# ---------------------------------------------------------------- 단위·환율
def big_number(text: str, base: str = "원") -> str:
    """숫자 <-> 만·억·조 표기. 한글 단위가 들어 있으면 숫자로, 숫자면 한글 표기로 바꾼다."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("숫자를 입력하세요")
    if any(c in raw for c in SCALE_CHARS):
        n = parse_amount(raw)
        if n != n.to_integral_value():
            return plain(n)
        return f"{int(n):,}"
    n = parse_amount(raw)
    return format_quantity(n, base)


def convert_area(text: str, to_pyeong: bool = True) -> str:
    v = parse_number(text)
    if to_pyeong:
        p = strip_zeros(quantize_half_up(v * M2_TO_PYEONG, 1))
        return f"{format_quantity(v, '㎡')}(약 {plain(p)}평)"
    m2 = strip_zeros(quantize_half_up(v / M2_TO_PYEONG, 1))
    return f"{format_quantity(v, '평')}(약 {format_quantity(m2, '㎡')})"


@dataclass
class FxResult:
    text: str
    note: str
    hint: str = ""


def convert_fx(amount_text: str, currency: str, rate_text: str, date_text: str = "") -> FxResult:
    amount = parse_amount(amount_text)
    rate = parse_number(rate_text)
    if rate <= 0:
        raise ValueError("환율은 0보다 커야 해요")
    cur = (currency or "").strip() or "달러"
    won = round_sig(amount * rate)
    text = f"{format_quantity(amount, cur)}(약 {format_quantity(won, '원')})"
    note = f"환산 기준: 1{cur}={plain(rate)}원"
    if (date_text or "").strip():
        note += f", {date_text.strip()}"
    hint = ""
    if cur == "달러":
        hint = "달러는 미국 달러예요. 다른 나라 달러는 앞에 국명을 붙여 입력하세요"
    return FxResult(text, note, hint)


# ---------------------------------------------------------------- 현재 환율 가져오기
FX_API_URL = "https://open.er-api.com/v6/latest/USD"
FX_CODES = {"달러": "USD", "엔": "JPY", "유로": "EUR", "위안": "CNY", "파운드": "GBP"}


@dataclass
class FxRate:
    rate: Decimal          # 1단위당 원
    as_of: datetime        # 환율 제공처의 갱신 시각 (현지 시간)


class FxFetchError(Exception):
    """환율을 가져오지 못했을 때. 메시지는 사용자에게 그대로 보여 준다."""


def parse_fx_payload(payload: dict, currency: str) -> FxRate:
    """open.er-api.com 응답에서 '통화 1단위당 원' 환율을 뽑는다 (달러 기준 교차 환율)."""
    code = FX_CODES.get((currency or "").strip())
    if not code:
        raise FxFetchError("이 통화는 환율 가져오기를 지원하지 않아요. 환율을 직접 입력하세요")
    try:
        if payload.get("result") != "success":
            raise KeyError("result")
        rates = payload["rates"]
        krw = Decimal(str(rates["KRW"]))
        cur = Decimal(str(rates[code]))
        if krw <= 0 or cur <= 0:
            raise ValueError
        stamp = datetime.fromtimestamp(int(payload["time_last_update_unix"]))
    except (KeyError, TypeError, ValueError, ArithmeticError):
        raise FxFetchError("환율 정보를 읽지 못했어요. 환율을 직접 입력하세요") from None
    rate = (krw / cur).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return FxRate(rate, stamp)


def fetch_fx_rate(currency: str, timeout: float = 6.0, opener=None) -> FxRate:
    """인터넷에서 최신 환율을 받아 온다. opener는 테스트용으로 바꿔 끼울 수 있다."""
    import json
    import urllib.error
    import urllib.request

    if not FX_CODES.get((currency or "").strip()):
        raise FxFetchError("이 통화는 환율 가져오기를 지원하지 않아요. 환율을 직접 입력하세요")
    open_fn = opener or urllib.request.urlopen
    try:
        req = urllib.request.Request(FX_API_URL, headers={"User-Agent": "QNumberCalc/1.0"})
        with open_fn(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        raise FxFetchError("환율을 가져오지 못했어요. 인터넷 연결을 확인하거나 환율을 직접 입력하세요") from None
    return parse_fx_payload(payload, currency)


def format_fx_stamp(dt: datetime) -> str:
    return f"{dt.month}월 {dt.day}일 {dt:%H:%M} 기준"


# ---------------------------------------------------------------- 여러 건 한꺼번에
def bulk_compute(text: str, base: CalcInput) -> list[dict]:
    """엑셀에서 복사한 '항목 / 기준값 / 현재값' 표를 한꺼번에 계산한다.

    첫 줄이 숫자가 아니면 제목 줄로 보고 건너뛴다. 설정(비교 기준, 단위, 소수점, 종류, 유형)은 base를 따른다.
    """
    from dataclasses import replace

    rows: list[dict] = []
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    for idx, line in enumerate(lines):
        if "\t" in line:
            toks = [t.strip() for t in line.split("\t")]
        else:
            toks = [t.strip() for t in line.rsplit(None, 2)]
        if len(toks) < 3:
            rows.append({"item": toks[0] if toks else line, "prev": "", "cur": "", "change": "", "sentence": "", "error": "항목, 기준값, 현재값 세 칸이 필요해요"})
            continue
        item, prev_s, cur_s = toks[0], toks[1], toks[2]
        if idx == 0:
            try:
                parse_number(prev_s)
                parse_number(cur_s)
            except ValueError:
                continue  # 제목 줄
        inp = replace(base, item=item, prev=prev_s, cur=cur_s, prev_label="", cur_label="")
        r = compute(inp)
        if not r.ok:
            rows.append({"item": item, "prev": prev_s, "cur": cur_s, "change": "", "sentence": "", "error": "숫자를 확인하세요"})
            continue
        rows.append({
            "item": item, "prev": prev_s, "cur": cur_s,
            "change": r.main_text, "sentence": r.sentences[0] if r.sentences else "", "error": "",
        })
    return rows
