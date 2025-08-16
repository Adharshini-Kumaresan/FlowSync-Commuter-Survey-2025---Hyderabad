# FlowSync — Investor-Grade Interactive Dashboard
# Run: streamlit run FlowDash.py
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st
from PIL import Image

# -------------------------
# Page setup & theme
# -------------------------
st.set_page_config(
    page_title="FlowSync — Smarter Commutes, Faster Roads",
    layout="wide",
    page_icon="🛣️",
    initial_sidebar_state="expanded",
)

PRIMARY = "#0E7C86"   # teal
SECONDARY = "#072540" # deep navy
ACCENT = "#21C4CC"    # bright aqua

st.markdown(
    f"""
    <style>
      :root {{
        --primary: {PRIMARY};
        --secondary: {SECONDARY};
        --accent: {ACCENT};
      }}
      .title {{
        font-size: 34px; font-weight: 800; color: var(--secondary); margin-bottom: 0;
      }}
      .subtitle {{
        color: #6b7280; margin-top: 6px; margin-bottom: 14px;
      }}
      .kpi {{
        background: linear-gradient(90deg, var(--primary), var(--secondary));
        color: white; padding: 14px 18px; border-radius: 14px; text-align: left;
        box-shadow: 0 6px 18px rgba(0,0,0,0.08);
      }}
      .kpi h2 {{ margin: 0; font-size: 28px; }}
      .kpi small {{ opacity: 0.9; }}
      .card {{
        background: #fff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 16px 18px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.04);
      }}
      .pill {{
        display:inline-block; background: #eef; color: var(--secondary); 
        padding: 4px 10px; border-radius: 999px; font-size: 12px; margin-right: 6px;
      }}
      .cta {{
        background: var(--primary); color: white; padding: 10px 14px; border-radius: 8px; 
        text-decoration: none; font-weight: 600;
      }}
      [data-testid="stMetricDelta"] svg {{ display:none; }}
      .footer-note {{ color:#6b7280; font-size: 12px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Strict CSV loader
# -------------------------
def load_csv_required(path):
    if not os.path.exists(path):
        st.error(f"❌ Required CSV not found: {path}")
        st.stop()
    return pd.read_csv(path)

# -------------------------
# Load required datasets
# -------------------------
traffic = load_csv_required("flowsync_hitec_traffic_timeseries.csv")
companies = load_csv_required("flowsync_hitec_companies_sample.csv")
survey = load_csv_required("flowsync_commuter_survey.csv")

# Optional dataset
emissions = None
emissions_path = "flowsync_emissions_econ_estimates.csv"
if os.path.exists(emissions_path):
    emissions = pd.read_csv(emissions_path)

# -------------------------
# Hotspots
# -------------------------
def hotspot_df():
    return pd.DataFrame({
        "name": [
            "HITEC City MMTS Underpass",
            "Gachibowli Flyover / Cyber Towers",
            "Mindspace–Yashoda Road",
            "Cyber Towers – Mindspace Rotary",
            "U-turn Bottleneck (Dairy Farm)"
        ],
        "lat": [17.4425, 17.4379, 17.4436, 17.4446, 17.4800],
        "lon": [78.3828, 78.3678, 78.3795, 78.3803, 78.4480]
    })
hotspots = hotspot_df()

# -------------------------
# Header
# -------------------------
logo = None
for candidate in [
    "FlowSync Logo with Green-Blue Gradient.png",
    "FlowSync Logo with Teal and Navy Color Scheme.png"
]:
    logo_path = os.path.join(r"d:\DataViz\FlowSync-Dash", candidate)
    if os.path.exists(logo_path):
        logo = logo_path
        break

c1, c2 = st.columns([0.12, 0.88])
with c1:
    if logo:
        st.image(Image.open(logo), use_column_width=True)
with c2:
    st.markdown('<div class="title">FlowSync — Smarter Commutes, Faster Roads</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Interactive pilot dashboard for HITEC City: traffic, companies, commuters, and impact simulation.</div>', unsafe_allow_html=True)

# -------------------------
# Sidebar Filters
# -------------------------
st.sidebar.header("Data Inputs & Filters")

time_window = st.sidebar.selectbox(
    "Traffic window",
    ["Full day", "Morning peak (08:00–11:00)", "Evening peak (16:00–20:00)"],
    index=2,
)
top_n = st.sidebar.slider("Top N companies (by employees)", 5, 25, 12)
reduction_pct = st.sidebar.slider("Assumed total km reduction with FlowSync (%)", 10, 60, 35)
avg_time_saved_min = st.sidebar.slider("Avg. time saved per commuter (mins)", 5, 60, 15)
value_per_hour = st.sidebar.number_input("Value of productive hour (INR)", value=500, step=50)

# -------------------------
# KPI Row
# -------------------------
c1, c2, c3, c4 = st.columns(4)
with c1:
    peak_ev = int(traffic.iloc[10:14]["vehicles_per_hour"].max())
    st.markdown(f'<div class="kpi"><small>Peak vehicles / hr (Evening)</small><h2>{peak_ev:,}</h2></div>', unsafe_allow_html=True)
with c2:
    avg_comm = round(traffic["commute_time_min_for_10km"].mean(), 1)
    st.markdown(f'<div class="kpi"><small>Avg commute (10 km)</small><h2>{avg_comm} mins</h2></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="kpi"><small>Companies (sample)</small><h2>{len(companies)}</h2></div>', unsafe_allow_html=True)
with c4:
    pct_willing = round((survey["willing_to_shift"].astype(str) == "Yes").mean()*100, 1)
    st.markdown(f'<div class="kpi"><small>Willing to shift</small><h2>{pct_willing}%</h2></div>', unsafe_allow_html=True)

# (Your tab sections for Traffic Trends, Company Profiles, etc. remain unchanged)

# -------------------------
# Tabs
# -------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Traffic Trends", "Company Profiles", "Commuter Sentiment",
    "Emissions & ROI", "Pilot Simulator", "Hotspot Map"
])
# Paste the rest of your visualization and interaction code here
# ---- Tab 1: Traffic Trends ----
with tab1:
    st.markdown("### Traffic Trends — Volume, Speed & Delay")

    if time_window == "Morning peak (08:00–11:00)":
        vis = traffic.iloc[2:5].copy()
    elif time_window == "Evening peak (16:00–20:00)":
        vis = traffic.iloc[10:14].copy()
    else:
        vis = traffic.copy()

    # Dual-axis: vehicles + commute time
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=vis["time"], y=vis["vehicles_per_hour"], name="Vehicles / hr", opacity=0.75
    ))
    fig.add_trace(go.Scatter(
        x=vis["time"], y=vis["commute_time_min_for_10km"],
        mode="lines+markers", name="Commute time (min, 10 km)", yaxis="y2"
    ))
    fig.update_layout(
        height=420,
        xaxis_title="Time of day",
        yaxis=dict(title="Vehicles / hr"),
        yaxis2=dict(title="Commute time (min)", overlaying="y", side="right"),
        legend=dict(orientation="h"),
        hovermode="x unified",
        margin=dict(l=20,r=20,t=40,b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Congestion heatmap
    heat = traffic.copy()
    heat["hour"] = pd.to_datetime(heat["time"], format="%H:%M").dt.hour
    heat["day"] = "Weekday"
    pivot = heat.pivot_table(index="day", columns="hour", values="congestion_index_0_100", aggfunc="mean")
    fig_h = px.imshow(
        pivot.values,
        labels=dict(x="Hour", y="Day", color="Congestion Index"),
        x=pivot.columns, y=pivot.index, aspect="auto", text_auto=False
    )
    fig_h.update_layout(height=300, margin=dict(l=20,r=20,t=20,b=20))
    st.plotly_chart(fig_h, use_container_width=True)

    st.download_button("Download Traffic CSV", data=traffic.to_csv(index=False), file_name="flowsync_hitec_traffic_timeseries.csv")

# ---- Tab 2: Company Profiles ----
with tab2:
    st.markdown("### Company Commute Profiles")
    # Filters + table
    colL, colR = st.columns([0.6, 0.4])
    with colL:
        top_companies = companies.sort_values("estimated_employees_in_hyderabad", ascending=False).head(top_n)
        fig2 = px.bar(
            top_companies,
            x="company_name", y="estimated_employees_in_hyderabad",
            title=f"Top {top_n} Companies by Estimated Employees",
            labels={"company_name":"Company", "estimated_employees_in_hyderabad":"Employees"}
        )
        fig2.update_layout(xaxis_tickangle=-45, height=420, margin=dict(l=20,r=20,t=40,b=20))
        st.plotly_chart(fig2, use_container_width=True)

    with colR:
        st.markdown("#### Drilldown")
        pick = st.selectbox("Select a company", top_companies["company_name"].tolist())
        emp = int(top_companies.loc[top_companies["company_name"] == pick, "estimated_employees_in_hyderabad"].values[0])
        st.markdown(f"**Estimated Employees:** {emp:,}")
        # Simple impact estimate for this company
        distance_km = 10
        base_km = emp * distance_km
        co2_tonnes = round(base_km * 0.2 / 1000, 2)
        co2_tonnes_after = round(base_km * 0.2 * (1 - reduction_pct/100) / 1000, 2)
        st.markdown(f"- **Baseline CO₂/day:** {co2_tonnes} t\n- **After FlowSync:** {co2_tonnes_after} t")
        st.progress(min(1.0, reduction_pct/60))

    st.dataframe(top_companies, use_container_width=True)
    st.download_button("Download Companies CSV", data=companies.to_csv(index=False), file_name="flowsync_hitec_companies_sample.csv")

# ---- Tab 3: Commuter Sentiment ----
with tab3:
    st.markdown("### Commuter Sentiment & Willingness")
    colA, colB, colC = st.columns([0.4, 0.35, 0.25])

    with colA:
        willing_counts = survey["willing_to_shift"].value_counts().reset_index()
        willing_counts.columns = ["response","count"]
        fig3 = px.pie(willing_counts, values="count", names="response", title="Willing to shift departure time")
        st.plotly_chart(fig3, use_container_width=True)

    with colB:
        slot_pref = survey["preferred_departure_slot_evening"].value_counts().reset_index()
        slot_pref.columns = ["slot", "count"]
        fig4 = px.bar(slot_pref.sort_values("slot"), x="slot", y="count", title="Preferred evening departure slots")
        fig4.update_layout(xaxis_tickangle=-30)
        st.plotly_chart(fig4, use_container_width=True)

    with colC:
        inc = survey["incentive_preference"].value_counts().reset_index()
        inc.columns = ["incentive","count"]
        fig5 = px.bar(inc, x="incentive", y="count", title="Incentive preference")
        st.plotly_chart(fig5, use_container_width=True)

    st.dataframe(survey.sample(min(30, len(survey))), use_container_width=True)
    st.download_button("Download Survey CSV", data=survey.to_csv(index=False), file_name="flowsync_commuter_survey.csv")

# ---- Tab 4: Emissions & ROI ----
with tab4:
    st.markdown("### Emissions & Economic Impact (What-If)")
    total_commuters = int(companies["estimated_employees_in_hyderabad"].sum())
    distance_km = 10
    baseline_km = total_commuters * distance_km
    baseline_co2_tonnes = round(baseline_km * 0.2 / 1000, 2)

    after_km = int(baseline_km * (1 - reduction_pct/100))
    after_co2_tonnes = round(after_km * 0.2 / 1000, 2)

    avg_time_saved_hrs = avg_time_saved_min / 60.0
    weekly_value_saved = int(total_commuters * avg_time_saved_hrs * value_per_hour * 5)  # 5 working days

    c1, c2, c3 = st.columns(3)
    c1.metric("Baseline CO₂ (t/day)", baseline_co2_tonnes)
    c2.metric("After FlowSync CO₂ (t/day)", after_co2_tonnes, delta=f"-{baseline_co2_tonnes - after_co2_tonnes}")
    c3.metric("Weekly productivity saved (₹)", f"{weekly_value_saved:,}")

    # Waterfall chart for ROI narratives (Productivity + Fuel + Others)
    prod = weekly_value_saved
    fuel_saved = int((baseline_km - after_km) * 8)  # rough ₹8/km
    other = int(prod * 0.15)
    total = prod + fuel_saved + other

    wf = pd.DataFrame({
        "Item":["Start","Productivity","Fuel","Other","Total"],
        "Value":[0, prod, fuel_saved, other, total]
    })
    base = 0
    measures = []
    for i, row in wf.iterrows():
        if row["Item"] in ["Start","Total"]: measures.append("total")
        else: measures.append("relative")

    fig_wf = go.Figure(go.Waterfall(
        name="ROI", orientation="v",
        measure=measures,
        x=wf["Item"], textposition="outside",
        y=wf["Value"], connector={"line":{"width":1}}
    ))
    fig_wf.update_layout(title="Weekly Economic Impact (Illustrative)", height=420, margin=dict(l=20,r=20,t=40,b=20))
    st.plotly_chart(fig_wf, use_container_width=True)

# ---- Tab 5: Pilot Simulator ----
with tab5:
    st.markdown("### Pilot Simulator — Before / After")
    st.markdown(
        "<span class='pill'>Goal</span> Spread departures so no more than 2 companies share the same 15-min slot.",
        unsafe_allow_html=True
    )

    # Pick subset for simulation
    sim_companies = companies.sort_values("estimated_employees_in_hyderabad", ascending=False).head(top_n).copy()
    sim_companies["baseline_departure"] = "18:00"
    # Assign staggered slots (15-min intervals from 17:00–20:00)
    slots = pd.date_range("17:00", "20:00", freq="15min").strftime("%H:%M").tolist()
    sim_companies["staggered_slot"] = [slots[i % len(slots)] for i in range(len(sim_companies))]

    # Compute load per slot
    load_baseline = pd.DataFrame({"slot":["18:00"]*len(sim_companies), "employees":sim_companies["estimated_employees_in_hyderabad"]})
    load_baseline = load_baseline.groupby("slot")["employees"].sum().reset_index()
    load_staggered = sim_companies.groupby("staggered_slot")["estimated_employees_in_hyderabad"].sum().reset_index()
    load_staggered.rename(columns={"staggered_slot":"slot"}, inplace=True)

    colA, colB = st.columns(2)
    with colA:
        figB = px.bar(load_baseline, x="slot", y="employees", title="Before — Single Peak at 18:00")
        st.plotly_chart(figB, use_container_width=True)
    with colB:
        figA = px.bar(load_staggered.sort_values("slot"), x="slot", y="estimated_employees_in_hyderabad", title="After — Smoothed Departures (15-min slots)")
        st.plotly_chart(figA, use_container_width=True)

    # Impact estimate on congestion (toy model)
    peak_before = int(load_baseline["employees"].max())
    peak_after = int(load_staggered["estimated_employees_in_hyderabad"].max())
    reduction_peak = round((peak_before - peak_after) / peak_before * 100, 1) if peak_before else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Peak departure load (Before)", f"{peak_before:,}")
    c2.metric("Peak departure load (After)", f"{peak_after:,}", delta=f"-{peak_before-peak_after:,}")
    c3.metric("Peak smoothing (%)", f"{reduction_peak}%")

    st.download_button("Download Staggered Plan (CSV)", data=sim_companies.to_csv(index=False), file_name="flowsync_staggered_plan.csv")

# ---- Tab 6: Hotspot Map ----
with tab6:
    st.markdown("### HITEC City — Congestion Hotspots")
    st.caption("Focus pilot near repeatable bottlenecks for measurable results.")

    # Pydeck map
    view_state = pdk.ViewState(latitude=17.444, longitude=78.382, zoom=13, pitch=45)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=hotspots,
        get_position='[lon, lat]',
        get_radius=70,
        get_fill_color=[14, 124, 134, 200], # teal
        pickable=True,
    )
    tooltip = {"html":"<b>{name}</b><br/>Lat: {lat}<br/>Lon: {lon}", "style":{"backgroundColor":"#0E7C86","color":"white"}}
    r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip, map_style="mapbox://styles/mapbox/light-v9")
    st.pydeck_chart(r)

    st.dataframe(hotspots, use_container_width=True)

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.markdown(
    "<div class='footer-note'>This dashboard uses sample/synthetic data if live CSVs are not provided. Replace the CSVs with telemetry & HR data to power a real pilot. © FlowSync</div>",
    unsafe_allow_html=True
)
