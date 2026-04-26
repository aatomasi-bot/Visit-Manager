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
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0.5rem 1rem 5rem !important; max-width: 860px !important; }
.vm-logo { font-size: 22px; font-weight: 900; color: #0f172a; letter-spacing:-.5px; margin-bottom: 14px; }
.vm-logo b { color: #2563eb; }
.vm-card { background:#fff; border-radius:14px; border:1px solid #e2e8f0;
           box-shadow:0 1px 3px rgba(0,0,0,.06); padding:14px 16px 12px; margin-bottom:12px; }
.vm-card-blue   { border-left:4px solid #3b82f6; }
.vm-card-green  { border-left:4px solid #22c55e; }
.vm-card-red    { border-left:4px solid #ef4444; }
.vm-card-amber  { border-left:4px solid #f59e0b; }
.vm-card-gray   { border-left:4px solid #cbd5e1; opacity:.7; }
.vm-name  { font-size:18px; font-weight:700; color:#0f172a; margin-bottom:2px; }
.vm-meta  { font-size:12px; color:#94a3b8; font-family:monospace; margin-bottom:8px; }
.bdg { display:inline-block; font-size:11px; font-weight:700;
       padding:3px 9px; border-radius:20px; margin:2px 2px 2px 0; font-family:monospace; }
.bdg-blue   { background:#eff6ff; color:#1d4ed8; }
.bdg-green  { background:#f0fdf4; color:#15803d; }
.bdg-red    { background:#fef2f2; color:#b91c1c; }
.bdg-amber  { background:#fffbeb; color:#92400e; }
.bdg-purple { background:#f5f3ff; color:#5b21b6; }
.bdg-teal   { background:#f0fdfa; color:#0f766e; }
.vm-special { background:#fffbeb; border-left:4px solid #f59e0b;
              border-radius:0 8px 8px 0; padding:9px 13px;
              font-size:14px; font-weight:600; color:#92400e; margin:8px 0; line-height:1.5; }
.vm-adverse { background:#fef2f2; border-left:4px solid #ef4444;
              border-radius:0 8px 8px 0; padding:9px 13px;
              font-size:14px; color:#b91c1c; font-weight:500; margin-top:6px; }
.vm-next { display:inline-block; background:#eff6ff; color:#1d4ed8;
           border-radius:8px; padding:6px 12px; font-size:12px;
           font-family:monospace; margin-top:6px; }
.vm-grp { text-align:center; font-size:11px; font-weight:700; color:#94a3b8;
          text-transform:uppercase; letter-spacing:.8px;
          border-bottom:1px solid #e2e8f0; padding:12px 0 6px; margin:6px 0; }
.vm-empty { text-align:center; padding:50px 20px;
            font-size:15px; color:#94a3b8; font-weight:600; }
.stButton > button { border-radius:10px !important; font-weight:600 !important;
                     min-height:44px !important; font-size:14px !important; }
.stTextInput > div > div > input { font-size:16px !important;
    min-height:48px !important; border-radius:10px !important; }
.stSelectbox > div > div { border-radius:10px !important; }
.stTextArea textarea { font-size:15px !important; border-radius:10px !important; }
</style>
""", unsafe_allow_html=True)

MONTHS       = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"]
SITES        = ["Left Side","Right Side","Left Glute","Right Glute"]
ASSIGN_TYPES = ["Permanent","1 Dose Only"]
FILE_STATUSES= ["Active","Pending","Archived"]
DOSE_WEEKS   = {7.5:4, 22.5:12, 30:16, 45:24}
CSV_URL    = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQQidcM4dXyR4xXYhZQyTqC-_9LmZ5vMkRiV7oluY13fFGO8ySmpkjH1k8xqzzjhLc__yL5vMafIsb9/pub?output=csv"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwNMhrg7E7UCU-GYn3zeSw_kXAOi6OfdVf_JMPfTzXYm75BYp6HaZW6dPDRN0QdNqgh/exec"

# ── URLS ──
def get_urls():
    csv_url    = st.session_state.get("csv_url", CSV_URL)
    script_url = st.session_state.get("script_url", SCRIPT_URL)
    return csv_url, script_url


# ── DATA ──
@st.cache_data(ttl=20)
def load_patients(csv_url):
    if not csv_url:
        return []
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


def write_patient(p, script_url):
    if not script_url:
        st.error("No Apps Script URL. Go to Setup (sidebar).")
        return
    try:
        p["lastUpdated"] = datetime.now().isoformat()
        payload = json.dumps({"action":"upsert","patient":p})
        url = f"{script_url}?payload={quote(payload)}&t={int(datetime.now().timestamp())}"
        requests.get(url, allow_redirects=True, timeout=15)
    except requests.exceptions.Timeout:
        pass  # write likely went through
    except Exception:
        pass


def delete_remote(fn, script_url):
    if not script_url:
        return
    try:
        payload = json.dumps({"action":"delete","fileNumber":fn})
        url = f"{script_url}?payload={quote(payload)}&t={int(datetime.now().timestamp())}"
        requests.get(url, allow_redirects=True, timeout=15)
    except Exception:
        pass


# ── DATES ──
def parse_date(s):
    if not s or str(s).strip() in ("","nan","None","NaT"):
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d","%d %B %Y","%Y-%m-%dT%H:%M",
                "%Y-%m-%dT%H:%M:%S","%d/%m/%Y","%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
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


# ── TAB LOGIC ──
def get_tab(p):
    s = p.get("status","Active")
    if s == "Archived": return "archived"
    if s == "Pending":  return "pending"
    today = date.today()
    appt  = parse_date(p.get("apptDT",""))
    due   = parse_date(p.get("dueDate",""))
    if appt and appt < today:           return "overdue"
    if due  and due < today and not appt: return "overdue"
    if appt and appt == today:          return "today"
    if appt and appt > today:           return "scheduled"
    if due  and due >= today:           return "queue"
    return "scheduled"


def sort_pts(pts, tab):
    def key(p):
        appt = parse_date(p.get("apptDT",""))  or date(9999,12,31)
        due  = parse_date(p.get("dueDate","")) or date(9999,12,31)
        name = p.get("patientName","")
        if tab in ("today","scheduled"): return (appt, name)
        if tab == "overdue":
            a = parse_date(p.get("apptDT","")) or \
                parse_date(p.get("dueDate","")) or date(9999,12,31)
            return (a, name)
        if tab in ("queue","pending"): return (due, name)
        if tab == "archived":
            arc = parse_date(p.get("archivedDate","")) or date(1900,1,1)
            return (-arc.toordinal(), name)
        return (name,)
    return sorted(pts, key=key)


# ── RENDER CARD ──
def render_card(p, tab, idx, script_url, csv_url):
    fn    = p.get("fileNumber","")
    name  = p.get("patientName","")
    dose  = p.get("dose","")
    mg    = get_mg(dose)
    wk    = DOSE_WEEKS.get(mg)
    appt  = parse_date(p.get("apptDT",""))
    due   = parse_date(p.get("dueDate",""))
    today = date.today()

    color = ("red"   if tab == "overdue" else
             "green" if (tab=="today" and appt) else
             "amber" if tab == "pending" else
             "gray"  if tab == "archived" else "blue")

    bdg = ""
    if tab == "today" and appt:
        bdg += f'<span class="bdg bdg-green">&#10003; {fmt_dt(p.get("apptDT",""))}</span>'
    elif tab == "today":
        bdg += '<span class="bdg bdg-blue">Today</span>'
    if tab == "overdue":
        bdg += '<span class="bdg bdg-red">&#9888; Overdue</span>'
    if due:
        bdg += f'<span class="bdg bdg-purple">Due {fmt_date(due)}</span>'
    if p.get("assignType","") == "1 Dose Only":
        bdg += '<span class="bdg bdg-amber">1 Dose Only</span>'
    if p.get("repeatsLeft",""):
        bdg += f'<span class="bdg bdg-teal">{p["repeatsLeft"]} left</span>'
    if tab == "pending":
        bdg += '<span class="bdg bdg-amber">Pending</span>'

    spec_html = (f'<div class="vm-special">&#9888; {p["special"]}</div>'
                 if p.get("special","") else "")
    pend_html = (f'<div style="background:#fffbeb;border-radius:8px;padding:7px 12px;'
                 f'font-size:13px;color:#92400e;margin-top:6px;font-weight:500">'
                 f'Pending: {p["pendReason"]}</div>'
                 if p.get("pendReason","") else "")

    addr = p.get("address","")
    addr_html = ""
    if addr:
        mu = f"https://www.google.com/maps/dir/?api=1&destination={quote(addr)}"
        short = addr[:40] + ("..." if len(addr) > 40 else "")
        addr_html = (f'<a href="{mu}" target="_blank" style="display:inline-flex;'
                     f'align-items:center;gap:6px;background:#f0fdf4;color:#15803d;'
                     f'border:1.5px solid #bbf7d0;border-radius:10px;padding:9px 14px;'
                     f'font-size:14px;font-weight:600;text-decoration:none;margin:4px 4px 4px 0;">'
                     f'&#128205; {short}</a>')

    ph_html = ""
    for ph in [p.get("phone1",""), p.get("phone2","")]:
        if ph:
            ph_clean = re.sub(r"[^0-9+]","",ph)
            ph_html += (f'<a href="tel:{ph_clean}" style="display:inline-flex;'
                        f'align-items:center;gap:6px;background:#eff6ff;color:#1d4ed8;'
                        f'border:1.5px solid #bfdbfe;border-radius:10px;padding:9px 14px;'
                        f'font-size:15px;font-weight:600;text-decoration:none;'
                        f'font-family:monospace;margin:4px 4px 4px 0;">&#128222; {ph}</a>')

    next_html = ""
    if wk and tab != "archived":
        nd = add_weeks(appt or today, wk)
        next_html = f'<div class="vm-next">&#9200; After confirmation: {fmt_date(nd)} (+{wk}w)</div>'

    st.markdown(f"""
<div class="vm-card vm-card-{color}">
  <div class="vm-name">{name}</div>
  <div class="vm-meta">#{fn} &middot; {dose} &middot; {p.get("assignType","")}</div>
  <div>{bdg}</div>
  {spec_html}{pend_html}
  <div style="margin-top:8px">{addr_html}{ph_html}</div>
  {next_html}
</div>""", unsafe_allow_html=True)

    with st.expander(f"Details — {name}"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Total Doses:** {p.get('totalDoses','--')}")
            st.markdown(f"**Repeats Left:** {p.get('repeatsLeft','--')}")
            st.markdown(f"**Prev Site:** {p.get('prevSite','None')}")
            st.markdown(f"**Current Site:** {p.get('site','Not set')}")
        with c2:
            st.markdown(f"**Due Date:** {fmt_date(due) or '--'}")
            st.markdown(f"**Appointment:** {fmt_dt(p.get('apptDT','')) or '--'}")
            st.markdown(f"**Assignment:** {p.get('assignType','--')}")
            st.markdown(f"**Status:** {p.get('status','Active')}")

        if p.get("prevDates",""):
            st.caption(f"Prev dates: {p['prevDates']}")
        if p.get("adverse",""):
            st.markdown(f'<div class="vm-adverse">&#9888; {p["adverse"]}</div>',
                        unsafe_allow_html=True)
        if p.get("comments",""):
            st.info(f"💬 {p['comments']}")

        st.divider()
        st.markdown("**Injection Site**")
        sc = st.columns(4)
        for si, sl in enumerate(SITES):
            with sc[si]:
                t = "primary" if p.get("site","") == sl else "secondary"
                if st.button(sl, key=f"s_{fn}_{si}_{idx}", type=t):
                    p["site"] = sl
                    write_patient(p, script_url)
                    st.cache_data.clear()
                    st.rerun()

        st.divider()
        st.markdown("**Set Appointment**")
        a1, a2 = st.columns([2,1])
        with a1:
            ad = st.date_input("Date", value=appt or today, key=f"ad_{fn}_{idx}")
            at_val = "09:00"
            if p.get("apptDT","") and "T" in p["apptDT"]:
                at_val = p["apptDT"].split("T")[1][:5]
            at = st.time_input("Time",
                    value=datetime.strptime(at_val,"%H:%M").time(),
                    key=f"at_{fn}_{idx}")
        with a2:
            st.write("")
            if st.button("Confirm Appt", key=f"sa_{fn}_{idx}", type="primary"):
                p["apptDT"] = f"{ad}T{at.strftime('%H:%M')}"
                write_patient(p, script_url)
                st.cache_data.clear()
                st.success("Confirmed")
                st.rerun()
            if st.button("Clear Appt", key=f"ca_{fn}_{idx}"):
                p["apptDT"] = ""
                write_patient(p, script_url)
                st.cache_data.clear()
                st.rerun()

        st.markdown("**Due Date**")
        d1, d2 = st.columns([2,1])
        with d1:
            dd = st.date_input("Due", value=due or today, key=f"dd_{fn}_{idx}")
        with d2:
            st.write("")
            if st.button("Save Due", key=f"sd_{fn}_{idx}"):
                p["dueDate"] = str(dd)
                write_patient(p, script_url)
                st.cache_data.clear()
                st.success("Saved")
                st.rerun()

        st.divider()
        if tab != "archived":
            st.markdown("**Confirm Injection Administered**")
            ci = st.text_input("Type DONE to confirm",
                               key=f"ci_{fn}_{idx}", placeholder="DONE")
            if st.button("Confirm Injection", key=f"cib_{fn}_{idx}",
                         type="primary",
                         disabled=ci.strip().upper() != "DONE"):
                base = appt or today
                prev = [x.strip() for x in p.get("prevDates","").split(",") if x.strip()]
                prev.append(fmt_date(base))
                p["prevDates"] = ", ".join(prev)
                p["prevSite"]  = p.get("site","")
                p["site"]      = ""
                rl = int(p.get("repeatsLeft","0") or "0")
                if rl > 0: p["repeatsLeft"] = str(rl-1)
                if wk: p["dueDate"] = str(add_weeks(base, wk))
                p["apptDT"] = ""
                write_patient(p, script_url)
                st.cache_data.clear()
                nd_str = fmt_date(parse_date(p.get("dueDate","")))
                st.success(f"Confirmed. Next due: {nd_str}")
                if p.get("assignType","") == "1 Dose Only":
                    st.warning("1 Dose Only — confirm continuation")
                st.rerun()

            st.divider()
            if tab != "pending":
                with st.expander("Mark as Pending"):
                    pr = st.text_input("Reason", key=f"pr_{fn}_{idx}",
                                       placeholder="Travelling, refused...")
                    if st.button("Mark Pending", key=f"mp_{fn}_{idx}"):
                        p["pendReason"] = pr or "No reason given"
                        p["status"]     = "Pending"
                        p["apptDT"]     = ""
                        write_patient(p, script_url)
                        st.cache_data.clear()
                        st.rerun()
            else:
                if st.button("Remove from Pending", key=f"up_{fn}_{idx}", type="secondary"):
                    p["status"]     = "Active"
                    p["pendReason"] = ""
                    write_patient(p, script_url)
                    st.cache_data.clear()
                    st.rerun()

        st.divider()
        nc = st.text_area("Comments", value=p.get("comments",""), key=f"nc_{fn}_{idx}")
        if st.button("Save Comments", key=f"sc_{fn}_{idx}"):
            p["comments"] = nc
            write_patient(p, script_url)
            st.cache_data.clear()
            st.success("Saved")

        st.divider()
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Edit", key=f"ed_{fn}_{idx}"):
                st.session_state["editing"] = fn
                st.rerun()
        with b2:
            if tab != "archived":
                if st.button("Archive", key=f"ar_{fn}_{idx}"):
                    p["status"]       = "Archived"
                    p["archivedDate"] = str(today)
                    write_patient(p, script_url)
                    st.cache_data.clear()
                    st.rerun()
            else:
                if st.button("Reactivate", key=f"ra_{fn}_{idx}"):
                    p["status"]       = "Active"
                    p["archivedDate"] = ""
                    write_patient(p, script_url)
                    st.cache_data.clear()
                    st.rerun()
        with b3:
            if st.button("Delete", key=f"dl_{fn}_{idx}"):
                st.session_state[f"cdel_{fn}"] = True
                st.rerun()

        if st.session_state.get(f"cdel_{fn}"):
            st.error(f"Delete **{name}** permanently?")
            y, n = st.columns(2)
            with y:
                if st.button("Yes, delete", key=f"yd_{fn}_{idx}", type="primary"):
                    delete_remote(fn, script_url)
                    st.cache_data.clear()
                    st.session_state.pop(f"cdel_{fn}", None)
                    st.rerun()
            with n:
                if st.button("Cancel", key=f"nd_{fn}_{idx}"):
                    st.session_state.pop(f"cdel_{fn}", None)
                    st.rerun()


# ── FORM ──
def patient_form(existing, script_url):
    p      = existing or {}
    is_edit= existing is not None
    st.subheader("Edit Patient" if is_edit else "Add New Patient")

    c1, c2 = st.columns(2)
    with c1:
        fn   = st.text_input("File Number *", value=p.get("fileNumber",""), disabled=is_edit)
        name = st.text_input("Patient Name *", value=p.get("patientName",""))
        ph1  = st.text_input("Phone 1", value=p.get("phone1",""))
        ph2  = st.text_input("Phone 2", value=p.get("phone2",""))
        dose = st.text_input("Dose", value=p.get("dose",""), placeholder="45 mg x 6")
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
                               value=parse_date(p.get("apptDT","")) or None,
                               key="fa_d")
        appt_t = st.time_input("Appointment Time",
                               value=datetime.strptime("09:00","%H:%M").time(),
                               key="fa_t")
    with s2:
        due_d  = st.date_input("Due Date (optional)",
                               value=parse_date(p.get("dueDate","")) or None,
                               key="fd_d")

    sv, ca = st.columns(2)
    with sv:
        if st.button("Save Patient", type="primary", use_container_width=True):
            if not fn:   st.error("File number required"); return
            if not name: st.error("Patient name required"); return
            new_p = {c: p.get(c,"") for c in COLS}
            new_p.update({
                "fileNumber": fn,  "patientName": name,
                "address":    addr,"phone1":      ph1,
                "phone2":     ph2, "dose":        dose,
                "totalDoses": td,  "repeatsLeft": rl,
                "assignType": at,  "status":      fs,
                "special":    spec,"adverse":     adv,
                "comments":   com,
                "apptDT":  f"{appt_d}T{appt_t.strftime('%H:%M')}" if appt_d else "",
                "dueDate": str(due_d) if due_d else "",
            })
            write_patient(new_p, script_url)
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


# ── SETUP ──
def setup_page():
    st.subheader("Setup")
    st.markdown("""
### Step 1 — Publish your Google Sheet as CSV
1. Open your Google Sheet
2. Click **File → Share → Publish to web**
3. First dropdown: select **Sheet1** (or your sheet name)
4. Second dropdown: select **Comma-separated values (.csv)**
5. Click **Publish** → OK
6. Copy the URL it shows you
""")
    csv_url = st.text_input("Paste CSV URL here",
                            value=st.session_state.get("csv_url",""),
                            placeholder="https://docs.google.com/spreadsheets/d/.../pub?output=csv")

    st.markdown("### Step 2 — Apps Script URL")
    script_url = st.text_input("Paste your /exec URL here",
                               value=st.session_state.get("script_url",""),
                               placeholder="https://script.google.com/macros/s/.../exec")

    if st.button("Connect", type="primary", use_container_width=True):
        if not csv_url:
            st.error("CSV URL is required")
            return
        try:
            df = pd.read_csv(csv_url, dtype=str)
            st.session_state["csv_url"]    = csv_url
            st.session_state["script_url"] = script_url
            st.success(f"Connected! {len(df)} rows found in sheet.")
            st.rerun()
        except Exception as e:
            st.error(f"Cannot read sheet: {e}\n\nMake sure you published it as CSV.")


# ── MAIN ──
def main():
    st.markdown('<div class="vm-logo">Visit<b>.</b>Manager &#128137;</div>',
                unsafe_allow_html=True)

    if "csv_url" not in st.session_state:
        st.session_state["csv_url"]    = CSV_URL
    if "script_url" not in st.session_state:
        st.session_state["script_url"] = SCRIPT_URL

    csv_url, script_url = get_urls()

    if not csv_url:
        setup_page()
        return

    if st.session_state.get("adding"):
        patient_form(None, script_url)
        return

    if st.session_state.get("editing"):
        pts = load_patients(csv_url)
        rec = next((p for p in pts if p["fileNumber"]==st.session_state["editing"]), None)
        patient_form(rec, script_url)
        return

    # Top bar
    t1, t2, t3 = st.columns([3,1,1])
    with t1:
        search = st.text_input("", placeholder="Search name, file #, phone...",
                               label_visibility="collapsed")
    with t2:
        if st.button("Sync", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with t3:
        if st.button("+ Add", type="primary", use_container_width=True):
            st.session_state["adding"] = True
            st.rerun()

    pts = load_patients(csv_url)
    if not pts:
        st.warning("No patients loaded. Check your sheet is published and has data.")
        return

    if search:
        q = search.lower()
        pts = [p for p in pts if any(
            q in p.get(f,"").lower()
            for f in ["patientName","fileNumber","phone1","phone2","address"])]

    buckets = {t:[] for t in ["today","scheduled","overdue","queue","pending","archived"]}
    for p in pts:
        buckets[get_tab(p)].append(p)

    labels = [
        f"Today ({len(buckets['today'])})",
        f"Scheduled ({len(buckets['scheduled'])})",
        f"Overdue ({len(buckets['overdue'])})",
        f"All Patients ({len(buckets['queue'])})",
        f"Pending ({len(buckets['pending'])})",
        f"Archived ({len(buckets['archived'])})",
    ]
    keys = ["today","scheduled","overdue","queue","pending","archived"]
    tabs = st.tabs(labels)

    for ti, (tab_obj, tk) in enumerate(zip(tabs, keys)):
        with tab_obj:
            tab_pts = sort_pts(buckets[tk], tk)
            if tk == "today":
                for p in tab_pts:
                    if p.get("assignType","") == "1 Dose Only":
                        st.warning(f"⚠ {p['patientName']} is 1 Dose Only")

            if not tab_pts:
                icons = {"today":"📅","scheduled":"🗓","overdue":"⚠️",
                         "queue":"👥","pending":"⏸","archived":"🗄"}
                msgs  = {"today":"No visits today","scheduled":"No appointments",
                         "overdue":"No overdue","queue":"No patients",
                         "pending":"No pending","archived":"No archived"}
                st.markdown(
                    f'<div class="vm-empty">{icons.get(tk,"📋")}<br>'
                    f'{msgs.get(tk,"Nothing here")}</div>',
                    unsafe_allow_html=True)
                continue

            if tk == "queue":
                last_g = None
                for idx, p in enumerate(tab_pts):
                    g = fmt_date(parse_date(p.get("dueDate",""))) or "No Due Date"
                    if g != last_g:
                        st.markdown(f'<div class="vm-grp">{g}</div>', unsafe_allow_html=True)
                        last_g = g
                    render_card(p, tk, f"{ti}_{idx}", script_url, csv_url)
            else:
                for idx, p in enumerate(tab_pts):
                    render_card(p, tk, f"{ti}_{idx}", script_url, csv_url)

    with st.sidebar:
        st.markdown("### Settings")
        if st.button("Change Setup"):
            st.session_state.pop("csv_url", None)
            st.rerun()

if __name__ == "__main__":
    main()
