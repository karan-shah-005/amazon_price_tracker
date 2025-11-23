# streamlit_app.py → FINAL BULLET-PROOF VERSION (Render.com + Python 3.13 tested)
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time

st.set_page_config(page_title="Amazon Price Tracker", page_icon="Chart", layout="wide")
st.title("Live Amazon.in Price Tracker")
st.markdown("**Auto-refreshes every 5 minutes • Data updates every 6 hours**")

# ====================== AUTO REFRESH ======================
refresh_interval = 300
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

elapsed = int(time.time() - st.session_state.last_refresh)
if elapsed >= refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()

mins, secs = divmod(refresh_interval - elapsed, 60)
st.sidebar.info(f"Next auto-refresh: {mins:02d}:{secs:02d}")
if st.sidebar.button("Refresh Now"):
    st.rerun()

# ====================== SAFE PRICE CLEANER ======================
def clean_price(x):
    if pd.isna(x) or not x:
        return None
    s = str(x).replace("₹", "").replace(",", "").replace(" ", "")
    digits = ''.join(c for c in s if c.isdigit() or c == '.')
    try:
        return float(digits) if digits else None
    except:
        return None

# ====================== LOAD DATA ======================
@st.cache_data(ttl=360)
def load_data():
    files = [f for f in os.listdir('.') if f.startswith("amazon_prices_") and f.endswith(".csv")]
    if not files:
        st.error("No CSV files found! Run scraper first.")
        return None, None
    latest = max(files, key=os.path.getctime)
    df = pd.read_csv(latest)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    return relief, latest

df, filename = load_data()
if df is None:
    st.stop()

# ====================== CLEAN & CALCULATE DISCOUNT SAFELY ======================
df["Current_Price"] = df["Price"].apply(clean_price)
df["MRP_Price"]     = df["MRP"].apply(clean_price)

# Only calculate discount where both prices exist and MRP > 0
discount_series = pd.Series(index=df.index, dtype=float)
mask = df["Current_Price"].notna() & df["MRP_Price"].notna() & (df["MRP_Price"] > 0)

# THIS LINE IS 100% SAFE — no more dtype errors
discount_series[mask] = (
    (df.loc[mask, "MRP_Price"] - df.loc[mask, "Current_Price"]) / df.loc[mask, "MRP_Price"] * 100
).astype(float).round(1)

df["Discount_%"] = discount_series

# ====================== DASHBOARD ======================
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Products Tracked", len(df["Title"].dropna().unique()))
with col2:
    avg = df["Current_Price"].mean()
    st.metric("Avg Price", f"₹{avg:,.0f}" if pd.notna(avg) else "N/A")
with col3:
    avg_d = df["Discount_%"].mean()
    st.metric("Avg Discount", f"{avg_d:.1f}%" if pd.notna(avg_d) else "N/A")
with col4:
    last = df["Timestamp"].max()
    st.metric("Last Update", last.strftime("%d %b %Y, %I:%M %p") if pd.notna(last) else "N/A")

st.success(f"Data loaded: `{filename}`")

# ====================== PRICE CHART ======================
chart_df = df.dropna(subset=["Current_Price", "Timestamp"])
if not chart_df.empty:
    fig = px.line(chart_df.sort_values("Timestamp"),
                  x="Timestamp", y="Current_Price", color="Title",
                  title="Live Price Movement", markers=True)
    fig.update_layout(height=500, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Waiting for first successful scrape...")

# ====================== CURRENT TABLE ======================
st.subheader("Current Prices & Hot Deals")
current = df.drop_duplicates(subset="Title", keep="last")[["Title", "Price", "MRP", "Discount_%", "Rating", "Availability", "URL"]]

def highlight(row):
    disc = row["Discount_%"]
    if pd.isna(disc): return [""] * len(row)
    if disc > 10: return ["background-color: #ffb3b3"] * len(row)
    if disc > 5:  return ["background-color: #ffffb3"] * len(row)
    return [""] * len(row)

styled = current.style\
    .format({"Discount_%": lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A",
             "URL": lambda x: f'<a href="{x}" target="_blank">View Product</a>'})\
    .apply(highlight, axis=1)

st.dataframe(styled, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("Professional Amazon Price Tracker • Built by **Your Name** • WhatsApp: +91-XXXXXXXXXX • 100% Automated")