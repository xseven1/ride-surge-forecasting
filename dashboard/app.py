import time
import requests
import numpy as np
import pandas as pd
import streamlit as st
import os

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="Real-Time Demand Forecasting", layout="wide")

st.title("Real-Time Demand Forecasting and Surge Dashboard")

with st.sidebar:
    st.header("Controls")

    request_rate = st.slider("Request rate (events per second)", 0, 200, 30, 1)
    rush_hour = st.toggle("Rush hour", value=False)
    rain = st.toggle("Rain", value=False)
    event = st.toggle("Special event", value=False)

    if st.button("Apply controls"):
        requests.post(f"{API_BASE}/control", json={
            "request_rate": request_rate,
            "rush_hour": rush_hour,
            "rain": rain,
            "event": event,
        })

    st.divider()
    refresh = st.slider("Refresh interval (seconds)", 1, 5, 1, 1)

colA, colB = st.columns([2, 1], gap="large")

@st.cache_data(ttl=1)
def fetch_state():
    resp = requests.get(f"{API_BASE}/zones/state", timeout=3)
    resp.raise_for_status()
    return resp.json()

with colA:
    st.subheader("Zone grid (surge multiplier)")
    data = fetch_state()
    zones = data.get("zones", [])

    if not zones:
        st.info("No zone data yet. Start simulator and aggregator first.")
    else:
        # Map zones into a grid
        n = max([z["zone_id"] for z in zones]) + 1
        n_zones = n
        rows = int(np.ceil(np.sqrt(n_zones)))
        cols = int(np.ceil(n_zones / rows))

        grid = np.full((rows, cols), np.nan, dtype=float)
        for z in zones:
            zid = z["zone_id"]
            r = zid // cols
            c = zid % cols
            grid[r, c] = z.get("surge_multiplier") if z.get("surge_multiplier") is not None else np.nan

        st.dataframe(pd.DataFrame(grid), use_container_width=True, height=360)

with colB:
    st.subheader("Zone drill-down")
    zone_ids = [z["zone_id"] for z in zones] if zones else list(range(20))
    selected = st.selectbox("Zone", zone_ids, index=0)

    if zones:
        zrow = next((z for z in zones if z["zone_id"] == selected), None)
        if zrow:
            feats = zrow["features"]
            st.metric("Predicted next 5m demand", f"{zrow['pred_next_5m_demand']:.2f}" if zrow["pred_next_5m_demand"] is not None else "N/A")
            st.metric("Surge multiplier", f"{zrow['surge_multiplier']:.2f}" if zrow["surge_multiplier"] is not None else "N/A")

            st.write("Current features")
            st.json(feats)

st.caption("Tip: run simulator + aggregator, then run training to enable predictions.")
time.sleep(refresh)
st.rerun()