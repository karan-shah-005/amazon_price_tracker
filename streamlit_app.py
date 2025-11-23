# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import time

st.set_page_config(page_title="Amazon Price Tracker", layout="wide")
st.title("Live Amazon.in Price Tracker")
st.markdown("Auto-refreshes every 5 minutes | Built with ❤️ using Python + Selenium")

# Auto-refresh every 300 seconds
st.sidebar.info("Auto-refreshing every 5 minutes...")
time.sleep(1)
st.experimental_rerun()  # Remove this line if you want manual refresh

# ====================== LOAD LATEST DATA ======================
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data():
    # Look for the latest CSV file
    files = [f for f in os.listdir() if f.startswith("amazon_prices_") and f.endswith(".csv")]
    if not files:
        st.error("No data found! Run the scraper first.")
        return pd.DataFrame()
    
    latest_file = max(files)
    df = pd.read_csv(latest_file)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    return df

df = load_data()

if df.empty:
    st.stop()

# Clean price columns
def clean_price(price_str):
    if pd.isna(price_str) or price_str == "N/A":
        return None
    return float(str(price_str).replace("₹", "").replace(",", "").strip())

df["Current_Price"] = df["Price"].apply(clean_price)
df["MRP_Price"] = df["MRP"].apply(clean_price)
df["Discount_%"] = ((df["MRP_Price"] - df["Current_Price"]) / df["MRP_Price"] * 100).round(1)

# ====================== SIDEBAR FILTERS ======================
st.sidebar.header("Filters")
selected_products = st.sidebar.multiselect("Select Products", options=df["Title"].unique(), default=df["Title"].unique())

df_filtered = df[df["Title"].isin(selected_products)]

# ====================== MAIN DASHBOARD ======================
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Products Tracked", len(df_filtered))
with col2:
    avg_price = df_filtered["Current_Price"].mean()
    st.metric("Avg Price", f"₹{avg_price:,.0f}" if avg_price else "N/A")
with col3:
    avg_discount = df_filtered["Discount_%"].mean()
    st.metric("Avg Discount", f"{avg_discount:.1f}%" if avg_discount else "N/A")
with col4:
    st.metric("Last Updated", df["Timestamp"].max().strftime("%d %b %Y, %I:%M %p"))

# Price trend chart
if len(df_filtered) > 0:
    fig = px.line(df_filtered, x="Timestamp", y="Current_Price", color="Title",
                  title="Live Price Movement (Last 7 Days)",
                  markers=True)
    fig.update_layout(hovermode="x unified", height=500)
    st.plotly_chart(fig, use_container_width=True)

# Current prices table with alerts
st.subheader("Current Prices & Alerts")
current = df_filtered.drop_duplicates(subset="Title", keep="last").copy()
current = current[["Title", "Current_Price", "MRP_Price", "Discount_%", "Availability", "URL", "Timestamp"]]

# Highlight price drops >8%
def highlight_drop(row):
    if row["Discount_%"] > 8:
        return ['background-color: #ffcccc'] * len(row)
    return [''] * len(row)

styled = current.style.format({
    "Current_Price": "₹{:,.0f}",
    "MRP_Price": "₹{:,.0f}",
    "URL": lambda x: f'<a href="{x}" target="_blank">View Product</a>'
}).apply(highlight_drop, axis=1)

st.dataframe(styled, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown("Built by [Your Name] | Python + Selenium + Streamlit | Contact: +91-xxxxxxxxxx")