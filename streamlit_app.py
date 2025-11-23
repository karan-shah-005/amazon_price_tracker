# streamlit_app.py → 100% Render/Streamlit Cloud safe (Nov 2025)
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time

st.set_page_config(page_title="Amazon Price Tracker", page_icon="📈", layout="wide")
st.title("Live Amazon.in Price Tracker")
st.markdown("**Auto-refreshes every 5 minutes • Data updates every 6 hours**")

# ====================== AUTO REFRESH (2025 method) ======================
refresh_interval = 300  # 5 minutes
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

elapsed = int(time.time() - st.session_state.last_refresh)
if elapsed >= refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()

mins, secs = divmod(refresh_interval - elapsed, 60)
st.sidebar.info(f"Next auto-refresh in: {mins:02d}:{secs:02d}")

if st.sidebar.button("Refresh Now"):
    st.rerun()

# ====================== SAFE PRICE CLEANER ======================
def clean_price(price_str):
    """Safely convert Amazon price string → float or None"""
    if pd.isna(price_str) or not price_str:
        return None
    text = str(price_str).strip()
    if text in ["N/A", "", "None", "Out of stock", "Currently unavailable"]:
        return None
    # Remove ₹, commas, and everything except numbers and decimal point
    digits = ""
    for char in text:
        if char.isdigit() or char == '.':
            digits += char
    try:
        return float(digits) if digits else None
    except:
        return None

# ====================== LOAD LATEST CSV ======================
@st.cache_data(ttl=360)
def load_data():
    csv_files = [f for f in os.listdir('.') if f.startswith("amazon_prices_") and f.endswith(".csv")]
    if not csv_files:
        st.error("No data found! Run the scraper first.")
        return None, None
    
    latest_file = max(csv_files, key=os.path.getctime)
    df = pd.read_csv(latest_file)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    return df, latest_file

df, filename = load_data()
if df is None:
    st.stop()

# Apply safe cleaning
df["Current_Price"] = df["Price"].apply(clean_price)
df["MRP_Price"]     = df["MRP"].apply(clean_price)
df["Discount_%"]    = None
mask = (df["MRP_Price"].notna()) & (df["MRP_Price"] > 0) & (df["Current_Price"].notna())
df.loc[mask, "Discount_%"] = ((df["MRP_Price"] - df["Current_Price"]) / df["MRP_Price"] * 100).round(1)

# ====================== DASHBOARD METRICS ======================
col1, col2, col3, col4 = st.columns(4)
valid_prices = df["Current_Price"].dropna()

with col1:
    st.metric("Products Tracked", len(df["Title"].unique()))
with col2:
    avg = valid_prices.mean()
    st.metric("Average Price", f"₹{avg:,.0f}" if not valid_prices.empty else "N/A")
with col3:
    avg_disc = df["Discount_%"].mean()
    st.metric("Average Discount", f"{avg_disc:.1f}%" if avg_disc else "N/A")
with col4:
    last = df["Timestamp"].max()
    st.metric("Last Updated", last.strftime("%d %b %Y, %I:%M %p") if pd.notna(last) else "N/A")

st.info(f"Latest file: `{filename}`")

# ====================== PRICE CHART ======================
fig = px.line(df.dropna(subset=["Current_Price", "Timestamp"]).sort_values("Timestamp"),
              x="Timestamp", y="Current_Price", color="Title",
              title="Live Price Movement", markers=True,
              hover_data={"Discount_%": ":.1f", "Availability": True})
fig.update_layout(height=500, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# ====================== CURRENT TABLE WITH ALERTS ======================
st.subheader("Current Prices")
current = df.drop_duplicates(subset="Title", keep="last").copy()
current = current[["Title", "Price", "MRP", "Discount_%", "Rating", "Availability", "URL"]]

def highlight_discount(row):
    if pd.isna(row["Discount_%"]): return [""] * len(row)
    if row["Discount_%"] > 10:     return ["background-color: #ffcccc"] * len(row)
    if row["Discount_%"] > 5:      return ["background-color: #fff4cc"] * len(row)
    return [""] * len(row)

styled = current.style\
    .format({"Discount_%": lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A",
             "URL": lambda x: f'<a href="{x}" target="_blank">View</a>'})\
    .apply(highlight_discount, axis=1)

st.dataframe(styled, use_container_width=True, hide_index=True)

# ====================== FOOTER ======================
st.markdown("---")
st.markdown("Built by **Your Name** • WhatsApp: +91-xxxxxxxxx • Fully automated 24/7")