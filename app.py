"""Streamlit web UI for Fuel Reimbursement Cycle Planner — Premium Dashboard."""

import io
import json
from datetime import date

import streamlit as st

from engine.models import CycleConfig, PlanResult
from engine.planner import plan_cycle_spend, plan_cycle_odometer
from export import export_excel, result_to_dict

# ── Emoji constants (avoids \U escapes inside f-strings for Python 3.9) ──────
E_CALENDAR = "\U0001F4C5"
E_ROAD = "\U0001F6E3\uFE0F"
E_BEACH = "\U0001F3D6\uFE0F"
E_RULER = "\U0001F4CF"
E_FUEL = "\u26FD"
E_MONEY = "\U0001F4B5"
E_CHECK = "\u2705"
E_MONEYBAG = "\U0001F4B0"
E_FLAG = "\U0001F3C1"
E_GEAR = "\u2699\uFE0F"
E_PACKAGE = "\U0001F4E6"
E_CHART = "\U0001F4CA"
E_SPEND = "\U0001F4B8"
E_CAR = "\U0001F697"
E_DICE = "\U0001F3B2"
E_ZAP = "\u26A1"
E_INBOX = "\U0001F4E5"
E_DOC = "\U0001F4C4"
E_RUPEE = "\u20B9"
E_DASH = "\u2014"

st.set_page_config(
    page_title="Fuel Reimbursement Cycle Planner",
    page_icon=E_FUEL,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg-primary: #0a0e1a;
    --bg-card: #111827;
    --bg-card-hover: #1a2332;
    --border-card: #1e293b;
    --accent-blue: #3b82f6;
    --accent-purple: #8b5cf6;
    --accent-teal: #14b8a6;
    --accent-gold: #f59e0b;
    --accent-green: #10b981;
    --accent-rose: #f43f5e;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --gradient-1: linear-gradient(135deg, #3b82f6, #8b5cf6);
    --gradient-2: linear-gradient(135deg, #14b8a6, #3b82f6);
    --gradient-3: linear-gradient(135deg, #f59e0b, #f43f5e);
    --gradient-gold: linear-gradient(135deg, #f59e0b, #d97706);
}

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
[data-testid="stAppViewContainer"] {
    background: var(--bg-primary) !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%) !important;
    border-right: 1px solid rgba(139, 92, 246, 0.2) !important;
}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] label {
    color: #94a3b8 !important;
    font-weight: 500 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.03em !important;
}
[data-testid="stSidebar"] .stRadio label { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stNumberInput input,
[data-testid="stSidebar"] .stDateInput input {
    background: rgba(15, 23, 42, 0.6) !important;
    border: 1px solid rgba(59, 130, 246, 0.3) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stNumberInput input:focus,
[data-testid="stSidebar"] .stDateInput input:focus {
    border-color: var(--accent-blue) !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
}
.sidebar-section {
    margin: 0.5rem 0 0.3rem 0;
    padding: 0.4rem 0.8rem;
    background: rgba(59, 130, 246, 0.08);
    border-left: 3px solid var(--accent-blue);
    border-radius: 0 8px 8px 0;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--accent-blue);
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--gradient-1) !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    letter-spacing: 0.03em !important;
    padding: 0.7rem 1.5rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(59, 130, 246, 0.45) !important;
}
.stDownloadButton > button {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-card) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    padding: 0.7rem 1.5rem !important;
    transition: all 0.3s ease !important;
}
.stDownloadButton > button:hover {
    border-color: var(--accent-blue) !important;
    background: var(--bg-card-hover) !important;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.15) !important;
    transform: translateY(-1px) !important;
}

