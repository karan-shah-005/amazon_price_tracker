# Run this file every 6 hours (via cron or Render)
import os
import subprocess

# Run scraper
print("Running Amazon scraper...")
subprocess.run(["python", "amazon_price_tracker.py"])

# Then launch dashboard (only needed locally)
# os.system("streamlit run streamlit_app.py")