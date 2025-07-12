import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
from modules.gee_utils import get_composite_image, get_rgb_thumbnail, classify_and_summarize
import ee
from PIL import Image
import requests
from io import BytesIO

# -------------------- Session Initialization --------------------
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "generate_pdf" not in st.session_state:
    st.session_state.generate_pdf = False

def save_image_from_url(url, filename):
    """
    Downloads an image from a URL and saves it locally.
    """
    response = requests.get(url)
    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        img.save(filename)


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
if "submitted" not in st.session_state:
    st.session_state.submitted = False

if st.sidebar.button("Run Analysis"):
    st.session_state.submitted = True
    st.session_state.generate_pdf = False  # reset report trigger


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

# Show selected coordinates
if region_option == "Custom Coordinates":
    st.info(f"📍 Custom Location Selected:\n- Latitude = `{lat}`\n- Longitude = `{lon}`\n- Buffer = `{buffer_km} km`")
else:
    st.info("📍 Region: EKSU Environs (predefined)")

# RGB Band Legend
with st.expander("ℹ️ RGB Bands Info"):
    st.markdown("""
    **Sentinel-2 RGB Composite**
    - **B4** = Red  
    - **B3** = Green  
    - **B2** = Blue  
    This true-color visualization simulates how the human eye sees the landscape.
    """)

# Section 1: Map/Imagery Output
st.header("🛰️ Satellite Image View")
if st.session_state.submitted:
    st.info("Fetching satellite images for before and after...")

    try:
        midpoint = start_date + (end_date - start_date) / 2

        before_img = get_composite_image(str(start_date), str(midpoint), region_geom)
        before_rgb = before_img.select(['B4', 'B3', 'B2']).visualize(min=100, max=3000, bands=['B4', 'B3', 'B2'])
        before_url = get_rgb_thumbnail(before_rgb, region_geom)
        st.session_state.before_url = before_url

        after_img = get_composite_image(str(midpoint + timedelta(days=1)), str(end_date), region_geom)
        after_rgb = after_img.select(['B4', 'B3', 'B2']).visualize(min=100, max=3000, bands=['B4', 'B3', 'B2'])
        after_url = get_rgb_thumbnail(after_rgb, region_geom)
        st.session_state.after_url = after_url

        # Display images side by side
        st.success("Images fetched successfully!")
        col1, col2 = st.columns(2)
        col1.image(before_url, caption=f"Before: {start_date} to {midpoint} {caption_suffix}", use_container_width=True)
        col2.image(after_url, caption=f"After: {midpoint} to {end_date} {caption_suffix}", use_container_width=True)

    except Exception as e:
        st.error(f"Failed to fetch images: {e}")