/* Hero */
.hero-container { padding: 2rem 0 1rem 0; text-align: left; }
.hero-title {
    font-size: 2.4rem; font-weight: 800;
    background: linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 0.3rem; line-height: 1.15;
}
.hero-subtitle { font-size: 1rem; color: var(--text-secondary); font-weight: 400; margin-bottom: 0.3rem; }
.mode-badge {
    display: inline-block; padding: 0.25rem 0.9rem; border-radius: 20px;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.mode-spend { background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
.mode-odo { background: rgba(20,184,166,0.15); color: #5eead4; border: 1px solid rgba(20,184,166,0.3); }

/* Section headers */
.section-header { display: flex; align-items: center; gap: 0.6rem; margin: 2rem 0 1.2rem 0; }
.section-header .icon {
    width: 36px; height: 36px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center; font-size: 1.1rem;
}
.section-header .icon.blue { background: rgba(59,130,246,0.15); }
.section-header .icon.purple { background: rgba(139,92,246,0.15); }
.section-header .icon.gold { background: rgba(245,158,11,0.15); }
.section-header h2 { font-size: 1.4rem; font-weight: 700; color: var(--text-primary); margin: 0; }
.section-header .line { flex: 1; height: 1px; background: linear-gradient(90deg, var(--border-card), transparent); }

/* KPI Cards */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem; }
@media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
.kpi-card {
    background: var(--bg-card); border: 1px solid var(--border-card);
    border-radius: 16px; padding: 1.2rem 1.3rem;
    transition: all 0.3s ease; position: relative; overflow: hidden;
}
.kpi-card:hover {
    border-color: rgba(59,130,246,0.3); transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.3);
}
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0;
    height: 3px; border-radius: 16px 16px 0 0;
}
.kpi-card.blue::before { background: var(--gradient-1); }
.kpi-card.teal::before { background: var(--gradient-2); }
.kpi-card.gold::before { background: var(--gradient-3); }
.kpi-card.green::before { background: linear-gradient(135deg, #10b981, #14b8a6); }
.kpi-icon { font-size: 1.4rem; margin-bottom: 0.5rem; display: block; }
.kpi-label {
    font-size: 0.72rem; font-weight: 600; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.3rem;
}
.kpi-value { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); line-height: 1.2; }
.kpi-card.highlight {
    background: linear-gradient(135deg, rgba(59,130,246,0.08), rgba(139,92,246,0.08));
    border-color: rgba(139,92,246,0.25);
}
.kpi-card.highlight .kpi-value {
    background: var(--gradient-1);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.kpi-card.highlight-gold {
    background: linear-gradient(135deg, rgba(245,158,11,0.08), rgba(244,63,94,0.06));
    border-color: rgba(245,158,11,0.25);
}
.kpi-card.highlight-gold .kpi-value {
    background: var(--gradient-gold);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}

/* Styled Table */
.fuel-table-container {
    border-radius: 16px; overflow: hidden;
    border: 1px solid var(--border-card); background: var(--bg-card); margin-bottom: 1.5rem;
}
.fuel-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.fuel-table thead th {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    color: var(--text-secondary); font-weight: 600; font-size: 0.72rem;
    text-transform: uppercase; letter-spacing: 0.08em;
    padding: 1rem 1.2rem; text-align: right;
    border-bottom: 1px solid var(--border-card);
}
.fuel-table thead th:first-child { text-align: center; }
.fuel-table tbody td {
    padding: 0.85rem 1.2rem; color: var(--text-primary); text-align: right;
    border-bottom: 1px solid rgba(30,41,59,0.5); font-variant-numeric: tabular-nums;
}
.fuel-table tbody td:first-child { text-align: center; font-weight: 600; color: var(--accent-blue); }
.fuel-table tbody tr:nth-child(even) { background: rgba(15,23,42,0.3); }
.fuel-table tbody tr:hover { background: rgba(59,130,246,0.06); }
.fuel-table tbody tr.total-row {
    background: linear-gradient(135deg, rgba(59,130,246,0.1), rgba(139,92,246,0.08)) !important;
    border-top: 2px solid rgba(59,130,246,0.3);
}
.fuel-table tbody tr.total-row td {
    font-weight: 700; color: #e2e8f0;
    padding-top: 1rem; padding-bottom: 1rem; border-bottom: none;
}
.fuel-table tbody tr.total-row td:first-child {
    background: var(--gradient-1);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    font-size: 0.8rem; letter-spacing: 0.06em;
}
.discount-active { color: var(--accent-green) !important; font-weight: 600; }
.discount-none { color: var(--text-muted) !important; }
.refuel-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 8px;
    background: rgba(59,130,246,0.12); color: var(--accent-blue); font-weight: 700; font-size: 0.85rem;
}

/* Export */
.export-container {
    background: var(--bg-card); border: 1px solid var(--border-card);
    border-radius: 16px; padding: 1.5rem; margin-top: 0.5rem;
}

/* Empty state */
.empty-state { text-align: center; padding: 5rem 2rem; }
.empty-icon { font-size: 4rem; margin-bottom: 1rem; opacity: 0.6; }
.empty-title { font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.5rem; }
.empty-desc {
    font-size: 1rem; color: var(--text-secondary);
    max-width: 400px; margin: 0 auto 2rem auto; line-height: 1.6;
}
.empty-steps { display: inline-flex; gap: 2rem; margin-top: 1rem; }
.empty-step { display: flex; flex-direction: column; align-items: center; gap: 0.4rem; }
.step-num {
    width: 32px; height: 32px; border-radius: 50%;
    background: rgba(59,130,246,0.15); color: var(--accent-blue);
    font-weight: 700; font-size: 0.85rem;
    display: flex; align-items: center; justify-content: center;
}
.step-label { font-size: 0.78rem; color: var(--text-muted); font-weight: 500; }

[data-testid="stMetric"] { display: none !important; }

.styled-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-card), transparent);
    margin: 1.5rem 0;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:0.5rem 0 0.8rem 0;">'
        '<span style="font-size:2rem;">&#9981;</span><br>'
        '<span style="font-size:1.1rem;font-weight:700;color:#e2e8f0;">Fuel Planner</span>'
        '</div>', unsafe_allow_html=True)
    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    mode = st.radio("Planning Mode", ["Spend-Driven", "Odometer-Driven"], label_visibility="collapsed")

    st.markdown(
        '<div class="sidebar-section">' + E_GEAR + ' Cycle Settings</div>',
        unsafe_allow_html=True)
    cycle_start = st.date_input("Cycle Start Date (15th)", value=date(2026, 4, 15))
    start_odo = st.number_input("Start Odometer (km)", value=50000.0, step=100.0, format="%.1f")

    if mode == "Odometer-Driven":
        end_odo = st.number_input("End Odometer (km)", value=52700.0, step=100.0, format="%.1f")
    else:
        end_odo = None

    st.markdown(
        '<div class="sidebar-section">' + E_CAR + ' Vehicle</div>',
        unsafe_allow_html=True)
    daily_km = st.number_input("Daily Office Commute (km)", value=52.0, step=1.0, format="%.1f")
    mileage_input = st.number_input("Mileage (km/l)", value=14.0, step=0.5, format="%.1f")

    st.markdown(
        '<div class="sidebar-section">' + E_MONEYBAG + ' Fuel & Budget</div>',
        unsafe_allow_html=True)
    target_cap = st.number_input("Monthly Cap (INR)", value=19300.0, step=100.0, format="%.0f")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        price_min = st.number_input("Min Price", value=100.0, step=0.5, format="%.2f")
    with col_p2:
        price_max = st.number_input("Max Price", value=103.0, step=0.5, format="%.2f")

    st.markdown(
        '<div class="sidebar-section">' + E_DICE + ' Options</div>',
        unsafe_allow_html=True)
    seed = st.number_input("Random Seed (0 = random)", value=42, step=1)
    seed_val = seed if seed != 0 else None

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
    generate = st.button(E_ZAP + " Generate Plan", type="primary", use_container_width=True)


