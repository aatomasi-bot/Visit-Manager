import streamlit as st
import pandas as pd
import requests
import json
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote

st.set_page_config(
    page_title="Visit Manager",
    page_icon="💉",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── APP SHELL ── */
.vm-app {
    background: #f8fafc;
    min-height: 100vh;
    font-family: 'Inter', sans-serif;
}

/* ── TOPBAR ── */
.vm-topbar {
    background: #fff;
    border-bottom: 1px solid #e2e8f0;
    padding: 0 20px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.vm-brand {
    font-size: 20px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -.5px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.vm-brand-dot { color: #2563eb; }
.vm-brand-icon {
    width: 32px; height: 32px;
    background: linear-gradient(135deg,#1d4ed8,#3b82f6);
    border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
}

/* ── SEARCH BAR ── */
.vm-searchbar {
    background: #fff;
    border-bottom: 1px solid #e2e8f0;
    padding: 10px 20px;
}

/* ── CONTENT ── */
.vm-content {
    padding: 12px 16px 80px;
    max-width: 860px;
    margin: 0 auto;
}

/* ── CARD ── */
.vm-card {
    background: #ffffff;
    border-radius: 16px;
    border: 1px solid #e8edf2;
    box-shadow: 0 1px 4px rgba(0,0,0,.05), 0 2px 8px rgba(0,0,0,.03);
    margin-bottom: 10px;
    overflow: hidden;
    transition: box-shadow .2s;
}
.vm-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.09); }
.vm-card-blue   { border-left: 4px solid #3b82f6; }
.vm-card-green  { border-left: 4px solid #22c55e; }
.vm-card-red    { border-left: 4px solid #ef4444; }
.vm-card-amber  { border-left: 4px solid #f59e0b; }
.vm-card-gray   { border-left: 4px solid #cbd5e1; opacity: .7; }

.vm-card-top { padding: 14px 16px 10px; }
.vm-card-name {
    font-size: 17px; font-weight: 700; color: #0f172a;
    line-height: 1.3; margin-bottom: 3px;
}
.vm-card-meta {
    font-size: 12px; color: #94a3b8;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    margin-bottom: 8px;
}

/* ── BADGES ── */
.bdg {
    display: inline-block; font-size: 11px; font-weight: 700;
    padding: 3px 9px; border-radius: 20px;
    margin: 2px 3px 2px 0;
    font-family: 'JetBrains Mono','Courier New',monospace;
    white-space: nowrap;
}
.bdg-blue   { background: #eff6ff; color: #1d4ed8; }
.bdg-green  { background: #f0fdf4; color: #15803d; }
.bdg-red    { background: #fef2f2; color: #b91c1c; }
.bdg-amber  { background: #fffbeb; color: #92400e; }
.bdg-purple { background: #f5f3ff; color: #5b21b6; }
.bdg-teal   { background: #f0fdfa; color: #0f766e; }
.bdg-gray   { background: #f1f5f9; color: #475569; }

/* ── SPECIAL / WARNINGS ── */
.vm-special {
    background: #fffbeb; border-left: 4px solid #f59e0b;
    border-radius: 0 10px 10px 0; padding: 10px 14px;
    font-size: 13px; font-weight: 600; color: #92400e;
    margin: 8px 16px; line-height: 1.5;
    display: flex; align-items: flex-start; gap: 8px;
}
.vm-pend-reason {
    background: #fffbeb; border-radius: 8px;
    padding: 7px 12px; font-size: 12px; color: #92400e;
    margin: 4px 16px; font-weight: 500;
}
.vm-adverse {
    background: #fef2f2; border-left: 4px solid #ef4444;
    border-radius: 0 8px 8px 0; padding: 10px 14px;
    font-size: 13px; color: #b91c1c; font-weight: 500;
    margin-top: 8px; line-height: 1.5;
}

/* ── QUICK ACTIONS (address + phone) ── */
.vm-quick { padding: 6px 16px 12px; display: flex; flex-wrap: wrap; gap: 7px; }
.vm-addr-btn {
    display: inline-flex; align-items: center; gap: 6px;
    background: #f0fdf4; color: #15803d;
    border: 1.5px solid #bbf7d0; border-radius: 10px;
    padding: 8px 14px; font-size: 13px; font-weight: 600;
    text-decoration: none; max-width: 100%; overflow: hidden;
}
.vm-addr-btn span { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:220px; }
.vm-phone-btn {
    display: inline-flex; align-items: center; gap: 6px;
    background: #eff6ff; color: #1d4ed8;
    border: 1.5px solid #bfdbfe; border-radius: 10px;
    padding: 8px 14px; font-size: 14px; font-weight: 600;
    text-decoration: none; white-space: nowrap;
    font-family: 'JetBrains Mono','Courier New',monospace;
}

/* ── EXPAND TOGGLE ── */
.vm-expand-btn {
    display: flex; align-items: center; justify-content: center;
    gap: 5px; padding: 9px; border-top: 1px solid #f1f5f9;
    font-size: 12px; font-weight: 600; color: #94a3b8;
    cursor: pointer; user-select: none;
    background: transparent;
    transition: background .15s;
}

/* ── DETAIL PANEL ── */
.vm-detail { background: #f8fafc; border-top: 1px solid #f1f5f9; }
.vm-det-sec { padding: 16px 18px; border-bottom: 1px solid #f1f5f9; }
.vm-det-sec:last-child { border-bottom: none; }
.vm-det-title {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #94a3b8; margin-bottom: 12px;
    font-family: 'JetBrains Mono','Courier New',monospace;
}
.vm-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.vm-field { display: flex; flex-direction: column; gap: 3px; }
.vm-fld-lbl {
    font-size: 10px; font-weight: 600; color: #94a3b8;
    text-transform: uppercase; letter-spacing: .5px;
}
.vm-fld-val {
    font-size: 14px; font-weight: 500; color: #1e293b; line-height: 1.4;
}
.vm-fld-mono { font-family: 'JetBrains Mono','Courier New',monospace; font-size: 13px; }
.vm-next-due {
    display: inline-flex; align-items: center; gap: 6px;
    background: #eff6ff; color: #1d4ed8; border-radius: 8px;
    padding: 6px 12px; font-size: 12px;
    font-family: 'JetBrains Mono','Courier New',monospace; margin-top: 10px;
}

/* ── CONFIRM BOX ── */
.vm-confirm-box {
    background: #f0fdf4; border: 1.5px solid #bbf7d0;
    border-radius: 12px; padding: 14px;
}
.vm-confirm-label {
    font-size: 13px; color: #374151; margin-bottom: 10px; line-height: 1.5;
}
.vm-confirm-label strong { color: #15803d; }

/* ── DATE DIVIDER ── */
.vm-date-div {
    display: flex; align-items: center; gap: 12px;
    padding: 14px 0 6px; font-size: 11px; font-weight: 700;
    color: #94a3b8; text-transform: uppercase; letter-spacing: .8px;
}
.vm-date-div-line { flex: 1; height: 1px; background: #e2e8f0; }

/* ── EMPTY STATE ── */
.vm-empty {
    text-align: center; padding: 56px 20px;
    font-size: 15px; color: #94a3b8; font-weight: 600;
}
.vm-empty-icon { font-size: 44px; margin-bottom: 12px; }

/* ── SITE BUTTONS ── */
.site-sel-L { background:#eff6ff !important; color:#1d4ed8 !important; border-color:#93c5fd !important; }
.site-sel-R { background:#fffbeb !important; color:#92400e !important; border-color:#fcd34d !important; }
.site-sel-G { background:#f0fdf4 !important; color:#15803d !important; border-color:#86efac !important; }

/* ── STREAMLIT OVERRIDES ── */
div[data-testid="stTabs"] { margin-top: 0; }
div[data-testid="stTabs"] > div:first-child {
    background: #fff;
    border-bottom: 1px solid #e2e8f0;
    padding: 0 16px;
    position: sticky;
    top: 56px;
    z-index: 90;
}
button[data-baseweb="tab"] {
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 14px 14px 12px !important;
    color: #94a3b8 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #2563eb !important;
}
div[data-baseweb="tab-highlight"] { background: #2563eb !important; }
div[data-baseweb="tab-border"] { background: #e2e8f0 !important; }

.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    min-height: 42px !important;
    border: none !important;
    transition: all .15s !important;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,.12) !important; }
.stTextInput > div > div > input {
    font-size: 15px !important; min-height: 46px !important;
    border-radius: 10px !important; border: 1.5px solid #e2e8f0 !important;
}
.stTextInput > div > div > input:focus { border-color: #2563eb !important; }
.stDateInput > div > div > input {
    font-size: 15px !important; min-height: 46px !important;
    border-radius: 10px !important;
}
.stTimeInput > div > div > input { font-size: 15px !important; border-radius: 10px !important; }
.stSelectbox > div > div { border-radius: 10px !important; border: 1.5px solid #e2e8f0 !important; }
.stTextArea > div > div > textarea {
    font-size: 14px !important; border-radius: 10px !important;
    border: 1.5px solid #e2e8f0 !important; line-height: 1.6 !important;
}
div[data-testid="stExpander"] { display: none !important; }
.stAlert { border-radius: 10px !important; }
div[data-testid="column"] { gap: 6px; }

@media (max-width: 600px) {
    .vm-content { padding: 10px 12px 80px; }
    .vm-grid-2 { grid-template-columns: 1fr; }
    .vm-card-name { font-size: 16px; }
}
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ──
MONTHS       = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"]
SITES        = ["Left Side","Right Side","Left Glute","Right Glute"]
ASSIGN_TYPES = ["Permanent","1 Dose Only"]
FILE_STATUSES= ["Active","Pending","Archived"]
DOSE_WEEKS   = {7.5:4, 22.5:12, 30:16, 45:24}
COLS = ["fileNumber","patientName","address","phone1","phone2",
        "dose","totalDoses","repeatsLeft","prevSite","site",
        "dueDate","apptDT","prevDates","assignType","special",
        "adverse","comments","status","pendReason","archivedDate","lastUpdated"]
CSV_URL    = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQQidcM4dXyR4xXYhZQyTqC-_9LmZ5vMkRiV7oluY13fFGO8ySmpkjH1k8xqzzjhLc__yL5vMafIsb9/pub?output=csv"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwNMhrg7E7UCU-GYn3zeSw_kXAOi6OfdVf_JMPfTzXYm75BYp6HaZW6dPDRN0QdNqgh/exec"

# ── DATA ──
@st.cache_data(ttl=30)
def load_patients(csv_url):
    try:
        df = pd.read_csv(csv_url, dtype=str).fillna("")
        result = []
        for _, row in df.iterrows():
            p = {}
            for c in COLS:
                val = ""
                for col in df.columns:
                    if col.strip() == c:
                        val = str(row[col]).strip()
                        break
                p[c] = val
            if p.get("fileNumber","").strip():
                result.append(p)
        return result
    except Exception as e:
        st.error(f"Cannot read sheet: {e}")
        return []

def write_patient(p, script_url=SCRIPT_URL):
    try:
        p["lastUpdated"] = datetime.now().isoformat()
        payload = json.dumps({"action":"upsert","patient":p})
        url = f"{script_url}?payload={quote(payload)}&t={int(datetime.now().timestamp())}"
        requests.get(url, allow_redirects=True, timeout=15)
    except Exception:
        pass

def delete_remote(fn, script_url=SCRIPT_URL):
    try:
        payload = json.dumps({"action":"delete","fileNumber":fn})
        url = f"{script_url}?payload={quote(payload)}&t={int(datetime.now().timestamp())}"
        requests.get(url, allow_redirects=True, timeout=15)
    except Exception:
        pass

# ── DATE UTILS ──
def parse_date(s):
    if not s or str(s).strip() in ("","nan","None","NaT"): return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d","%d %B %Y","%Y-%m-%dT%H:%M","%Y-%m-%dT%H:%M:%S","%d/%m/%Y","%m/%d/%Y"):
        try: return datetime.strptime(s, fmt).date()
        except: pass
    return None

def fmt_date(d):
    if d is None: return ""
    if isinstance(d, str): d = parse_date(d)
    if d is None: return ""
    return f"{d.day} {MONTHS[d.month-1]} {d.year}"

def fmt_dt(s):
    d = parse_date(s)
    return fmt_date(d) if d else (s or "")

def add_weeks(d, w):
    return d + timedelta(weeks=w) if d else None

def get_mg(dose_str):
    m = re.search(r"(\d+(?:\.\d+)?)\s*mg", str(dose_str), re.I)
    return float(m.group(1)) if m else 0.0

def esc(s):
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

# ── TAB LOGIC ──
def get_tab(p):
    s = p.get("status","Active")
    if s == "Archived": return "archived"
    if s == "Pending":  return "pending"
    today = date.today()
    appt  = parse_date(p.get("apptDT",""))
    due   = parse_date(p.get("dueDate",""))
    if appt and appt < today:             return "overdue"
    if due  and due < today and not appt: return "overdue"
    if appt and appt == today:            return "today"
    if appt and appt > today:             return "scheduled"
    if due  and due >= today:             return "queue"
    return "scheduled"

def sort_pts(pts, tab):
    def key(p):
        appt = parse_date(p.get("apptDT",""))  or date(9999,12,31)
        due  = parse_date(p.get("dueDate","")) or date(9999,12,31)
        name = p.get("patientName","")
        if tab in ("today","scheduled"): return (appt, name)
        if tab == "overdue":
            a = parse_date(p.get("apptDT","")) or parse_date(p.get("dueDate","")) or date(9999,12,31)
            return (a, name)
        if tab in ("queue","pending"): return (due, name)
        if tab == "archived":
            arc = parse_date(p.get("archivedDate","")) or date(1900,1,1)
            return (-arc.toordinal(), name)
        return (name,)
    return sorted(pts, key=key)

# ── SESSION HELPERS ──
def toggle_card(fn):
    key = f"open_{fn}"
    st.session_state[key] = not st.session_state.get(key, False)

def is_open(fn):
    return st.session_state.get(f"open_{fn}", False)

# ── RENDER CARD ──
def render_card(p, tab, idx):
    fn    = p.get("fileNumber","")
    name  = p.get("patientName","")
    dose  = p.get("dose","")
    mg    = get_mg(dose)
    wk    = DOSE_WEEKS.get(mg)
    appt  = parse_date(p.get("apptDT",""))
    due   = parse_date(p.get("dueDate",""))
    today = date.today()
    open_ = is_open(fn)

    color = ("red"   if tab=="overdue" else
             "green" if (tab=="today" and appt) else
             "amber" if tab=="pending" else
             "gray"  if tab=="archived" else "blue")

    # Badges
    bdg = ""
    if tab == "today" and appt:
        bdg += f'<span class="bdg bdg-green">&#10003; {esc(fmt_dt(p.get("apptDT","")))}</span>'
    elif tab == "today":
        bdg += '<span class="bdg bdg-blue">Today</span>'
    if tab == "overdue":
        bdg += '<span class="bdg bdg-red">&#9888; Overdue</span>'
    if due:
        bdg += f'<span class="bdg bdg-purple">Due {esc(fmt_date(due))}</span>'
    if p.get("assignType","") == "1 Dose Only":
        bdg += '<span class="bdg bdg-amber">1 Dose Only</span>'
    if p.get("repeatsLeft",""):
        bdg += f'<span class="bdg bdg-teal">{esc(p["repeatsLeft"])} left</span>'
    if tab == "pending":
        bdg += '<span class="bdg bdg-amber">Pending</span>'

    # Next due preview
    next_html = ""
    if wk and tab != "archived":
        base = appt or today
        nd   = add_weeks(base, wk)
        next_html = f'<div class="vm-next-due">&#9200; After confirmation: {esc(fmt_date(nd))} (+{wk}w)</div>'

    # Special instructions
    spec_html = ""
    if p.get("special",""):
        spec_html = f'<div class="vm-special"><span>&#9888;</span>{esc(p["special"])}</div>'

    # Pending reason
    pend_html = ""
    if p.get("pendReason",""):
        pend_html = f'<div class="vm-pend-reason">Pending: {esc(p["pendReason"])}</div>'

    # Address + phones
    addr = p.get("address","")
    addr_html = ""
    if addr:
        mu = f"https://www.google.com/maps/dir/?api=1&destination={quote(addr)}"
        short = addr[:38] + ("..." if len(addr) > 38 else "")
        addr_html = f'<a href="{mu}" target="_blank" class="vm-addr-btn">&#128205;<span>{esc(short)}</span></a>'

    ph_html = ""
    for ph in [p.get("phone1",""), p.get("phone2","")]:
        if ph:
            ph_clean = re.sub(r"[^0-9+]","",ph)
            ph_html += f'<a href="tel:{ph_clean}" class="vm-phone-btn">&#128222; {esc(ph)}</a>'

    expand_icon = "&#9650;" if open_ else "&#9660;"
    expand_txt  = "Hide details" if open_ else "Show details"

    # Card HTML
    st.markdown(f"""
<div class="vm-card vm-card-{color}" id="card-{fn}">
  <div class="vm-card-top">
    <div class="vm-card-name">{esc(name)}</div>
    <div class="vm-card-meta">#{esc(fn)} &middot; {esc(dose)} &middot; {esc(p.get("assignType",""))}</div>
    <div style="margin-bottom:4px">{bdg}</div>
  </div>
  {spec_html}{pend_html}
  <div class="vm-quick">{addr_html}{ph_html}</div>
  {next_html if not open_ else ""}
</div>
""", unsafe_allow_html=True)

    # Toggle button
    if st.button(f"{expand_txt} {expand_icon}", key=f"tog_{fn}_{idx}",
                 use_container_width=True):
        toggle_card(fn)
        st.rerun()

    # Expanded details
    if open_:
        render_detail(p, tab, idx, appt, due, wk, today, next_html)

def render_detail(p, tab, idx, appt, due, wk, today, next_html):
    fn = p.get("fileNumber","")

    # Info grid
    st.markdown(f"""
<div style="background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;padding:16px;margin-bottom:8px">
  <div class="vm-det-title">Dosing &amp; Schedule</div>
  <div class="vm-grid-2">
    <div class="vm-field"><div class="vm-fld-lbl">Dose</div><div class="vm-fld-val vm-fld-mono">{esc(p.get("dose","--"))}</div></div>
    <div class="vm-field"><div class="vm-fld-lbl">Assignment</div><div class="vm-fld-val">{esc(p.get("assignType","--"))}</div></div>
    <div class="vm-field"><div class="vm-fld-lbl">Total Doses</div><div class="vm-fld-val vm-fld-mono">{esc(p.get("totalDoses","--"))}</div></div>
    <div class="vm-field"><div class="vm-fld-lbl">Repeats Left</div><div class="vm-fld-val vm-fld-mono">{esc(p.get("repeatsLeft","--"))}</div></div>
    <div class="vm-field"><div class="vm-fld-lbl">Due Date</div><div class="vm-fld-val vm-fld-mono">{esc(fmt_date(due) or "--")}</div></div>
    <div class="vm-field"><div class="vm-fld-lbl">Appointment</div><div class="vm-fld-val vm-fld-mono">{esc(fmt_dt(p.get("apptDT","")) or "--")}</div></div>
    <div class="vm-field"><div class="vm-fld-lbl">Prev Site</div><div class="vm-fld-val">{esc(p.get("prevSite","None"))}</div></div>
    <div class="vm-field"><div class="vm-fld-lbl">Current Site</div><div class="vm-fld-val">{esc(p.get("site","Not set"))}</div></div>
  </div>
  {next_html}
</div>
""", unsafe_allow_html=True)

    if p.get("prevDates",""):
        st.markdown(f'<div style="font-size:12px;color:#94a3b8;padding:0 2px 8px;font-family:monospace">Prev dates: {esc(p["prevDates"])}</div>', unsafe_allow_html=True)

    if p.get("adverse",""):
        st.markdown(f'<div class="vm-adverse">&#9888; Adverse: {esc(p["adverse"])}</div>', unsafe_allow_html=True)

    if p.get("comments",""):
        st.info(f"💬 {p['comments']}")

    # INJECTION SITE
    st.markdown('<div class="vm-det-title" style="margin-top:12px">Injection Site</div>', unsafe_allow_html=True)
    site_cols = st.columns(4)
    site_cls  = {"Left Side":"L","Right Side":"R","Left Glute":"G","Right Glute":"G"}
    for si, sl in enumerate(SITES):
        with site_cols[si]:
            is_sel = p.get("site","") == sl
            cls    = f"site-sel-{site_cls[sl]}" if is_sel else ""
            if st.button(sl, key=f"site_{fn}_{si}_{idx}",
                         type="primary" if is_sel else "secondary"):
                p["site"] = sl
                write_patient(p)
                st.cache_data.clear()
                st.rerun()

    st.divider()

    # APPOINTMENT
    st.markdown('<div class="vm-det-title">Schedule Appointment</div>', unsafe_allow_html=True)
    a1, a2, a3 = st.columns([2,1,1])
    with a1:
        appt_d = st.date_input("Date", value=appt or today, key=f"ad_{fn}_{idx}", label_visibility="collapsed")
    with a2:
        at_str = "09:00"
        if p.get("apptDT","") and "T" in p["apptDT"]:
            at_str = p["apptDT"].split("T")[1][:5]
        appt_t = st.time_input("Time", value=datetime.strptime(at_str,"%H:%M").time(),
                               key=f"at_{fn}_{idx}", label_visibility="collapsed")
    with a3:
        if st.button("Confirm", key=f"sa_{fn}_{idx}", type="primary"):
            p["apptDT"] = f"{appt_d}T{appt_t.strftime('%H:%M')}"
            write_patient(p)
            st.cache_data.clear()
            st.success("Appointment confirmed")
            st.rerun()

    b1, b2 = st.columns(2)
    with b1:
        due_in = st.date_input("Due Date", value=due or today, key=f"dd_{fn}_{idx}", label_visibility="collapsed")
    with b2:
        if st.button("Save Due Date", key=f"sd_{fn}_{idx}"):
            p["dueDate"] = str(due_in)
            write_patient(p)
            st.cache_data.clear()
            st.success("Due date saved")
            st.rerun()

    if appt:
        if st.button("Clear Appointment", key=f"ca_{fn}_{idx}"):
            p["apptDT"] = ""
            write_patient(p)
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # CONFIRM INJECTION
    if tab != "archived":
        st.markdown('<div class="vm-det-title">Confirm Injection</div>', unsafe_allow_html=True)
        st.markdown('<div class="vm-confirm-box"><div class="vm-confirm-label">Type <strong>DONE</strong> to unlock confirmation</div></div>', unsafe_allow_html=True)
        ci = st.text_input("", key=f"ci_{fn}_{idx}", placeholder="Type DONE here...",
                           label_visibility="collapsed")
        if st.button("✓ Confirm Injection Administered", key=f"cib_{fn}_{idx}",
                     type="primary", use_container_width=True,
                     disabled=ci.strip().upper() != "DONE"):
            base = appt or today
            prev = [x.strip() for x in p.get("prevDates","").split(",") if x.strip()]
            prev.append(fmt_date(base))
            p["prevDates"] = ", ".join(prev)
            p["prevSite"]  = p.get("site","")
            p["site"]      = ""
            rl = int(p.get("repeatsLeft","0") or "0")
            if rl > 0: p["repeatsLeft"] = str(rl-1)
            mg = get_mg(p.get("dose",""))
            wk2 = DOSE_WEEKS.get(mg)
            if wk2: p["dueDate"] = str(add_weeks(base, wk2))
            p["apptDT"] = ""
            write_patient(p)
            st.cache_data.clear()
            nd_str = fmt_date(parse_date(p.get("dueDate","")))
            st.success(f"Confirmed. Next due: {nd_str}")
            if p.get("assignType","") == "1 Dose Only":
                st.warning("1 Dose Only — confirm continuation with patient")
            st.rerun()

        st.divider()

        # PENDING
        if tab != "pending":
            st.markdown('<div class="vm-det-title">Mark as Pending</div>', unsafe_allow_html=True)
            pr = st.text_input("Reason", key=f"pr_{fn}_{idx}",
                               placeholder="e.g. travelling, refused, hospitalised...")
            if st.button("Mark as Pending", key=f"mp_{fn}_{idx}"):
                p["pendReason"] = pr or "No reason given"
                p["status"]     = "Pending"
                p["apptDT"]     = ""
                write_patient(p)
                st.cache_data.clear()
                st.rerun()
        else:
            if st.button("Remove from Pending", key=f"up_{fn}_{idx}", type="secondary",
                         use_container_width=True):
                p["status"]     = "Active"
                p["pendReason"] = ""
                write_patient(p)
                st.cache_data.clear()
                st.rerun()

    # COMMENTS
    st.divider()
    st.markdown('<div class="vm-det-title">Comments</div>', unsafe_allow_html=True)
    nc = st.text_area("", value=p.get("comments",""), key=f"nc_{fn}_{idx}",
                      placeholder="Add notes...", label_visibility="collapsed")
    if st.button("Save Comments", key=f"sc_{fn}_{idx}"):
        p["comments"] = nc
        write_patient(p)
        st.cache_data.clear()
        st.success("Saved")

    # ACTIONS
    st.divider()
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        if st.button("Edit", key=f"ed_{fn}_{idx}", use_container_width=True):
            st.session_state["editing"] = fn
            st.rerun()
    with b2:
        if tab != "archived":
            if st.button("Archive", key=f"ar_{fn}_{idx}", use_container_width=True):
                p["status"]       = "Archived"
                p["archivedDate"] = str(today)
                write_patient(p)
                st.cache_data.clear()
                st.rerun()
        else:
            if st.button("Reactivate", key=f"ra_{fn}_{idx}", use_container_width=True):
                p["status"]       = "Active"
                p["archivedDate"] = ""
                write_patient(p)
                st.cache_data.clear()
                st.rerun()
    with b3:
        if st.button("Delete", key=f"dl_{fn}_{idx}", use_container_width=True):
            st.session_state[f"cdel_{fn}"] = True
            st.rerun()
    with b4:
        if st.button("Close", key=f"cl_{fn}_{idx}", use_container_width=True):
            st.session_state[f"open_{fn}"] = False
            st.rerun()

    if st.session_state.get(f"cdel_{fn}"):
        name_val = p.get("patientName","")
        st.error(f"Delete **{name_val}** permanently? This cannot be undone.")
        y, n = st.columns(2)
        with y:
            if st.button("Yes, delete", key=f"yd_{fn}_{idx}", type="primary", use_container_width=True):
                delete_remote(fn)
                st.cache_data.clear()
                st.session_state.pop(f"cdel_{fn}", None)
                st.session_state.pop(f"open_{fn}", None)
                st.rerun()
        with n:
            if st.button("Cancel", key=f"nd_{fn}_{idx}", use_container_width=True):
                st.session_state.pop(f"cdel_{fn}", None)
                st.rerun()

# ── PATIENT FORM ──
def patient_form(existing=None):
    p       = existing or {}
    is_edit = existing is not None
    st.markdown(f'<div style="font-size:20px;font-weight:800;color:#0f172a;margin-bottom:20px">{"Edit Patient" if is_edit else "Add New Patient"}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        fn   = st.text_input("File Number *", value=p.get("fileNumber",""), disabled=is_edit)
        name = st.text_input("Patient Name *", value=p.get("patientName",""))
        ph1  = st.text_input("Phone 1", value=p.get("phone1",""))
        ph2  = st.text_input("Phone 2", value=p.get("phone2",""))
        dose = st.text_input("Dose", value=p.get("dose",""), placeholder="e.g. 45 mg x 6")
    with c2:
        addr = st.text_input("Address", value=p.get("address",""))
        td   = st.text_input("Total Doses", value=p.get("totalDoses",""))
        rl   = st.text_input("Repeats Left", value=p.get("repeatsLeft",""))
        at   = st.selectbox("Assignment Type", ASSIGN_TYPES,
               index=ASSIGN_TYPES.index(p.get("assignType","Permanent"))
                     if p.get("assignType") in ASSIGN_TYPES else 0)
        fs   = st.selectbox("File Status", FILE_STATUSES,
               index=FILE_STATUSES.index(p.get("status","Active"))
                     if p.get("status") in FILE_STATUSES else 0)

    spec = st.text_area("Special Instructions", value=p.get("special",""))
    adv  = st.text_area("Adverse Effects",      value=p.get("adverse",""))
    com  = st.text_area("Comments",             value=p.get("comments",""))

    s1, s2 = st.columns(2)
    with s1:
        appt_d = st.date_input("Appointment Date (optional)",
                               value=parse_date(p.get("apptDT","")) or None, key="fa_d")
        appt_t = st.time_input("Appointment Time",
                               value=datetime.strptime("09:00","%H:%M").time(), key="fa_t")
    with s2:
        due_d = st.date_input("Due Date (optional)",
                              value=parse_date(p.get("dueDate","")) or None, key="fd_d")

    sv, ca = st.columns(2)
    with sv:
        if st.button("Save Patient", type="primary", use_container_width=True):
            if not fn:   st.error("File number is required"); return
            if not name: st.error("Patient name is required"); return
            new_p = {c: p.get(c,"") for c in COLS}
            new_p.update({
                "fileNumber": fn,   "patientName": name,
                "address":    addr, "phone1":      ph1,
                "phone2":     ph2,  "dose":        dose,
                "totalDoses": td,   "repeatsLeft": rl,
                "assignType": at,   "status":      fs,
                "special":    spec, "adverse":     adv,
                "comments":   com,
                "apptDT":  f"{appt_d}T{appt_t.strftime('%H:%M')}" if appt_d else "",
                "dueDate": str(due_d) if due_d else "",
            })
            write_patient(new_p)
            st.cache_data.clear()
            st.session_state.pop("editing", None)
            st.session_state.pop("adding",  None)
            st.success(f"Saved {name}")
            st.rerun()
    with ca:
        if st.button("Cancel", use_container_width=True):
            st.session_state.pop("editing", None)
            st.session_state.pop("adding",  None)
            st.rerun()

# ── MAIN ──
def main():
    # Header
    st.markdown("""
<div class="vm-topbar">
  <div class="vm-brand">
    <div class="vm-brand-icon">💉</div>
    <span>Visit<span class="vm-brand-dot">.</span>Manager</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # Load data
    pts = load_patients(CSV_URL)

    # Show form if editing/adding
    if st.session_state.get("adding"):
        with st.container():
            st.markdown('<div class="vm-content">', unsafe_allow_html=True)
            patient_form(None)
            st.markdown('</div>', unsafe_allow_html=True)
        return

    if st.session_state.get("editing"):
        fn  = st.session_state["editing"]
        rec = next((p for p in pts if p["fileNumber"]==fn), None)
        with st.container():
            st.markdown('<div class="vm-content">', unsafe_allow_html=True)
            patient_form(rec)
            st.markdown('</div>', unsafe_allow_html=True)
        return

    # Search + action bar
    st.markdown('<div class="vm-content">', unsafe_allow_html=True)
    r1, r2, r3 = st.columns([4,1,1])
    with r1:
        search = st.text_input("", placeholder="🔍 Search name, file #, phone...",
                               label_visibility="collapsed")
    with r2:
        if st.button("🔄 Sync", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with r3:
        if st.button("＋ Add", type="primary", use_container_width=True):
            st.session_state["adding"] = True
            st.rerun()

    # Filter
    if search:
        q = search.lower()
        pts = [p for p in pts if any(
            q in p.get(f,"").lower()
            for f in ["patientName","fileNumber","phone1","phone2","address"])]

    # Bucket into tabs
    buckets = {t:[] for t in ["today","scheduled","overdue","queue","pending","archived"]}
    for p in pts:
        buckets[get_tab(p)].append(p)

    TCFG = [
        ("today",     f"Today ({len(buckets['today'])})"),
        ("scheduled", f"Scheduled ({len(buckets['scheduled'])})"),
        ("overdue",   f"Overdue ({len(buckets['overdue'])})"),
        ("queue",     f"All Patients ({len(buckets['queue'])})"),
        ("pending",   f"Pending ({len(buckets['pending'])})"),
        ("archived",  f"Archived ({len(buckets['archived'])})"),
    ]

    tabs = st.tabs([t[1] for t in TCFG])

    for ti, (tab_obj, (tk, _)) in enumerate(zip(tabs, TCFG)):
        with tab_obj:
            tab_pts = sort_pts(buckets[tk], tk)

            # 1-dose banners
            if tk == "today":
                for p in tab_pts:
                    if p.get("assignType","") == "1 Dose Only":
                        st.warning(f"⚠ {p['patientName']} is 1 Dose Only — confirm continuation after visit.")

            if not tab_pts:
                icons = {"today":"📅","scheduled":"🗓","overdue":"⚠️",
                         "queue":"👥","pending":"⏸","archived":"🗄"}
                msgs  = {"today":"No visits today","scheduled":"No scheduled appointments",
                         "overdue":"No overdue patients","queue":"No patients found",
                         "pending":"No pending patients","archived":"No archived records"}
                st.markdown(
                    f'<div class="vm-empty"><div class="vm-empty-icon">{icons.get(tk,"📋")}</div>'
                    f'{msgs.get(tk,"Nothing here")}</div>',
                    unsafe_allow_html=True)
                continue

            # Date grouping for All Patients
            if tk == "queue":
                last_g = None
                for idx, p in enumerate(tab_pts):
                    g = fmt_date(parse_date(p.get("dueDate",""))) or "No Due Date"
                    if g != last_g:
                        st.markdown(
                            f'<div class="vm-date-div">'
                            f'<div class="vm-date-div-line"></div>'
                            f'<span>{g}</span>'
                            f'<div class="vm-date-div-line"></div></div>',
                            unsafe_allow_html=True)
                        last_g = g
                    render_card(p, tk, f"{ti}_{idx}")
            else:
                for idx, p in enumerate(tab_pts):
                    render_card(p, tk, f"{ti}_{idx}")

    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