# Section 2: Change Detection Summary
if st.session_state.submitted and 'before_img' in locals() and 'after_img' in locals():
    try:
        st.info("Running unsupervised classification for change detection...")

        n_clusters = 4  # Consistent cluster count used across classification and visualization

        before_summary, before_clustered = classify_and_summarize(before_img, region_geom, n_clusters=n_clusters)
        st.session_state.before_summary = before_summary
        after_summary, after_clustered = classify_and_summarize(after_img, region_geom, n_clusters=n_clusters)
        st.session_state.after_summary = after_summary

        st.success("Classification completed!")

        st.subheader("🖼️ Cluster Visualization")

        # Define the cluster color palette
        palette = ['red', 'green', 'blue', 'yellow']

        # Visualize and fetch thumbnails
        before_vis = before_clustered.visualize(min=0, max=n_clusters - 1, palette=palette)
        after_vis = after_clustered.visualize(min=0, max=n_clusters - 1, palette=palette)

        before_thumb = get_rgb_thumbnail(before_vis, region_geom)
        after_thumb = get_rgb_thumbnail(after_vis, region_geom)


        # Side-by-side display
        col1, col2 = st.columns(2)
        col1.image(before_thumb, caption="Cluster Map (Before)", use_container_width=True)
        col2.image(after_thumb, caption="Cluster Map (After)", use_container_width=True)

        # Display legend
        st.markdown("**🗺️ Cluster Legend**")
        legend_md = "| Cluster ID | Color |\n|------------|--------|\n"
        for i, color in enumerate(palette):
            legend_md += f"| {i} | {color.capitalize()} |\n"
        st.markdown(legend_md)

        st.subheader("📋 Cluster Area Comparison (hectares)")

        all_keys = sorted(set(before_summary.keys()) | set(after_summary.keys()))
        before_vals = [before_summary.get(k, 0) for k in all_keys]
        after_vals = [after_summary.get(k, 0) for k in all_keys]

        table_data = []
        for k in all_keys:
            b = before_summary.get(k, 0)
            a = after_summary.get(k, 0)
            diff = round(a - b, 2)
            percent = round((diff / b) * 100, 2) if b != 0 else "N/A"
            table_data.append((k, b, a, diff, percent))

        df_table = pd.DataFrame(table_data, columns=['Cluster', 'Before', 'After', 'Change', '% Change'])
        st.dataframe(df_table)

        # Plotly Grouped Bar Chart
        fig = go.Figure(data=[
            go.Bar(name='Before', x=[str(k) for k in all_keys], y=before_vals, marker_color='rgb(158,202,225)'),
            go.Bar(name='After', x=[str(k) for k in all_keys], y=after_vals, marker_color='rgb(255,178,102)')
        ])
        fig.update_layout(
            barmode='group',
            xaxis_title='Cluster ID',
            yaxis_title='Area (hectares)',
            title='Land Use Category Comparison',
            legend=dict(x=0.8, y=1.1, orientation='h')
        )
        st.plotly_chart(fig, use_container_width=True)

        # Save plot as image
        # Recreate chart image (for PDF)
        fig_image = go.Figure()
        fig_image.add_trace(go.Bar(name='Before', x=df_table['Cluster'], y=df_table['Before'], marker_color='rgb(158,202,225)'))
        fig_image.add_trace(go.Bar(name='After', x=df_table['Cluster'], y=df_table['After'], marker_color='rgb(255,178,102)'))
        fig_image.update_layout(
            barmode='group',
            title='Cluster Area Comparison',
            xaxis_title='Cluster',
            yaxis_title='Area (hectares)',
            legend=dict(x=0.75, y=1.1, orientation='h')
        )
        fig_image.write_image("chart.png")


    except Exception as e:
        st.error(f"Failed to generate summary: {e}")

# Section 3: Downloadable Report
st.header("📥 Downloadable Report")

if st.button("Generate Report PDF"):
    st.session_state.generate_pdf = True

if st.session_state.generate_pdf:
    try:
        metadata = {
            "Region": region_option,
            "Buffer (km)": buffer_km if region_option == "Custom Coordinates" else "N/A",
            "Start Date": start_date,
            "End Date": end_date
        }

        summary_structured = {
            "clusters": {
                k: {
                    "before": st.session_state.before_summary.get(k, 0),
                    "after": st.session_state.after_summary.get(k, 0),
                    "change": round(st.session_state.after_summary.get(k, 0) - st.session_state.before_summary.get(k, 0), 2),
                    "percent": round(((st.session_state.after_summary.get(k, 0) - st.session_state.before_summary.get(k, 0)) / st.session_state.before_summary.get(k, 0)) * 100, 2)
                    if st.session_state.before_summary.get(k, 0) != 0 else 0
                } for k in sorted(set(st.session_state.before_summary) | set(st.session_state.after_summary))
            }
        }

        # Save the images
        save_image_from_url(st.session_state.before_url, "before.png")
        save_image_from_url(st.session_state.after_url, "after.png")
        fig_image.write_image("chart.png")

        from modules.report_utils import generate_pdf_report
        generate_pdf_report("before.png", "after.png", summary_structured, "chart.png", "report.pdf", metadata)

        with open("report.pdf", "rb") as f:
            st.download_button("📄 Download PDF Report", f, file_name="LULC_Report.pdf")

    except Exception as e:
        st.error(f"Failed to generate report: {e}")
    st.session_state.generate_pdf = False

