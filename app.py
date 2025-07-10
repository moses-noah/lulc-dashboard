import streamlit as st
import pandas as pd
from datetime import date, timedelta
from modules.gee_utils import get_composite_image, get_rgb_thumbnail, classify_and_summarize
import ee

# -------------------- Page Config --------------------
st.set_page_config(
    page_title="Land Use Change Detection Dashboard",
    layout="wide"
)

# -------------------- Sidebar --------------------
st.sidebar.title("Input Parameters")

# Location Input
st.sidebar.subheader("Select Region")
region_option = st.sidebar.selectbox(
    "Choose a predefined region:",
    ["EKSU Environs", "Custom Coordinates"]
)

# Default location: EKSU Environs
region_geom = ee.Geometry.Polygon([
    [[5.2772, 7.7326], [5.2772, 7.7500], [5.2950, 7.7500], [5.2950, 7.7326], [5.2772, 7.7326]]
])
caption_suffix = ""  # Default caption suffix

if region_option == "Custom Coordinates":
    lat = st.sidebar.number_input("Latitude", value=7.7380, format="%.6f")
    lon = st.sidebar.number_input("Longitude", value=5.2860, format="%.6f")

    buffer_km = st.sidebar.number_input("Buffer Radius (km)", value=3.0, min_value=0.1, max_value=10.0, step=0.1)
    delta = buffer_km / 111.0  # Convert km to approximate degrees

    region_geom = ee.Geometry.Polygon([
        [
            [lon - delta, lat - delta],
            [lon - delta, lat + delta],
            [lon + delta, lat + delta],
            [lon + delta, lat - delta],
            [lon - delta, lat - delta]
        ]
    ])
    caption_suffix = f"(Buffer: {buffer_km} km)"

# Date Range Input
st.sidebar.subheader("Select Time Range")
start_date = st.sidebar.date_input("Start Date", value=date(2015, 6, 30), min_value=date(2015, 6, 30))
end_date = st.sidebar.date_input("End Date", value=date(2023, 1, 1))

if start_date < date(2015, 6, 30):
    st.sidebar.warning("Sentinel-2 data is only available from June 30, 2015 onward.")

# Submission button
submit = st.sidebar.button("Run Analysis")

# -------------------- Main Page --------------------
st.title("🌍 Land Use Change Detection Dashboard")
st.markdown(
    """
    This tool allows users to analyze and visualize land use and land cover changes 
    in any selected region using freely available satellite imagery. 
    Start by selecting a region and date range from the sidebar.
    """
)

# Add spacing
st.markdown("---")

# Section 1: Map/Imagery Output
st.header("🛰️ Satellite Image View")
if submit:
    st.info("Fetching satellite images for before and after...")

    try:
        midpoint = start_date + (end_date - start_date) / 2

        before_img = get_composite_image(str(start_date), str(midpoint), region_geom)
        before_rgb = before_img.select(['B4', 'B3', 'B2']).visualize(min=100, max=3000, bands=['B4', 'B3', 'B2'])
        before_url = get_rgb_thumbnail(before_rgb, region_geom)

        after_img = get_composite_image(str(midpoint + timedelta(days=1)), str(end_date), region_geom)
        after_rgb = after_img.select(['B4', 'B3', 'B2']).visualize(min=100, max=3000, bands=['B4', 'B3', 'B2'])
        after_url = get_rgb_thumbnail(after_rgb, region_geom)

        st.success("Images fetched successfully!")
        col1, col2 = st.columns(2)
        col1.image(before_url, caption=f"Before: {start_date} to {midpoint} {caption_suffix}", use_column_width=True)
        col2.image(after_url, caption=f"After: {midpoint} to {end_date} {caption_suffix}", use_column_width=True)

    except Exception as e:
        st.error(f"Failed to fetch images: {e}")

# Section 2: Change Detection Summary
st.header("📊 Change Detection Summary")
if submit and 'before_img' in locals() and 'after_img' in locals():
    try:
        st.info("Running unsupervised classification for change detection...")

        before_summary, before_clustered = classify_and_summarize(before_img, region_geom)
        after_summary, after_clustered = classify_and_summarize(after_img, region_geom)


        st.write("Before Summary Data:", before_summary)
        st.write("After Summary Data:", after_summary)

        st.success("Classification completed!")

        st.subheader("🖼️ Cluster Visualization")

        n_clusters = 4  # must match what you used during classification

        before_vis = before_clustered.visualize(
            min=0, max=n_clusters - 1,
            palette=['red', 'green', 'blue', 'yellow']
        )
        before_thumb = get_rgb_thumbnail(before_vis, region_geom)
        st.image(before_thumb, caption="Cluster Map (Before)", use_column_width=True)

        after_vis = after_clustered.visualize(
            min=0, max=n_clusters - 1,
            palette=['red', 'green', 'blue', 'yellow']
        )
        after_thumb = get_rgb_thumbnail(after_vis, region_geom)
        st.image(after_thumb, caption="Cluster Map (After)", use_column_width=True)

        st.subheader("📋 Cluster Area Comparison (hectares)")
        st.write("| Cluster | Before | After | Change | % Change |")
        st.write("|---------|--------|-------|--------|----------|")

        all_keys = sorted(set(before_summary.keys()) | set(after_summary.keys()))
        for k in all_keys:
            b = before_summary.get(k, 0)
            a = after_summary.get(k, 0)
            diff = round(a - b, 2)
            percent = round((diff / b) * 100, 2) if b != 0 else "N/A"
            st.write(f"| {k} | {b} | {a} | {diff} | {percent}% |")

        # Create DataFrame from cluster values
        df = pd.DataFrame({
            'Cluster': all_keys,
            'Before': [before_summary.get(k, 0) for k in all_keys],
            'After': [after_summary.get(k, 0) for k in all_keys],
        })

        st.subheader("📈 Cluster Area Comparison Chart")
        st.bar_chart(df.set_index('Cluster'))


    except Exception as e:
        st.error(f"Failed to generate summary: {e}")

# Section 3: Downloadable Report
st.header("📥 Optional Report Export")
if submit:
    st.success("Report generation will be added here.")
