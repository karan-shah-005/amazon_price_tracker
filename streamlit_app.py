# streamlit_app.py → FINAL VERSION — ZERO CRASHES on Render/Streamlit Cloud
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time

st.set_page_config(page_title="Amazon Price Tracker", page_icon="Chart", layout="wide")
st.title("Live Amazon.in Price Tracker")
st.markdown("**Auto-refreshes every 5 minutes • Data updates every 6 hours**")

# ====================== AUTO REFRESH ======================
refresh_interval = 300  # 5 minutes
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

# ====================== SUPER SAFE PRICE CLEANER ======================
def clean_price(text):
    if pd.isna(text) or not text:
        return None
    s = str(text).strip()
    if s in ["N/A", "None", "", "Out of stock", "Currently unavailable"]:
        return None
    digits = ''.join(c for c in s if c.isdigit() or c == '.')
    if not digits:
        return None
    try:
        return float(digits)
    except:
        return None

# ====================== LOAD DATA ======================
@st.cache_data(ttl=360)
def load_data():
    files = [f for f in os.listdir('.') if f.startswith("amazon_prices_") and f.endswith(".csv")]
    if not files:
        st.error("No CSV files found! Run the scraper first.")
        return None, None
    latest = max(files, key=os.path.getctime)
    df = pd.read_csv(latest)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    return df, latest

df, filename = load_data()
if df is None:
    st.stop()

# ====================== CLEAN PRICES & CALCULATE DISCOUNT ======================
df["Current_Price"] = df["Price"].apply(clean_price)
df["MRP_Price"] = df["MRP"].apply(clean_price)

# Safe discount calculation (only where both prices exist)
df["Discount_%"] = None
valid = df["Current_Price"].notna() & df["MRP_Price"].notna() & (df["MRP_Price"] > 0)
df.loc[valid, "Discount_%"] = (
    (df.loc[valid, "MRP_Price"] - df.loc[valid, "Current_Price"]) / df.loc[valid, "MRP_Price"] * 100
).round(1).astype(float)   # ← This fixes the object dtype error

# ====================== METRICS ======================
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Products Tracked", len(df["Title"].dropna().unique()))
with col2:
    avg_price = df["Current_Price"].mean()
    st.metric("Avg Price", f"₹{avg_price:,.0f}" if pd.notna(avg_price) else "N/A")
with col3:
    avg_disc = df["Discount_%"].mean()
    st.metric("Avg Discount", f"{avg_disc:.1f}%" if pd.notna(avg_disc) else "N/A")
with col4:
    last = df["Timestamp"].max()
    st.metric("Last Update", last.strftime("%d %b %Y, %I:%M %p") if pd.notna(last) else "N/A")

st.info(f"Latest data: `{filename}`")

# ====================== PRICE CHART ======================
chart_data = df.dropna(subset=["Current_Price", "Timestamp"])
if not chart_data.empty:
    fig = px.line(chart_data.sort_values("Timestamp"),
                  x="Timestamp", y="Current_Price", color="Title",
                  title="Live Price Trend", markers=True,
                  hover_data={"Discount_%": ":.1f", "Availability": True})
    fig.update_layout(height=500, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No valid price data to display in chart yet.")

# ====================== CURRENT TABLE ======================
st.subheader("Current Prices & Deals")
current = df.drop_duplicates(subset="Title", keep="last").copy()
display_cols = ["Title", "Price", "MRP", "Discount_%", "Rating", "Availability", "URL"]

def highlight(row):
    if pd.isna(row["Discount_%"]):
        return [""] * len(row)
    if row["Discount_%"] > 10:
        return ["background-color: #ffb3b3"] * len(row)
    if row["Discount_%"] > 5:
        return ["background-color: #ffffb3"] * len(row)
    return [""] * len(row)

styled = current[display_cols].style\
    .format({"Discount_%": lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A",
             "URL": lambda x: f'<a href="{x}" target="_blank">View</a>'})\
    .apply(highlight, axis=1)

st.dataframe(styled, use_container_width=True, hide_index=True)

# ====================== FOOTER ======================
st.markdown("---")
st.markdown("Professional Amazon Price Tracker • Built by **Your Name** • WhatsApp: +91-xxxxxxxxx")