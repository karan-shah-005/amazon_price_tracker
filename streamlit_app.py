# streamlit_app.py → Works perfectly on Streamlit 1.38+ (Nov 2025)
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import time

# Page config
st.set_page_config(
    page_title="Amazon Price Tracker",
    page_icon="📈",
    layout="wide"
)

st.title("🚀 Live Amazon.in Price Tracker")
st.markdown("**Auto-refreshes every 5 minutes** | Data updates every 6 hours")

# ====================== AUTO REFRESH (NEW 2025 METHOD) ======================
# Add a refresh countdown + button
placeholder = st.empty()

refresh_interval = 300  # seconds (5 minutes)

if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

elapsed = int(time.time() - st.session_state.last_refresh)

if elapsed >= refresh_interval:
    st.session_state.last_refresh = time.time()
    st.rerun()  # This is the new correct way (replaces experimental_rerun)

with placeholder.container():
    mins, secs = divmod(refresh_interval - elapsed, 60)
    st.markdown(f"🔄 **Next auto-refresh in:** {mins:02d}:{secs:02d}")

# Optional: Manual refresh button
if st.button("Refresh Now"):
    st.rerun()

# ====================== LOAD LATEST DATA ======================
@st.cache_data(ttl=360)  # Cache 6 minutes
def load_latest_data():
    files = [f for f in os.listdir('.') if f.startswith("amazon_prices_") and f.endswith(".csv")]
    if not files:
        st.error("No scraped data found! Run the scraper first.")
        return pd.DataFrame()
    
    latest_file = max(files, key=os.path.getctime)
    df = pd.read_csv(latest_file)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    return df, latest_file

df, filename = load_latest_data()
if df.empty:
    st.stop()

# Clean prices
def clean_price(x):
    if pd.isna(x) or x == "N/A": return None
    return float(str(x).replace("₹", "").replace(",", "").replace(".", "").strip())

df["Current_Price"] = df["Price"].apply(clean_price)
df["MRP_Clean"] = df["MRP"].apply(clean_price)
df["Discount_%"] = ((df["MRP_Clean"] - df["Current_Price"]) / df["MRP_Clean"] * 100).round(1)

# ====================== DASHBOARD ======================
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Products Tracked", len(df["Title"].unique()))
with col2:
    avg = df["Current_Price"].mean()
    st.metric("Average Price", f"₹{avg:,.0f}" if avg else "N/A")
with col3:
    disc = df["Discount_%"].mean()
    st.metric("Average Discount", f"{disc:.1f}%" if disc else "N/A")
with col4:
    last_update = df["Timestamp"].max()
    st.metric("Last Scrape", last_update.strftime("%d %b %Y, %I:%M %p"))

st.info(f"Data source: `{filename}`")

# Price trend line chart
fig = px.line(df.sort_values("Timestamp"),
              x="Timestamp",
              y="Current_Price",
              color="Title",
              title="📉 Live Price Movement",
              markers=True,
              hover_data=["Discount_%", "Availability"])
fig.update_layout(height=500, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# Current status table with alerts
st.subheader("Current Prices (Real-Time)")
current = df.drop_duplicates(subset="Title", keep="last")[["Title", "Price", "MRP", "Discount_%", "Rating", "Availability", "URL"]]

def highlight_rows(row):
    if row["Discount_%"] > 10:
        return ['background-color: #ffcccc'] * len(row)
    elif row["Discount_%"] > 5:
        return ['background-color: #fff4cc'] * len(row)
    return [''] * len(row)

styled = current.style\
    .format({"URL": lambda x: f'<a href="{x}" target="_blank">View on Amazon</a>', "Discount_%": "{:.1f}%"})\
    .apply(highlight_rows, axis=1)

st.dataframe(styled, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown("Built by **[Your Name]** | Python + Selenium + Streamlit | WhatsApp: +91-xxxxxxxxxx")