# ── Generate Logic ───────────────────────────────────────────────────────────
if generate:
    try:
        if cycle_start.day != 15:
            st.error("Cycle start date must be the 15th of a month.")
        else:
            cfg = CycleConfig(
                cycle_start=cycle_start,
                start_odometer=start_odo,
                daily_commute_km=daily_km,
                mileage_kmpl=mileage_input,
                target_cap=target_cap,
                price_min=price_min,
                price_max=price_max,
                seed=seed_val,
                end_odometer=end_odo,
            )
            if mode == "Spend-Driven":
                result = plan_cycle_spend(cfg)
            else:
                result = plan_cycle_odometer(cfg)
            st.session_state["result"] = result
            st.session_state["mode"] = mode
    except ValueError as e:
        st.error(f"Invalid input: {e}")


# ── Helper: KPI card HTML ────────────────────────────────────────────────────
def kpi_card(icon, label, value, css_class="blue"):
    return (
        '<div class="kpi-card ' + css_class + '">'
        '<span class="kpi-icon">' + icon + '</span>'
        '<div class="kpi-label">' + label + '</div>'
        '<div class="kpi-value">' + value + '</div>'
        '</div>'
    )


# ── Display ──────────────────────────────────────────────────────────────────
if "result" in st.session_state:
    result: PlanResult = st.session_state["result"]
    s = result.summary
    current_mode = st.session_state.get("mode", "Spend-Driven")
    badge_cls = "mode-spend" if current_mode == "Spend-Driven" else "mode-odo"
    badge_label = (E_SPEND + " Spend-Driven") if current_mode == "Spend-Driven" else (E_RULER + " Odometer-Driven")

    # Hero
    cycle_range = s.cycle_start.strftime('%B %d') + " " + E_DASH + " " + s.cycle_end.strftime('%B %d, %Y')
    st.markdown(
        '<div class="hero-container">'
        '<div class="hero-title">Fuel Reimbursement Cycle Planner</div>'
        '<div class="hero-subtitle">'
        + cycle_range +
        '&nbsp;&nbsp;<span class="mode-badge ' + badge_cls + '">' + badge_label + '</span>'
        '</div></div>',
        unsafe_allow_html=True)

    # Section: Cycle Summary
    st.markdown(
        '<div class="section-header">'
        '<div class="icon blue">' + E_CHART + '</div>'
        '<h2>Cycle Summary</h2>'
        '<div class="line"></div></div>',
        unsafe_allow_html=True)

    # KPI row 1
    savings = s.raw_fuel_cost - s.final_billed_total
    row1 = '<div class="kpi-grid">'
    row1 += kpi_card(E_CALENDAR, "Working Days", str(s.working_days), "blue")
    row1 += kpi_card(E_ROAD, "Office Commute", "{:,.2f} km".format(s.office_km), "teal")
    row1 += kpi_card(E_BEACH, "Extra Weekend KM", "{:,.2f} km".format(s.extra_weekend_km), "blue")
    row1 += kpi_card(E_RULER, "Total Distance", "{:,.2f} km".format(s.total_km), "teal")
    row1 += '</div>'
    st.markdown(row1, unsafe_allow_html=True)

    # KPI row 2
    row2 = '<div class="kpi-grid">'
    row2 += kpi_card(E_FUEL, "Fuel Used", "{:,.2f} L".format(s.fuel_used_litres), "blue")
    row2 += kpi_card(E_MONEY, "Raw Fuel Cost", E_RUPEE + " {:,.2f}".format(s.raw_fuel_cost), "highlight")
    row2 += kpi_card(E_CHECK, "Final Billed", E_RUPEE + " {:,.2f}".format(s.final_billed_total), "highlight-gold")
    row2 += kpi_card(E_MONEYBAG, "Discount Saved", E_RUPEE + " {:,.2f}".format(savings), "green")
    row2 += '</div>'
    st.markdown(row2, unsafe_allow_html=True)

    # KPI row 3
    row3 = '<div class="kpi-grid">'
    row3 += kpi_card(E_FLAG, "Start Odometer", "{:,.1f} km".format(s.start_odometer), "blue")
    row3 += kpi_card(E_FLAG, "End Odometer", "{:,.1f} km".format(s.end_odometer), "teal")
    row3 += kpi_card(E_GEAR, "Mileage", str(s.mileage_kmpl) + " km/l", "blue")
    row3 += kpi_card(E_PACKAGE, "Refuel Count", str(len(result.refuels)), "teal")
    row3 += '</div>'
    st.markdown(row3, unsafe_allow_html=True)

    # Section: Refuelling Breakdown
    st.markdown(
        '<div class="section-header">'
        '<div class="icon purple">' + E_FUEL + '</div>'
        '<h2>Refuelling Breakdown</h2>'
        '<div class="line"></div></div>',
        unsafe_allow_html=True)

    # Build table
    table_rows = ""
    for r in result.refuels:
        disc_cls = "discount-active" if r.discount > 0 else "discount-none"
        disc_val = E_RUPEE + " {:,.2f}".format(r.discount) if r.discount > 0 else E_DASH
        table_rows += (
            '<tr>'
            '<td><span class="refuel-badge">' + str(r.number) + '</span></td>'
            '<td>{:,.2f} L</td>'.format(r.litres) +
            '<td>' + E_RUPEE + ' {:,.2f}</td>'.format(r.price_per_litre) +
            '<td>' + E_RUPEE + ' {:,.2f}</td>'.format(r.amount) +
            '<td class="' + disc_cls + '">' + disc_val + '</td>'
            '<td>' + E_RUPEE + ' {:,.2f}</td>'.format(r.final_bill) +
            '</tr>'
        )

    total_disc = sum(r.discount for r in result.refuels)
    table_rows += (
        '<tr class="total-row">'
        '<td>TOTAL</td>'
        '<td>{:,.2f} L</td>'.format(result.total_litres) +
        '<td></td>'
        '<td>' + E_RUPEE + ' {:,.2f}</td>'.format(result.total_raw_cost) +
        '<td class="discount-active">' + E_RUPEE + ' {:,.2f}</td>'.format(total_disc) +
        '<td>' + E_RUPEE + ' {:,.2f}</td>'.format(result.total_final_billed) +
        '</tr>'
    )

    st.markdown(
        '<div class="fuel-table-container"><table class="fuel-table"><thead><tr>'
        '<th style="text-align:center">#</th><th>Volume</th><th>Price / L</th>'
        '<th>Amount</th><th>Discount</th><th>Final Bill</th>'
        '</tr></thead><tbody>' + table_rows + '</tbody></table></div>',
        unsafe_allow_html=True)

    # Section: Export
    st.markdown(
        '<div class="section-header">'
        '<div class="icon gold">' + E_INBOX + '</div>'
        '<h2>Export</h2>'
        '<div class="line"></div></div>',
        unsafe_allow_html=True)

    st.markdown('<div class="export-container">', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        json_str = json.dumps(result_to_dict(result), indent=2)
        st.download_button(
            label=E_DOC + " Download JSON",
            data=json_str,
            file_name="fuel_plan.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_b:
        buf = io.BytesIO()
        export_excel(result, buf)
        buf.seek(0)
        st.download_button(
            label=E_CHART + " Download Excel",
            data=buf,
            file_name="fuel_plan.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # ── Empty state ──
    st.markdown(
        '<div class="hero-container">'
        '<div class="hero-title">Fuel Reimbursement Cycle Planner</div>'
        '<div class="hero-subtitle">Plan your monthly fuel reimbursement cycle with precision</div>'
        '</div>',
        unsafe_allow_html=True)

    st.markdown(
        '<div class="empty-state">'
        '<div class="empty-icon">' + E_FUEL + '</div>'
        '<div class="empty-title">Ready to Plan Your Cycle</div>'
        '<div class="empty-desc">'
        'Configure your cycle parameters in the sidebar and hit '
        '<strong>Generate Plan</strong> to see your optimized refuelling breakdown.'
        '</div>'
        '<div class="empty-steps">'
        '<div class="empty-step"><div class="step-num">1</div><div class="step-label">Set dates</div></div>'
        '<div class="empty-step"><div class="step-num">2</div><div class="step-label">Enter vehicle info</div></div>'
        '<div class="empty-step"><div class="step-num">3</div><div class="step-label">Generate</div></div>'
        '</div></div>',
        unsafe_allow_html=True)
