import csv
import io
import os
from datetime import date, datetime

import streamlit as st

try:
    from dotenv import find_dotenv, load_dotenv
    load_dotenv(find_dotenv(usecwd=True))  # walks up from cwd to find .env
except ImportError:
    pass

from ingest import append_web_rfp, load_rfps, load_rfps_from_web, load_saved_web_rfps
from scorer import score_rfp

st.set_page_config(
    page_title="Risely · RFP Monitor",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_PATH = "data/rfps.json"

PRIORITY_STYLE = {"High": ("p-high", "🔴"), "Maybe": ("p-maybe", "🟡"), "Low": ("p-low", "⚪")}
STATUS_STYLE = {
    "Open": ("p-high", "🟢"),
    "Due Soon": ("p-maybe", "🟠"),
    "Closed": ("p-closed", "⛔"),
    "Unknown": ("p-gray", "❓"),
}


def html(s: str) -> None:
    """Strip per-line leading whitespace so markdown never treats indented HTML as a code block."""
    st.markdown("\n".join(ln.lstrip() for ln in s.split("\n")), unsafe_allow_html=True)


def load_and_score():
    local = load_rfps(DATA_PATH)
    web = load_saved_web_rfps()
    return sorted([score_rfp(r) for r in local + web], key=lambda r: r["score"], reverse=True)


def days_label(rfp: dict) -> str:
    days = rfp.get("days_remaining")
    if rfp.get("date_status") == "Closed" and days is not None:
        return f"{abs(days)} days overdue"
    if days is not None:
        return f"{days} days remaining"
    return "No deadline"


def pretty_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%b %d")
    except ValueError:
        return iso


_CSV_FIELDS = [
    "title", "institution", "product_fit", "secondary_fit",
    "score", "priority", "due_date", "date_status", "days_remaining",
    "summary", "recommended_action", "source", "source_url",
]


def generate_csv(rfp_list: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_CSV_FIELDS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for r in rfp_list:
        writer.writerow({f: r.get(f, "") for f in _CSV_FIELDS})
    return buf.getvalue().encode("utf-8")


if "selected" not in st.session_state:
    st.session_state.selected = 0

rfps = load_and_score()


# ── GLOBAL STYLES ─────────────────────────────────────────────────────────────
html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    box-sizing: border-box;
}

[data-testid="stAppViewContainer"], .stApp {
    background: linear-gradient(180deg, #ECE9F4 0%, #E7E3F2 100%) !important;
    min-height: 100vh;
}
[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; height: 0 !important; min-height: 0 !important; }
.main .block-container { padding: 0 2.5rem 3rem 2.5rem !important; max-width: 1400px !important; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer { visibility: hidden !important; }
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }

p, span, div, label { color: #14163A; }

[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
.list-head { display: flex; align-items: center; justify-content: space-between; margin: 2px 2px 10px 2px; }

.topbar { display: flex; align-items: center; padding: 14px 0 12px 0; border-bottom: 1px solid #DDD9EE; margin-bottom: 22px; }
.topbar-brand { font-size: 19px; font-weight: 800; color: #6B4EF5 !important; letter-spacing: -0.6px; margin-right: 36px; }
.topbar-nav { display: flex; gap: 2px; flex: 1; align-items: center; }
.nav-link { font-size: 13px; font-weight: 500; color: #6B6E89 !important; padding: 6px 14px; border-radius: 8px; cursor: pointer; }
.nav-link.active { background: #EFEBFE; color: #6B4EF5 !important; font-weight: 600; }
.topbar-actions { display: flex; gap: 8px; align-items: center; }
.icon-btn { width: 34px; height: 34px; background: white; border-radius: 10px; border: 1px solid #ECEAF5; display: inline-flex; align-items: center; justify-content: center; font-size: 14px; box-shadow: 0 1px 4px rgba(20,22,58,0.05); cursor: pointer; }
.avatar { width: 34px; height: 34px; background: linear-gradient(135deg, #6B4EF5, #8B6CF8); border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: white !important; }

.page-header { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 22px; }
.page-title { font-size: 32px; font-weight: 800; line-height: 1.1; margin: 0 0 6px 0; letter-spacing: -1px; color: #14163A; }
.grad-text { background: linear-gradient(130deg, #6B4EF5 0%, #E27BB1 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.page-subtitle { font-size: 14px; color: #6B6E89 !important; margin: 0; font-weight: 400; }
.header-actions { display: flex; gap: 8px; align-items: center; }
.synced-chip { background: white; border: 1px solid #ECEAF5; border-radius: 20px; padding: 5px 13px; font-size: 12px; color: #6B6E89 !important; font-weight: 500; white-space: nowrap; }
.synced-chip b { color: #22C55E !important; }
.btn-ghost-h { background: white; color: #14163A !important; padding: 8px 16px; border-radius: 10px; font-size: 13px; font-weight: 500; border: 1px solid #ECEAF5; display: inline-block; box-shadow: 0 1px 4px rgba(20,22,58,0.05); white-space: nowrap; }
.btn-primary-h { background: linear-gradient(135deg, #6B4EF5, #8B6CF8); color: white !important; padding: 8px 18px; border-radius: 10px; font-size: 13px; font-weight: 600; border: none; display: inline-block; box-shadow: 0 4px 14px rgba(107,78,245,0.38); white-space: nowrap; }

.pill { display: inline-block; padding: 3px 9px; border-radius: 20px; font-size: 11px; font-weight: 600; letter-spacing: 0.15px; line-height: 1.6; white-space: nowrap; }
.p-high   { background: #D1FAE5; color: #065F46; }
.p-maybe  { background: #FEF3C7; color: #92400E; }
.p-low    { background: #FEE2E2; color: #991B1B; }
.p-purple { background: #EFEBFE; color: #6B4EF5; }
.p-navy   { background: #EEF0FD; color: #14163A; }
.p-gray   { background: #F1F0F8; color: #6B6E89; }
.p-closed { background: #F3F4F6; color: #374151; }
.p-pink   { background: #FEE9F2; color: #9D2259; }

.r-card { background: white; border-radius: 16px; border: 1px solid #ECEAF5; box-shadow: 0 2px 18px rgba(20,22,58,0.05); padding: 20px; margin-bottom: 12px; }
.sec-hd { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.sec-title { font-size: 14px; font-weight: 700; color: #14163A; letter-spacing: -0.2px; }
.sec-sub   { font-size: 11px; color: #6B6E89; margin-top: 1px; }

.nav-card { background: white; border-radius: 12px; border: 1px solid #ECEAF5; padding: 12px 14px; margin-bottom: 8px; display: flex; align-items: center; gap: 12px; box-shadow: 0 1px 5px rgba(20,22,58,0.04); }
.nav-card.sel { background: linear-gradient(135deg, #6B4EF5, #8B6CF8); border-color: transparent; box-shadow: 0 5px 20px rgba(107,78,245,0.32); }
.nc-icon  { font-size: 19px; line-height: 1; }
.nc-title { font-size: 13px; font-weight: 600; color: #14163A; }
.nc-sub   { font-size: 11px; color: #6B6E89; margin-top: 1px; }
.nav-card.sel .nc-title { color: white !important; }
.nav-card.sel .nc-sub   { color: rgba(255,255,255,0.65) !important; }

/* Opportunity cards (fixed height so the transparent button overlays exactly) */
.opp-card { background: white; border-radius: 12px; border: 1px solid #ECEAF5; padding: 13px 16px; height: 92px; overflow: hidden; box-shadow: 0 1px 5px rgba(20,22,58,0.04); }
.opp-card.sel { background: linear-gradient(135deg, #6B4EF5, #8B6CF8); border-color: transparent; box-shadow: 0 6px 24px rgba(107,78,245,0.3); }
.oc-row   { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 5px; }
.oc-title { font-size: 13px; font-weight: 600; color: #14163A; line-height: 1.35; flex: 1; margin-right: 8px; }
.oc-inst  { font-size: 12px; color: #6B6E89; }
.oc-path  { font-size: 11px; color: #6B6E89; margin-top: 6px; }
.oc-arrow { color: #C4BAF8; }
.opp-card.sel .oc-title { color: white !important; }
.opp-card.sel .oc-inst  { color: rgba(255,255,255,0.7) !important; }
.opp-card.sel .oc-path  { color: rgba(255,255,255,0.6) !important; }
.opp-card.sel .oc-arrow { color: rgba(255,255,255,0.5); }
.opp-card.sel .pill     { background: rgba(255,255,255,0.22) !important; color: white !important; }

/* Opportunity cards rendered AS real Streamlit buttons (fully clickable) */
div.stButton > button {
    width: 100%;
    text-align: left;
    background: white;
    border: 1px solid #ECEAF5;
    border-radius: 12px;
    padding: 13px 16px;
    box-shadow: 0 1px 5px rgba(20,22,58,0.04);
    color: #14163A;
    line-height: 1.4;
    transition: border-color 0.12s ease, box-shadow 0.12s ease;
}
div.stButton > button:hover { border-color: #C4BAF8; color: #14163A; box-shadow: 0 2px 12px rgba(107,78,245,0.12); }
div.stButton > button:focus:not(:active) { color: #14163A; box-shadow: 0 2px 12px rgba(107,78,245,0.12); }
div.stButton > button > div { display: block; width: 100%; }
div.stButton > button p { margin: 0 0 4px 0; text-align: left; font-size: 12px; color: #6B6E89; }
div.stButton > button p:first-child { font-size: 13px; font-weight: 600; color: #14163A; line-height: 1.35; margin-bottom: 5px; }
div.stButton > button p:last-child { margin-bottom: 0; }
div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #6B4EF5, #8B6CF8); border-color: transparent; box-shadow: 0 6px 24px rgba(107,78,245,0.3); }
div.stButton > button[kind="primary"]:hover { border-color: transparent; box-shadow: 0 6px 24px rgba(107,78,245,0.4); }
div.stButton > button[kind="primary"] p,
div.stButton > button[kind="primary"] p:first-child { color: white !important; }
div.stButton > button[kind="primary"] p:nth-child(2),
div.stButton > button[kind="primary"] p:last-child { color: rgba(255,255,255,0.75) !important; }

.tl-item { display: flex; gap: 10px; align-items: flex-start; padding: 9px 0; border-bottom: 1px solid #F5F4FC; }
.tl-item:last-child { border-bottom: none; padding-bottom: 0; }
.tl-icon { font-size: 15px; line-height: 1; padding-top: 1px; flex-shrink: 0; }
.tl-text { font-size: 13px; font-weight: 500; color: #14163A; }
.tl-time { font-size: 11px; color: #6B6E89; margin-top: 2px; }

.metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
.m-tile { background: #F9F8FE; border-radius: 12px; border: 1px solid #ECEAF5; padding: 14px 16px; }
.m-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.7px; color: #6B6E89; font-weight: 600; }
.m-value { font-size: 24px; font-weight: 800; color: #14163A; margin: 4px 0 6px; letter-spacing: -0.6px; }
.m-value .unit { font-size: 14px; font-weight: 400; color: #6B6E89; }
.prog-bar  { height: 4px; background: #ECEAF5; border-radius: 99px; overflow: hidden; margin-top: 6px; }
.prog-fill { height: 100%; border-radius: 99px; background: linear-gradient(90deg, #6B4EF5, #8B6CF8); }

.alert-card { background: #FFF1F5; border: 1px solid #F9C6D8; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
.alert-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: #B04070 !important; margin-bottom: 8px; }
.alert-card ul { margin: 0; padding-left: 18px; }
.alert-card li { font-size: 13px; color: #14163A; line-height: 1.75; }

.action-card { background: white; border-radius: 12px; border: 1px solid #ECEAF5; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 6px rgba(20,22,58,0.04); }
.ac-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: #6B6E89; margin-bottom: 8px; }
.ac-body  { font-size: 13px; color: #14163A; line-height: 1.65; margin-bottom: 14px; }
.ac-btns  { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.btn-p { background: linear-gradient(135deg, #6B4EF5, #8B6CF8); color: white !important; padding: 7px 15px; border-radius: 9px; font-size: 12px; font-weight: 600; display: inline-block; box-shadow: 0 2px 10px rgba(107,78,245,0.3); white-space: nowrap; }
.btn-g { background: white; color: #14163A !important; padding: 6px 14px; border-radius: 9px; font-size: 12px; font-weight: 500; border: 1px solid #ECEAF5; display: inline-block; white-space: nowrap; }
.btn-q { background: transparent; color: #6B6E89 !important; padding: 6px 10px; border-radius: 9px; font-size: 12px; font-weight: 500; display: inline-block; white-space: nowrap; }

.review-card { background: #EFEBFE; border-radius: 12px; border: 1px solid #D9D3FB; padding: 16px; }
.rv-icon  { font-size: 18px; margin-bottom: 6px; }
.rv-title { font-size: 13px; font-weight: 700; color: #14163A; margin-bottom: 4px; }
.rv-body  { font-size: 12px; color: #6B6E89; line-height: 1.55; }

[data-testid="column"] { padding: 0 6px !important; }
[data-testid="column"]:first-child { padding-left: 0 !important; }
[data-testid="column"]:last-child  { padding-right: 0 !important; }

div[data-testid="stDownloadButton"] > button {
    background: white; color: #14163A !important; padding: 8px 16px;
    border-radius: 10px; font-size: 13px; font-weight: 500;
    border: 1px solid #ECEAF5; box-shadow: 0 1px 4px rgba(20,22,58,0.05);
    width: 100%;
}
div[data-testid="stDownloadButton"] > button:hover {
    border-color: #C4BAF8; box-shadow: 0 2px 12px rgba(107,78,245,0.12);
    color: #14163A !important;
}
</style>
""")


# ── TOPBAR ────────────────────────────────────────────────────────────────────
html("""
<div class="topbar">
    <span class="topbar-brand">risely</span>
    <nav class="topbar-nav">
        <span class="nav-link active">Monitor</span>
        <span class="nav-link">Pipeline</span>
        <span class="nav-link">Analytics</span>
        <span class="nav-link">Settings</span>
    </nav>
    <div class="topbar-actions">
        <span class="icon-btn">🔔</span>
        <span class="icon-btn">🔍</span>
        <span class="avatar">NR</span>
    </div>
</div>
""")


# ── PAGE HEADER ───────────────────────────────────────────────────────────────
n = len(rfps)
today_str = date.today().strftime("%B %d, %Y")
html(f"""
<div class="page-header">
    <div>
        <div class="page-title">RFP <span class="grad-text">Intelligence</span></div>
        <p class="page-subtitle">Monitoring {n} opportunities &nbsp;·&nbsp; Higher Education &nbsp;·&nbsp; Updated {today_str}</p>
    </div>
    <div class="header-actions">
        <div class="synced-chip"><b>●</b>&nbsp; Synced 2 min ago</div>
        <span class="btn-primary-h">+ New RFP</span>
    </div>
</div>
""")


# ── WEB SEARCH BAR ────────────────────────────────────────────────────────────
_has_tavily = bool(os.environ.get("TAVILY_API_KEY"))
_has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
_missing = [k for k, v in [("TAVILY_API_KEY", _has_tavily), ("ANTHROPIC_API_KEY", _has_anthropic)] if not v]

_sb, _ex, _st = st.columns([1, 1, 4])
with _sb:
    _search_disabled = bool(_missing)
    _search_clicked = st.button(
        "Search Web",
        disabled=_search_disabled,
        use_container_width=True,
        help="Search live procurement portals via Tavily and classify results with Claude",
    )
with _ex:
    st.download_button(
        "↓ Export CSV",
        data=generate_csv(rfps),
        file_name=f"risely-rfps-{date.today()}.csv",
        mime="text/csv",
        use_container_width=True,
    )
with _st:
    if _missing:
        st.caption(
            f"Set **{', '.join(_missing)}** to enable live search. "
            "Most RFP portals are paywalled — Tavily surfaces cached/indexed snippets "
            "so we can classify opportunities without a portal subscription."
        )
    else:
        web_n = len(load_saved_web_rfps())
        if web_n:
            st.caption(
                f"**{web_n}** opportunit{'y' if web_n == 1 else 'ies'} saved from web search · "
                "classified by Claude Haiku · "
                "many portals are paywalled, so Tavily's AI-extracted snippets are used in place of direct page access"
            )

if _search_clicked:
    with st.spinner("Searching procurement portals via Tavily…"):
        try:
            existing_titles = {r["title"] for r in rfps}
            new_rfps = load_rfps_from_web(existing_titles=existing_titles)
            for rfp in new_rfps:
                append_web_rfp(rfp)
            st.session_state.selected = 0
        except Exception as exc:
            st.error(f"Search failed: {exc}")
    st.rerun()

st.write("")

# ── MAIN COLUMNS ──────────────────────────────────────────────────────────────
left, mid, right = st.columns([1, 2, 2])


# ── LEFT: COMMAND CENTER ──────────────────────────────────────────────────────
with left:
    counts = {"High": 0, "Maybe": 0, "Low": 0}
    for r in rfps:
        counts[r["priority"]] += 1
    nav_items = [
        ("🎯", "RFP Monitor", f"{n} opportunities", True),
        ("📋", "Bid Pipeline", f"{counts['High']} high-priority", False),
        ("📊", "Analytics", "Win rate & trends", False),
        ("⚙️", "Settings", "Sources & alerts", False),
    ]
    nav_html = (
        '<div class="r-card">'
        '<div class="sec-hd"><div>'
        '<div class="sec-title">Command Center</div>'
        '<div class="sec-sub">Navigate your workspace</div>'
        '</div></div>'
    )
    for icon, title, sub, sel in nav_items:
        cls = "nav-card sel" if sel else "nav-card"
        nav_html += (
            f'<div class="{cls}"><span class="nc-icon">{icon}</span><div>'
            f'<div class="nc-title">{title}</div><div class="nc-sub">{sub}</div>'
            f'</div></div>'
        )
    nav_html += "</div>"
    html(nav_html)


# ── MIDDLE: OPPORTUNITIES (clickable) + ACTIVITY ─────────────────────────────
with mid:
    html(
        '<div class="list-head"><span class="sec-title">Opportunities</span>'
        f'<span class="pill p-purple">{n}</span></div>'
    )

    for i, rfp in enumerate(rfps):
        _, p_icon = PRIORITY_STYLE.get(rfp["priority"], ("p-gray", "•"))
        path = rfp["product_fit"]
        if rfp.get("secondary_fit"):
            path += f" → {rfp['secondary_fit']}"
        web_tag = "  · 🌐 Web" if rfp.get("source") == "Tavily Search" else ""
        label = (
            f"{rfp['title']}\n\n"
            f"{rfp['institution']}\n\n"
            f"{p_icon} {rfp['priority']}  ·  {path}{web_tag}"
        )
        btn_type = "primary" if i == st.session_state.selected else "secondary"
        if st.button(label, key=f"opp_{i}", type=btn_type, use_container_width=True):
            st.session_state.selected = i
            st.rerun()

    st.write("")

    # Live activity feed (derived from the loaded records)
    activity = []
    for rfp in rfps[:3]:
        activity.append(("🎯", f"Matched — {rfp['institution']}", f"score {rfp['score']}/100"))
    activity.append(("📄", "PDF ingested — WSU RFP #AI-DU122025", "earlier today"))
    act_html = (
        '<div class="r-card">'
        '<div class="sec-hd"><div class="sec-title">Live Activity</div>'
        '<span class="pill p-gray">Recent</span></div>'
    )
    for icon, text, time in activity:
        act_html += (
            f'<div class="tl-item"><span class="tl-icon">{icon}</span><div>'
            f'<div class="tl-text">{text}</div><div class="tl-time">{time}</div>'
            f'</div></div>'
        )
    act_html += "</div>"
    html(act_html)


# ── RIGHT: DETAIL PANEL (driven by selection) ────────────────────────────────
with right:
    rfp = rfps[st.session_state.selected]
    p_cls, p_icon = PRIORITY_STYLE.get(rfp["priority"], ("p-gray", "•"))
    s_cls, s_icon = STATUS_STYLE.get(rfp["date_status"], ("p-gray", "❓"))
    d_label = days_label(rfp)
    overdue = rfp["date_status"] == "Closed"
    days_pill_cls = "p-low" if overdue else "p-high"

    rfp_id = rfp.get("id", "").upper()
    fits = [rfp["product_fit"]] + ([rfp["secondary_fit"]] if rfp.get("secondary_fit") else [])

    pills = (
        f'<span class="pill {p_cls}">{p_icon} {rfp["priority"]} Priority</span>'
        f'<span class="pill {s_cls}">{s_icon} {rfp["date_status"]}</span>'
        f'<span class="pill p-purple">{rfp["product_fit"]}</span>'
    )
    if rfp.get("secondary_fit"):
        pills += f'<span class="pill p-navy">→ {rfp["secondary_fit"]}</span>'

    why = "".join(f"<li>{w}</li>" for w in rfp["why_it_matches"])
    review_body = "; ".join(rfp["risks"][:2]) if rfp.get("risks") else "Confirm fit before bidding."

    _source_label = rfp.get("source", "")
    _source_url = rfp.get("source_url", "")
    if _source_label and _source_url:
        _source_html = f'<a href="{_source_url}" target="_blank" style="font-size:11px;color:#6B4EF5;text-decoration:none;">🌐 {_source_label} ↗</a>'
    elif _source_label:
        _source_html = f'<span style="font-size:11px;color:#6B6E89;">{_source_label}</span>'
    else:
        _source_html = ""

    html(f"""
<div class="r-card">
<div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:14px;">
<div style="width:42px;height:42px;background:#EFEBFE;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:21px;flex-shrink:0;">🏛️</div>
<div>
<div style="font-size:15px;font-weight:700;color:#14163A;line-height:1.35;letter-spacing:-0.3px;">{rfp['title']}</div>
<div style="font-size:12px;color:#6B6E89;margin-top:3px;">{rfp['institution']}{(' · ' + rfp_id) if rfp_id else ''}</div>
{(f'<div style="margin-top:4px;">{_source_html}</div>') if _source_html else ''}
</div>
</div>
<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:18px;">
{pills}
</div>
<div class="metric-grid">
<div class="m-tile">
<div class="m-label">Score</div>
<div class="m-value">{rfp['score']}<span class="unit">/100</span></div>
<div class="prog-bar"><div class="prog-fill" style="width:{rfp['score']}%"></div></div>
</div>
<div class="m-tile">
<div class="m-label">Priority</div>
<div class="m-value" style="font-size:20px;padding-top:2px;">{rfp['priority']}</div>
<div style="margin-top:6px;"><span class="pill {p_cls}" style="font-size:10px;">{p_icon} {rfp['priority']}</span></div>
</div>
<div class="m-tile">
<div class="m-label">Due Date</div>
<div class="m-value" style="font-size:18px;padding-top:2px;">{pretty_date(rfp.get('due_date',''))}</div>
<div style="margin-top:6px;"><span class="pill {days_pill_cls}" style="font-size:10px;">{d_label}</span></div>
</div>
<div class="m-tile">
<div class="m-label">Product Fit</div>
<div class="m-value">{len(fits)}<span class="unit">/3</span></div>
<div style="margin-top:6px;"><span class="pill p-purple" style="font-size:10px;">{' + '.join(fits)}</span></div>
</div>
</div>
<div class="alert-card">
<div class="alert-label">⚡ Why this surfaced</div>
<ul>{why}</ul>
</div>
<div class="action-card">
<div class="ac-label">Recommended Next Step</div>
<div class="ac-body">{rfp['recommended_action']}</div>
<div class="ac-btns">
<span class="btn-p">✍️ Draft Bid</span>
<span class="btn-g">🔖 Save</span>
<span class="btn-q">Dismiss</span>
</div>
</div>
<div class="review-card">
<div class="rv-icon">👤</div>
<div class="rv-title">Human Review Needed</div>
<div class="rv-body">{review_body}</div>
</div>
</div>
""")
