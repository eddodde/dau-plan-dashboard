import math
import pathlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── 기본 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title="VIP DAU 개선 실행 트래커",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

KFONT = "'Noto Sans KR','Malgun Gothic','Apple SD Gothic Neo',sans-serif"

# 목표 시나리오 (전년비 %) — 파일럿 실측 후 보정
SCENARIOS = [
    ("보수", -8.0, "트랙 B(재설치)만 성공", "#B0B0B0"),
    ("기본", -5.0, "트랙 A·B 부분 성공", "#4C72B0"),
    ("상한", -2.5, "앱푸시 반응 회복(커버 45%)", "#55A868"),
]
# 착수 시점 기준값 (2026-06, B2B 제외)
BASE = {"month": "2026-06", "dau": 18282, "yoy": -10.0, "stick": 22.5}

# ── 커스텀 CSS ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    .metric-card {
        background: #f8f9fa; border-radius: 10px; padding: 14px 18px;
        border-left: 4px solid #4C72B0; margin-bottom: 10px;
    }
    .metric-label { font-size: 13px; color: #666; margin-bottom: 4px; }
    .metric-value { font-size: 24px; font-weight: 700; color: #1a1a2e; }
    .metric-sub  { font-size: 12px; color: #888; margin-top: 2px; }
    .section-title {
        font-size: 18px; font-weight: 700; color: #1a1a2e;
        margin: 26px 0 12px 0; padding-bottom: 6px;
        border-bottom: 2px solid #e9ecef; scroll-margin-top: 70px;
    }
    .hint { font-size: 12px; color: #999; margin: -4px 0 10px 0; }
    a.navlink {
        display: block; padding: 8px 12px; margin: 4px 0; border-radius: 8px;
        background: #f2f5fa; color: #2E68B0; text-decoration: none;
        font-size: 14px; font-weight: 600; border: 1px solid #e3e9f2;
    }
    a.navlink:hover { background: #e3ecf8; color: #163E78; }
    a.navlink.navsub { margin: 3px 0 3px 10px; font-size: 13px; padding: 6px 10px; }
    details.navacc { margin: 4px 0; }
    summary.navgroup { cursor: pointer; font-size: 12px; font-weight: 700; color: #55606f;
        letter-spacing: .02em; padding: 7px 8px; border-radius: 6px; list-style: none;
        user-select: none; background: #eef1f6; }
    summary.navgroup::-webkit-details-marker { display: none; }
    summary.navgroup:hover { background: #e3e9f2; color: #1a1a2e; }
    summary.navgroup::before { content: "▸ "; color: #99a3b3; }
    details[open] summary.navgroup::before { content: "▾ "; }
    .insight {
        background: #eef4fb; border-left: 4px solid #4C72B0; border-radius: 8px;
        padding: 12px 16px; margin: 6px 0 14px 0; font-size: 14px; line-height: 1.6;
    }
    .insight.warn { background: #fdeeee; border-left-color: #C44E52; }
    .insight.ok   { background: #eef7f0; border-left-color: #55A868; }
    .insight b { color: #1a1a2e; }
    .insight ul { margin: 0; padding-left: 20px; }
    .insight li { margin: 5px 0; }
    .insight .cap { font-size: 12px; font-weight: 700; color: #666; display: block; margin-bottom: 6px; }
    .lever { background: #f8f9fa; border-radius: 10px; border-top: 4px solid #4C72B0;
        padding: 14px 16px; font-size: 13.5px; line-height: 1.65; height: 100%; }
    .lever .lh { font-weight: 700; font-size: 14.5px; color: #1a1a2e; margin-bottom: 6px; }
    .lever .lt { display: inline-block; background: #e3e9f2; color: #55606f; font-size: 11px;
        padding: 1px 8px; border-radius: 10px; margin-bottom: 8px; }
    .lever.now  { border-top-color: #C44E52; }
    .lever.soon { border-top-color: #4C72B0; }
    .lever.keep { border-top-color: #55A868; }
    table.scen { width: 100%; border-collapse: collapse; font-size: 13.5px; margin: 4px 0 10px; }
    table.scen th { background: #1f3864; color: #fff; padding: 8px 10px; font-weight: 600; }
    table.scen td { border: 1px solid #e3e9f2; padding: 8px 10px; text-align: center; }
    table.scen td.l { text-align: left; }
</style>
""", unsafe_allow_html=True)


# ── 헬퍼 ───────────────────────────────────────────────────
def fnum(x):
    return f"{int(round(x)):,}"


def metric_card(label, value, sub="", color="#4C72B0"):
    st.markdown(
        f'<div class="metric-card" style="border-left-color:{color}">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-sub">{sub}</div></div>',
        unsafe_allow_html=True)


def section(title, hint="", anchor=None):
    aid = f' id="{anchor}"' if anchor else ""
    st.markdown(f'<div class="section-title"{aid}>{title}</div>', unsafe_allow_html=True)
    if hint:
        st.markdown(f'<div class="hint">{hint}</div>', unsafe_allow_html=True)


def insight(bullets, kind="", cap="요약"):
    if isinstance(bullets, str):
        bullets = [bullets]
    bullets = [b for b in bullets if b]
    if not bullets:
        return
    items = "".join(f"<li>{b}</li>" for b in bullets)
    head = f'<span class="cap">{cap}</span>' if cap else ""
    st.markdown(f'<div class="insight {kind}">{head}<ul>{items}</ul></div>', unsafe_allow_html=True)


def plot(fig, title=None):
    if title:
        st.markdown(f'<div style="font-weight:700;font-size:15px;margin:10px 0 -6px">{title}</div>',
                    unsafe_allow_html=True)
    fig.update_layout(font=dict(family=KFONT))
    fig.update_yaxes(exponentformat="none", separatethousands=True)
    st.plotly_chart(fig, use_container_width=True)


def drop_incomplete_months(s, cutoff):
    """월초(MS) 인덱스 시계열에서 '월말 > cutoff'인 집계 중 부분월 제거."""
    if s is None or len(s) == 0 or cutoff is None:
        return s
    ends = s.index + pd.offsets.MonthEnd(0)
    return s[ends <= pd.Timestamp(cutoff)]


def ab_test(s1, n1, s2, n2):
    """두 비율 z-검정 (양측). 반환: (rate1, rate2, lift%p, z, p-value)."""
    if min(n1, n2) <= 0:
        return None
    p1, p2 = s1 / n1, s2 / n2
    p = (s1 + s2) / (n1 + n2)
    se = math.sqrt(max(p * (1 - p) * (1 / n1 + 1 / n2), 1e-12))
    z = (p1 - p2) / se
    pval = math.erfc(abs(z) / math.sqrt(2))
    return p1 * 100, p2 * 100, (p1 - p2) * 100, z, pval


# ── 데이터 로더 (진단 대시보드와 동일 포맷) ─────────────────
@st.cache_data(show_spinner=False)
def load_dau_channel(file):
    """채널별 일 DAU 파일 → long [date, channel, value]. (col3=2025-01-01 연속일)"""
    raw = pd.read_excel(file, sheet_name=0, header=None)
    base = pd.Timestamp(2025, 1, 1)
    recs = []
    for r in range(2, raw.shape[0]):
        ch = str(raw.iat[r, 1]).strip().replace("*", "")
        if not ch or ch.lower() == "nan":
            continue
        for c in range(2, raw.shape[1]):
            v = pd.to_numeric(raw.iat[r, c], errors="coerce")
            if pd.notna(v):
                recs.append({"date": base + pd.Timedelta(days=c - 2), "channel": ch, "value": v})
    return pd.DataFrame(recs)


@st.cache_data(show_spinner=False)
def load_dau_monthly_simple(file):
    """간이 포맷(구분×월, DAU/MAU 행, VIP 합계·B2B 제외) → long [date, metric, value]."""
    raw = pd.read_excel(file, sheet_name=0, header=None)
    years = raw.iloc[0].ffill()
    months = raw.iloc[1]
    col_dates = {}
    for c in range(1, raw.shape[1]):
        s = str(months.iloc[c]).replace("월", "").strip()
        try:
            yi = int(float(str(years.iloc[c]).replace("년", "").strip()))
        except (ValueError, TypeError):
            continue
        if s.isdigit():
            col_dates[c] = pd.Timestamp(yi, int(s), 1)
    recs = []
    for r in range(2, raw.shape[0]):
        met = str(raw.iat[r, 0]).strip().upper()
        if met not in ("DAU", "MAU"):
            continue
        for c, dt in col_dates.items():
            v = pd.to_numeric(raw.iat[r, c], errors="coerce")
            if pd.notna(v):
                recs.append({"date": dt, "metric": met, "value": v})
    return pd.DataFrame(recs)


def load_actions():
    p = pathlib.Path(__file__).parent / "data" / "actions.csv"
    if not p.exists():
        return None
    return pd.read_csv(p).fillna("")


# ── 사이드바 ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎯 VIP DAU 개선 실행 트래커")
    st.caption("실행 과제의 진행 상태와 성과를 주 1회 갱신하여 추적")

    with st.expander("📂 실적 데이터 업로드", expanded=False):
        up_chdau = st.file_uploader("① 채널별 일 DAU (.xlsx)", type=["xlsx", "xls"], key="up_ch",
                                    help="B2B 제외 기준 — DAU 실적 트래킹용(권장)")
        up_mau = st.file_uploader("② 월별 VIP MAU/DAU (.xlsx)", type=["xlsx", "xls"], key="up_mau",
                                  help="간이 포맷(구분×월). ① 미업로드 시 대체")
        up_tb = st.file_uploader("③ 트랙 B 결과 (재설치, .csv)", type=["csv"], key="up_tb")
        up_ta = st.file_uploader("④ 트랙 A 결과 (실시간 A/B, .csv)", type=["csv"], key="up_ta")

    st.markdown("**메뉴**")
    NAV = [
        ("계획", [("sec-now", "현황 요약"), ("sec-plan", "추진 배경·실행 계획")]),
        ("실행", [("sec-exec", "실행 현황 (주간 갱신)")]),
        ("실적", [("sec-kpi", "DAU 실적 — 월간·주간"),
                  ("sec-trackb", "트랙 B — 재설치"),
                  ("sec-tracka", "트랙 A — 실시간 A/B")]),
        ("기준·양식", [("sec-judge", "판정 기준·업로드 양식")]),
    ]
    _nav = ""
    for _gi, (gname, links) in enumerate(NAV):
        _open = " open" if _gi == 0 else ""
        inner = "".join(f'<a class="navlink navsub" href="#{aid}">{label}</a>' for aid, label in links)
        _nav += (f'<details class="navacc" name="navmenu"{_open}>'
                 f'<summary class="navgroup">{gname}</summary>{inner}</details>')
    st.markdown(_nav, unsafe_allow_html=True)

st.title("🎯 VIP DAU 개선 실행 트래커")
st.caption("원인 진단은 'VIP 도달·이탈 진단 대시보드' 참조 — 본 대시보드는 실행 과제의 진행 상태와 성과 추적을 목적으로 함")

# ── 데이터 사전 처리 (현황 요약·실적 섹션 공용) ─────────────
dau_m, dau_src, tot_d, cutoff = None, "", None, None
n_bad = 0
if up_chdau is not None:
    dc = load_dau_channel(up_chdau)
    tot_d = dc[dc["channel"] == "TOTAL"].set_index("date")["value"].sort_index()
    med_d = tot_d.rolling(91, center=True, min_periods=30).median()
    bad = tot_d.index[(tot_d / med_d > 1.6).fillna(False)]
    n_bad = len(bad)
    tot_d = tot_d.drop(bad)
    cutoff = tot_d.index.max()
    dau_m = tot_d.groupby(pd.Grouper(freq="MS")).mean()
    dau_m = drop_incomplete_months(dau_m, cutoff)
    dau_src = f"채널 파일 DAU(B2B 제외{'·급증일 ' + str(n_bad) + '일 제외' if n_bad else ''})"
elif up_mau is not None:
    dm = load_dau_monthly_simple(up_mau)
    s = dm[dm["metric"] == "DAU"].set_index("date")["value"].sort_index()
    cutoff = pd.Timestamp.today().normalize()
    dau_m = drop_incomplete_months(s, cutoff)
    dau_src = "월별 파일 DAU(25.9~10 중복집계 오염 가능성 유의)"

# 파생: 최근 완료월·전년비·주간
cur_kpi = {}
if dau_m is not None and len(dau_m) >= 13:
    last_dt = dau_m.index.max()
    last_v = dau_m.loc[last_dt]
    base_dt = last_dt - pd.DateOffset(years=1)
    base_v = dau_m.loc[base_dt] if base_dt in dau_m.index else None
    cur_kpi = {"dt": last_dt, "dau": last_v,
               "yoy": (last_v / base_v - 1) * 100 if base_v else None,
               "base": base_v}
wk, prev_wk = None, None
if tot_d is not None:
    wk = tot_d.groupby(pd.Grouper(freq="W-SUN")).mean()
    wk = wk[wk.index <= cutoff]          # 진행 중인 주 제외
    prev_wk = wk.shift(52)               # 전년 동주(52주 전)

# ════════════════════════════════════════════════════════════
# 현황 요약
# ════════════════════════════════════════════════════════════
section("현황 요약", f"착수 시점 기준: {BASE['month']} DAU {fnum(BASE['dau'])} · 전년비 {BASE['yoy']:+.1f}% (B2B 제외)",
        anchor="sec-now")

if cur_kpi:
    yoy = cur_kpi["yoy"]
    h1, h2, h3, h4 = st.columns(4)
    with h1:
        metric_card(f"VIP DAU (최근 완료월 {cur_kpi['dt']:%Y-%m})", fnum(cur_kpi["dau"]), dau_src)
    with h2:
        imp = (yoy - BASE["yoy"]) if yoy is not None else None
        metric_card("전년 동월비", f"{yoy:+.1f}%" if yoy is not None else "—",
                    (f"착수 시점 {BASE['yoy']:+.1f}% 대비 {imp:+.1f}%p" if imp is not None else ""),
                    color="#C44E52" if (yoy or 0) < 0 else "#55A868")
    with h3:
        w4 = None
        if wk is not None and len(wk) >= 4 and prev_wk.tail(4).notna().all():
            w4 = (wk.tail(4).mean() / prev_wk.tail(4).mean() - 1) * 100
        metric_card("최근 4주 평균 전년비", f"{w4:+.1f}%" if w4 is not None else "—",
                    "주간 변동 평활 — 추세 판단용",
                    color="#C44E52" if (w4 or 0) < 0 else "#55A868")
    with h4:
        if yoy is not None:
            met = [n for n, t, _, _ in SCENARIOS if yoy >= t]
            pos = f"'{met[-1]}' 달성" if met else "전 시나리오 미달"
            col = "#55A868" if met else "#C44E52"
            metric_card("시나리오 위치", pos,
                        " · ".join(f"{n} {t:+.0f}%" for n, t, _, _ in SCENARIOS), color=col)
else:
    st.info("사이드바의 '실적 데이터 업로드'에서 채널별 일 DAU 파일을 업로드하면 최신 현황이 표시됩니다. "
            "미업로드 시 착수 시점 기준값만 표기합니다.")
    h1, h2, h3 = st.columns(3)
    with h1: metric_card(f"VIP DAU ({BASE['month']})", fnum(BASE["dau"]), "착수 시점 기준 · B2B 제외")
    with h2: metric_card("전년 동월비", f"{BASE['yoy']:+.1f}%", "착수 시점 기준", color="#C44E52")
    with h3: metric_card("스티키니스(DAU/MAU)", f"{BASE['stick']:.1f}%", "26.7% → 22.5% (전년 동월 대비)")

# ════════════════════════════════════════════════════════════
# ① 추진 배경·실행 계획
# ════════════════════════════════════════════════════════════
section("① 추진 배경 및 실행 계획",
        "배경 → 실행 트랙(A·B) → 목표 시나리오 → 운영 방식", anchor="sec-plan")

insight([
    "VIP DAU 전년비 <b>−10% 역신장</b>. 반면 MAU(월 방문자 수)는 <b>+9.5% 증가</b> → 고객 수가 아닌 "
    "<b>방문 빈도의 문제</b>(스티키니스 26.7%→22.5%, 월평균 방문일수 8.1일→6.8일).",
    "빈도의 자발적 회복은 기대하기 어렵고(최대 혜택인 전관행사로도 미회복), 상품·시장 요인은 CRM 통제 범위 밖 → "
    "CRM의 통제 가능 수단은 <b>발송(터치)의 재방문 전환력 제고</b>.",
    "병목은 두 가지 — ① <b>발송 시점</b>: 현행 D-1(전일) 행동 기준 발송으로 고객 의사결정 시점과 불일치 "
    "② <b>도달</b>: VIP 수신동의자의 약 2/3가 앱 미보유/삭제 상태로 푸시 미도달. 트랙 A·B가 각각에 대응.",
], cap="추진 배경")

tc1, tc2 = st.columns(2)
with tc1:
    st.markdown("""<div class="lever now"><div class="lt">트랙 B · 금주 착수 · 리드타임 없음</div>
    <div class="lh">채널 도달 — 앱 미보유/삭제 VIP 재설치</div>
    <ul style="margin:6px 0 0;padding-left:18px">
    <li><b>추진 내용</b>: 푸시 수신동의 상태이나 앱 미보유/삭제인 VIP(약 168,000명) 대상 문자·이메일·카카오 재설치 캠페인</li>
    <li><b>배경</b>: 미도달 상태에서는 발송 자체가 무효 — 재설치 시 푸시 도달 모수로 편입되어 트랙 A의 대상도 확대</li>
    <li><b>검증 방법</b>: 발송군 vs 대조군 — 재설치율 → 재설치 후 7일 내 재방문 → 인센티브 비용 대비 복귀 가치</li>
    <li><b>일정</b>: 금주 오퍼 확정·대상 추출 → 익주 1차 발송 → 2~4주 측정</li>
    <li><b>기대 효과</b>: 재설치 전환 1% 가정 시 DAU 하락분의 약 <b>10% 커버(상한)</b></li>
    </ul></div>""", unsafe_allow_html=True)
with tc2:
    st.markdown("""<div class="lever soon"><div class="lt">트랙 A · 핵심 레버 · 준비는 금주 착수</div>
    <div class="lh">행동 시점 정밀도 — D-1 발송의 실시간 전환</div>
    <ul style="margin:6px 0 0;padding-left:18px">
    <li><b>추진 내용</b>: 고객의 당일 행동(조회·검색·장바구니)을 감지하여 수 시간 내 관련 메시지를 발송하는 실시간 트리거로 전환</li>
    <li><b>배경</b>: 현행 D-1(전일) 행동 기준 발송은 고객 의사결정 시점과 불일치 — 앱푸시 경유 DAU가 −20%로 최대 하락 항목</li>
    <li><b>검증 방법</b>: 동질군 무작위 분할 A/B(실시간 vs D-1) — 발송→익일 재방문율로 판정</li>
    <li><b>일정</b>: 금주 실시간 데이터 적재 요청·세그먼트 설계 착수 → 적재 완료 후 2~4주 파일럿</li>
    <li><b>기대 효과</b>: 앱푸시 반응 회복 시 DAU 하락분의 최대 약 <b>45% 커버(상한)</b></li>
    </ul></div>""", unsafe_allow_html=True)

st.markdown("""<div class="lever keep" style="margin-top:10px"><div class="lt">상시 운영 (신규 과제 아님)</div>
<b>기존 운영 레버 유지</b> — 휴면 자동화·행동 트리거(D-1)·전관행사·발송량 관리는 기 운영 중으로 유지(중단 시 실적 후퇴),
수신거부율 가드레일 병행 모니터링. 해당 레버는 소진 단계로, 추가 개선 여지는 트랙 A·B에 있음.</div>""",
            unsafe_allow_html=True)

st.markdown('<div style="font-weight:700;font-size:15px;margin:16px 0 4px">목표 — 역신장 폭의 단계적 축소</div>',
            unsafe_allow_html=True)
rows = "".join(
    f'<tr><td><b style="color:{c}">{n}</b></td><td class="l">{d}</td>'
    f'<td><b>{t:+.1f}%</b></td></tr>'
    for n, t, d, c in SCENARIOS)
st.markdown(f"""
<table class="scen">
<tr><th>시나리오</th><th>가정</th><th>26년 하반기 전년비 목표</th></tr>
{rows}
<tr><td>현재</td><td class="l">착수 시점 ({BASE['month']}, B2B 제외)</td><td><b style="color:#C44E52">{BASE['yoy']:+.1f}%</b></td></tr>
</table>
""", unsafe_allow_html=True)
st.caption("DAU는 시장·상품 요인의 영향이 커 CRM 단독의 반등 목표는 과약속 소지 — 커버 상한(A 약 45% + B 약 10%) 기반의 "
           "단계 목표이며, 파일럿 실측 후 보정 예정.")

insight([
    "주 1회 갱신 — ① 최신 채널 DAU 파일 업로드(현황·실적 자동 갱신) ② '② 실행 현황' 과제 상태 갱신 "
    "③ 파일럿 결과 CSV 업로드(트랙 A·B 자동 판정).",
], cap="운영 방식")

# ════════════════════════════════════════════════════════════
# ② 실행 현황
# ════════════════════════════════════════════════════════════
section("② 실행 현황 (주간 갱신)",
        "상태 편집 후 CSV 다운로드 → 레포 data/actions.csv 교체 시 영구 반영 · 목표일 순 정렬", anchor="sec-exec")

acts = load_actions()
if acts is None:
    st.info("data/actions.csv 가 없습니다. 레포에 실행 과제 CSV를 추가하십시오.")
else:
    STATUS = ["예정", "진행중", "완료", "보류", "운영중"]
    edited = st.data_editor(
        acts, use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={
            "status": st.column_config.SelectboxColumn("상태", options=STATUS, width="small"),
            "track": st.column_config.TextColumn("트랙", width="medium"),
            "phase": st.column_config.TextColumn("단계", width="small"),
            "task": st.column_config.TextColumn("과제", width="large"),
            "due": st.column_config.TextColumn("목표일", width="small"),
            "note": st.column_config.TextColumn("비고", width="medium"),
        }, key="actions_editor")
    done = (edited["status"] == "완료").sum()
    doing = (edited["status"] == "진행중").sum()
    total = (edited["status"].isin(["예정", "진행중", "완료", "보류"])).sum()  # 운영중은 분모 제외
    pc1, pc2, pc3 = st.columns([1, 1, 2])
    with pc1: metric_card("완료", f"{done} / {total}", "상시 운영 과제는 분모 제외")
    with pc2: metric_card("진행중", f"{doing}건", "")
    with pc3:
        st.progress(done / total if total else 0.0)
        st.download_button("수정본 CSV 다운로드 (레포 data/actions.csv 교체용)",
                           edited.to_csv(index=False).encode("utf-8-sig"),
                           "actions.csv", "text/csv")

# ════════════════════════════════════════════════════════════
# ③ 실적 — DAU (월간·주간)
# ════════════════════════════════════════════════════════════
section("③ DAU 실적 — 목표 시나리오 대비",
        "월간: 완료월 기준 시나리오 대비 · 주간: 주 1회 보고용 최신 추이", anchor="sec-kpi")

if dau_m is None or len(dau_m) < 13:
    st.info("채널별 일 DAU 파일(권장) 또는 월별 MAU/DAU 파일 업로드 시 실적이 표시됩니다. "
            "(전년 동월 비교를 위해 13개월 이상 필요)")
else:
    cur_year = int(dau_m.index.max().year)
    act = dau_m[dau_m.index.year == cur_year]
    prev = dau_m[dau_m.index.year == cur_year - 1]
    prev_by_m = {d.month: v for d, v in prev.items()}

    months_x = list(range(1, 13))
    fig = go.Figure()
    fig.add_bar(x=[d.month for d in act.index], y=act.values, name=f"{cur_year} 실적",
                marker_color="#4C72B0")
    if len(prev):
        fig.add_scatter(x=[d.month for d in prev.index], y=prev.values, name=f"{cur_year-1} 실적",
                        mode="lines+markers", line=dict(color="#9aa7b8", width=2))
        for n, t, _, c in SCENARIOS:
            ys = [prev_by_m[m] * (1 + t / 100) if m in prev_by_m else None for m in months_x]
            fig.add_scatter(x=months_x, y=ys, name=f"목표 {n}({t:+.0f}%)",
                            mode="lines", line=dict(color=c, width=1.6, dash="dash"))
    fig.update_layout(height=380, margin=dict(t=10, b=10), hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                      yaxis=dict(title="VIP DAU(명)"))
    fig.update_xaxes(tickmode="array", tickvals=months_x,
                     ticktext=[f"{m}월" for m in months_x], title=None)
    plot(fig, f"{cur_year}년 월별 VIP DAU — 전년 실선 · 목표 점선(전년 동월 × 시나리오)")
    st.caption("집계 중 부분월 자동 제외 · 목표선 = 전년 동월 × (1 + 시나리오 전년비)")

    # 주간 뷰: 월 마감 전에도 매주 최신 실적 확인
    if wk is not None and len(wk) > 1:
        last_wk = wk.index.max()
        w_now = wk.iloc[-1]
        w_base = prev_wk.iloc[-1] if pd.notna(prev_wk.iloc[-1]) else None
        wyoy = (w_now / w_base - 1) * 100 if w_base else None
        wc1, wc2 = st.columns(2)
        with wc1: metric_card(f"최근 완료주 주평균 DAU (~{last_wk:%m/%d})", fnum(w_now), "월~일 평균")
        with wc2:
            metric_card("전년 동주비", f"{wyoy:+.1f}%" if wyoy is not None else "—",
                        f"전년 동주 {fnum(w_base)}" if w_base else "전년 데이터 없음",
                        color="#C44E52" if (wyoy or 0) < 0 else "#55A868")
        rec, base = wk.tail(12), prev_wk.tail(12)
        figw = go.Figure()
        figw.add_bar(x=rec.index, y=rec.values, name="주평균 DAU", marker_color="#4C72B0")
        figw.add_scatter(x=base.index, y=base.values, name="전년 동주", mode="lines+markers",
                         line=dict(color="#9aa7b8", width=2))
        figw.update_layout(height=280, margin=dict(t=10, b=10), hovermode="x unified",
                           legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                           yaxis=dict(title="주평균 DAU(명)"))
        plot(figw, "주간 실적 — 최근 12주 vs 전년 동주")
        st.caption("주 단위=월~일(완료된 주만 표시) · 전년 동주=52주 전 · 급증일 제외 반영")

# ════════════════════════════════════════════════════════════
# ④ 실적 — 트랙 B (재설치 캠페인)
# ════════════════════════════════════════════════════════════
section("④ 트랙 B 실적 — 미보유 재설치 캠페인",
        "발송군 vs 대조군: 재설치율 → 재설치 후 재방문 → 비용 효율", anchor="sec-trackb")

TB_COLS = ["date", "group", "targets", "reinstalls", "revisits_7d", "optouts", "cost"]
if up_tb is None:
    st.info("트랙 B 결과 CSV 업로드 시 자동 집계됩니다. 컬럼: " + ", ".join(TB_COLS) +
            " (group=발송/대조, cost=인센티브 비용·원)")
else:
    tb = pd.read_csv(up_tb)
    missing = [c for c in TB_COLS[:5] if c not in tb.columns]
    if missing:
        st.error(f"필수 컬럼 누락: {missing}")
    else:
        g = tb.groupby("group")[["targets", "reinstalls", "revisits_7d"]].sum()
        b1, b2, b3, b4 = st.columns(4)
        send = g.loc["발송"] if "발송" in g.index else None
        ctrl = g.loc["대조"] if "대조" in g.index else None
        if send is not None:
            rr = send["reinstalls"] / send["targets"] * 100 if send["targets"] else 0
            rv = send["revisits_7d"] / send["reinstalls"] * 100 if send["reinstalls"] else 0
            with b1: metric_card("재설치율 (발송군)", f"{rr:.2f}%",
                                 f"{fnum(send['reinstalls'])} / {fnum(send['targets'])}")
            with b2: metric_card("재설치 후 7일 재방문", f"{rv:.1f}%",
                                 f"{fnum(send['revisits_7d'])}명 — DAU 편입 대상")
        if send is not None and ctrl is not None and ctrl["targets"]:
            res = ab_test(send["reinstalls"], send["targets"], ctrl["reinstalls"], ctrl["targets"])
            if res:
                p1, p2, lift, z, pval = res
                sig = pval < 0.05
                with b3: metric_card("자연 재설치율 (대조군)", f"{p2:.2f}%",
                                     f"순증 리프트 {lift:+.2f}%p")
                with b4: metric_card("통계 판정", "유의" if sig else "유의차 없음",
                                     f"p={pval:.3f}", color="#55A868" if sig else "#C44E52")
        if "cost" in tb.columns and send is not None and send["reinstalls"]:
            cost = tb.loc[tb["group"] == "발송", "cost"].sum()
            if cost > 0:
                st.caption(f"재설치 1인당 비용 {fnum(cost / send['reinstalls'])}원 · "
                           f"7일 재방문 1인당 비용 {fnum(cost / max(send['revisits_7d'], 1))}원 — 복귀 가치와 비교하여 판정")
        ts = tb.copy()
        ts["date"] = pd.to_datetime(ts["date"])
        w = (ts[ts["group"] == "발송"].groupby(pd.Grouper(key="date", freq="W"))
             [["reinstalls", "revisits_7d"]].sum())
        if len(w) > 1:
            figb = go.Figure()
            figb.add_bar(x=w.index, y=w["reinstalls"], name="재설치", marker_color="#4C72B0")
            figb.add_bar(x=w.index, y=w["revisits_7d"], name="7일 재방문", marker_color="#55A868")
            figb.update_layout(height=280, margin=dict(t=10, b=10), barmode="group",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
            plot(figb, "주간 재설치·재방문 추이 (발송군)")

# ════════════════════════════════════════════════════════════
# ⑤ 실적 — 트랙 A (실시간 트리거 A/B)
# ════════════════════════════════════════════════════════════
section("⑤ 트랙 A 실적 — 실시간 트리거 vs D-1",
        "동질군 무작위 분할: 발송→익일 재방문율 리프트가 1차 판정 지표", anchor="sec-tracka")

TA_COLS = ["date", "group", "sent", "clicks", "revisits_d1"]
if up_ta is None:
    st.info("트랙 A 결과 CSV 업로드 시 자동 집계됩니다. 컬럼: " + ", ".join(TA_COLS) +
            " (group=실시간/D-1)")
else:
    ta = pd.read_csv(up_ta)
    missing = [c for c in TA_COLS[:3] if c not in ta.columns]
    if missing:
        st.error(f"필수 컬럼 누락: {missing}")
    else:
        g = ta.groupby("group")[["sent", "clicks", "revisits_d1"]].sum()
        rt = g.loc["실시간"] if "실시간" in g.index else None
        d1 = g.loc["D-1"] if "D-1" in g.index else None
        a1, a2, a3, a4 = st.columns(4)
        if rt is not None and d1 is not None and rt["sent"] and d1["sent"]:
            res = ab_test(rt["revisits_d1"], rt["sent"], d1["revisits_d1"], d1["sent"])
            if res:
                p1, p2, lift, z, pval = res
                sig = pval < 0.05
                with a1: metric_card("재방문율 (실시간)", f"{p1:.2f}%",
                                     f"{fnum(rt['revisits_d1'])} / {fnum(rt['sent'])}")
                with a2: metric_card("재방문율 (D-1)", f"{p2:.2f}%",
                                     f"{fnum(d1['revisits_d1'])} / {fnum(d1['sent'])}")
                with a3: metric_card("리프트", f"{lift:+.2f}%p",
                                     f"상대 {((p1/p2-1)*100 if p2 else 0):+.0f}%",
                                     color="#55A868" if lift > 0 else "#C44E52")
                with a4: metric_card("통계 판정", "유의" if sig else "유의차 없음",
                                     f"p={pval:.3f} (양측)", color="#55A868" if sig else "#C44E52")
                insight([
                    ("<b>실시간 트리거가 통계적으로 유의하게 우세</b> — 확대 적용 대상. 커버 상한(약 45%) 내 확산 계획 수립."
                     if sig and lift > 0 else
                     "<b>유의차 미확인</b> — 표본 추가 확보 또는 세그먼트·콘텐츠 재설계 후 재검정 필요."),
                ], "ok" if sig and lift > 0 else "warn", cap="판정")
        if "clicks" in ta.columns and rt is not None and d1 is not None:
            ctr_rt = rt["clicks"] / rt["sent"] * 100 if rt["sent"] else 0
            ctr_d1 = d1["clicks"] / d1["sent"] * 100 if d1["sent"] else 0
            st.caption(f"CTR — 실시간 {ctr_rt:.2f}% vs D-1 {ctr_d1:.2f}% (보조 지표)")

# ════════════════════════════════════════════════════════════
# ⑥ 판정 기준·업로드 양식
# ════════════════════════════════════════════════════════════
section("⑥ 판정 기준 · 업로드 양식", anchor="sec-judge")

st.markdown("""
<table class="scen">
<tr><th>트랙</th><th>성공 기준</th><th>미달 시 조치</th></tr>
<tr><td><b>A 실시간</b></td>
    <td class="l">실시간군 재방문율이 D-1군 대비 통계적으로 유의하게 높음(p&lt;0.05)</td>
    <td class="l">시점 정밀도 가설 기각 → 콘텐츠·오퍼 레버로 전환 검토</td></tr>
<tr><td><b>B 재설치</b></td>
    <td class="l">재설치→재방문 전환이 인센티브 비용 대비 복귀 가치 손익분기 초과 + 대조군 대비 유의 리프트</td>
    <td class="l">규모 축소·오퍼 재설계 (도달 확대 비효율 판정)</td></tr>
</table>
""", unsafe_allow_html=True)

t1, t2 = st.columns(2)
with t1:
    tb_tmpl = pd.DataFrame([
        {"date": "2026-07-24", "group": "발송", "targets": 50000, "reinstalls": 450,
         "revisits_7d": 180, "optouts": 30, "cost": 1350000},
        {"date": "2026-07-24", "group": "대조", "targets": 10000, "reinstalls": 25,
         "revisits_7d": 8, "optouts": 0, "cost": 0},
    ])
    st.download_button("트랙 B 결과 양식 CSV", tb_tmpl.to_csv(index=False).encode("utf-8-sig"),
                       "trackB_template.csv", "text/csv")
with t2:
    ta_tmpl = pd.DataFrame([
        {"date": "2026-08-10", "group": "실시간", "sent": 20000, "clicks": 900, "revisits_d1": 620},
        {"date": "2026-08-10", "group": "D-1", "sent": 20000, "clicks": 700, "revisits_d1": 480},
    ])
    st.download_button("트랙 A 결과 양식 CSV", ta_tmpl.to_csv(index=False).encode("utf-8-sig"),
                       "trackA_template.csv", "text/csv")

st.caption("데이터 파일은 레포에 커밋하지 않고 업로드로만 사용(공개 레포 정보보호) · 실행 현황(actions.csv)만 레포에 저장")
