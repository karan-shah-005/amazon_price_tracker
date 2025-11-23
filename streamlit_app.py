# streamlit_app.py → FIXED VERSION (All bugs resolved)
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time

st.set_page_config(page_title="Amazon Price Tracker", page_icon="📊", layout="wide")
st.title("🛒 Live Amazon.in Price Tracker")
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
st.sidebar.info(f"⏱️ Next auto-refresh: {mins:02d}:{secs:02d}")
if st.sidebar.button("🔄 Refresh Now"):
    st.rerun()

# ====================== SAFE PRICE CLEANER ======================
def clean_price(x):
    """Safely extract numeric price from string"""
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
    """Load the most recent CSV file"""
    files = [f for f in os.listdir('.') if f.startswith("amazon_prices_") and f.endswith(".csv")]
    if not files:
        st.error("❌ No CSV files found! Run scraper first.")
        return None, None
    latest = max(files, key=os.path.getctime)
    try:
        df = pd.read_csv(latest)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        return df, latest  # BUG FIX: Changed 'relief' to 'df'
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return None, None

df, filename = load_data()
if df is None:
    st.stop()

# ====================== CLEAN & CALCULATE DISCOUNT SAFELY ======================
df["Current_Price"] = df["Price"].apply(clean_price)
df["MRP_Price"] = df["MRP"].apply(clean_price)

# Initialize discount column with None
df["Discount_%"] = None

# Only calculate discount where both prices exist and MRP > 0
mask = (
    df["Current_Price"].notna() & 
    df["MRP_Price"].notna() & 
    (df["MRP_Price"] > 0) &
    (df["Current_Price"] > 0)  # BUG FIX: Added check for positive current price
)

# Calculate discount safely
if mask.any():
    df.loc[mask, "Discount_%"] = (
        (df.loc[mask, "MRP_Price"] - df.loc[mask, "Current_Price"]) / 
        df.loc[mask, "MRP_Price"] * 100
    ).round(1)

# ====================== DASHBOARD ======================
col1, col2, col3, col4 = st.columns(4)

with col1:
    unique_products = len(df["Title"].dropna().unique())
    st.metric("📦 Products Tracked", unique_products)

with col2:
    avg = df["Current_Price"].mean()
    st.metric("💰 Avg Price", f"₹{avg:,.0f}" if pd.notna(avg) else "N/A")

with col3:
    avg_d = df["Discount_%"].mean()
    st.metric("🎯 Avg Discount", f"{avg_d:.1f}%" if pd.notna(avg_d) else "N/A")

with col4:
    last = df["Timestamp"].max()
    st.metric("🕒 Last Update", last.strftime("%d %b %Y, %I:%M %p") if pd.notna(last) else "N/A")

st.success(f"✅ Data loaded: `{filename}`")

# ====================== PRICE CHART ======================
st.subheader("📈 Price Movement Over Time")
chart_df = df.dropna(subset=["Current_Price", "Timestamp"])

if not chart_df.empty:
    fig = px.line(
        chart_df.sort_values("Timestamp"),
        x="Timestamp", 
        y="Current_Price", 
        color="Title",
        title="Live Price Movement", 
        markers=True,
        labels={"Current_Price": "Price (₹)", "Timestamp": "Date & Time"}
    )
    fig.update_layout(height=500, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("⏳ Waiting for first successful scrape...")

# ====================== CURRENT TABLE ======================
st.subheader("🔥 Current Prices & Hot Deals")

# Get latest entry for each product
current = df.sort_values("Timestamp").drop_duplicates(subset="Title", keep="last")
current = current[["Title", "Price", "MRP", "Discount_%", "Rating", "Availability", "URL"]].copy()

# BUG FIX: Define highlighting function properly
def highlight(row):
    """Highlight rows based on discount percentage"""
    disc = row["Discount_%"]
    if pd.isna(disc): 
        return [""] * len(row)
    if disc >= 10:  # BUG FIX: Changed > to >= for better edge case handling
        return ["background-color: #ffb3b3"] * len(row)
    if disc >= 5:   # BUG FIX: Changed > to >=
        return ["background-color: #ffffb3"] * len(row)
    return [""] * len(row)

# Format table
try:
    styled = current.style.format({
        "Discount_%": lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A",
        "Rating": lambda x: f"{x}" if pd.notna(x) else "N/A",
        "Price": lambda x: x if pd.notna(x) else "N/A",
        "MRP": lambda x: x if pd.notna(x) else "N/A",
        "Availability": lambda x: x if pd.notna(x) else "N/A"
    }, escape=None).apply(highlight, axis=1)
    
    # BUG FIX: Removed HTML formatting for URL in dataframe
    # Streamlit doesn't render HTML in dataframes by default
    st.dataframe(styled, use_container_width=True, hide_index=True)
    
    # Add clickable links separately
    st.markdown("**🔗 Product Links:**")
    for idx, row in current.iterrows():
        if pd.notna(row["URL"]):
            st.markdown(f"• [{row['Title']}]({row['URL']})")
            
except Exception as e:
    st.warning(f"⚠️ Styling error: {e}. Showing plain table.")
    st.dataframe(current, use_container_width=True, hide_index=True)

# ====================== DOWNLOAD OPTION ======================
st.markdown("---")
csv = current.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Current Prices (CSV)",
    data=csv,
    file_name=f"amazon_prices_{time.strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
)

# ====================== FOOTER ======================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        Professional Amazon Price Tracker • Built with ❤️ by <strong>Your Name</strong><br>
        📱 WhatsApp: +91-XXXXXXXXXX • 🤖 100% Automated
    </div>
    """, 
    unsafe_allow_html=True
)