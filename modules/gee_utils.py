import ee
from datetime import datetime

# Initialize Earth Engine with your project ID
try:
    ee.Initialize(project='lulc-dashboard') 
except Exception as e:
    ee.Authenticate()
    ee.Initialize(project='lulc-dashboard')

# -------------------------
# Cloud Masking Function
# -------------------------
def mask_s2_clouds(image):
    """
    Applies a mask to remove clouds using Sentinel-2 QA60 band.
    """
    qa = image.select('QA60')
    cloud_mask = qa.bitwiseAnd(int('010000000000', 2)).eq(0)
    return image.updateMask(cloud_mask).copyProperties(image, ["system:time_start"])

# -------------------------
# Get Sentinel-2 Composite
# -------------------------
def get_composite_image(start_date, end_date, region_geom):
    """
    Returns a cloud-masked Sentinel-2 image composite for the specified date range and region.
    """
    s2 = (ee.ImageCollection("COPERNICUS/S2")
          .filterDate(start_date, end_date)
          .filterBounds(region_geom)
          .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 20)
          .map(mask_s2_clouds))

    composite = s2.median().clip(region_geom)

    # Log info
    info = composite.getInfo()
    print("Composite metadata:", info)

    return composite

# -------------------------
# Generate Thumbnail URL (visualized image)
# -------------------------
def get_rgb_thumbnail(image, region_geom):
    """
    Returns a downloadable PNG thumbnail from a display-ready ee.Image using .visualize().
    Assumes the image has already been visualized.
    """
    url = image.getThumbURL({
        'region': region_geom,
        'scale': 50,  # Sentinel-2 RGB resolution
        'format': 'png'
    })
    return url

def classify_and_summarize(image, region_geom, n_clusters=4):
    """
    Classify an image using unsupervised KMeans clustering and summarize pixel area per class.

    Returns:
        A dictionary mapping cluster ID to estimated area in hectares.
    """
    # Select bands relevant for LULC differentiation
    bands = ['B2', 'B3', 'B4', 'B8']
    input_image = image.select(bands)

    # Step 1: Sample training pixels
    training = input_image.sample(
        region=region_geom,
        scale=10,
        numPixels=5000,
        seed=42
    )

    # ⚠️ Count the samples before proceeding
    size = training.size().getInfo()
    print(f"Sample size: {size}")
    if size == 0:
        print("No training data found in the region!")
        return {}

    # Step 2: Train KMeans and classify
    clusterer = ee.Clusterer.wekaKMeans(n_clusters).train(training)
    clustered = input_image.cluster(clusterer)

    # Step 3: Histogram of cluster labels
    clustered = clustered.rename('cluster')  # Set a proper band name

    # Ensure projection is set
    clustered = clustered.setDefaultProjection('EPSG:4326', None, 10)

    histogram = clustered.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=region_geom,
        scale=10,
        maxPixels=1e9,
        bestEffort=True
    ).getInfo()
    print("Histogram result:", histogram)

    class_freq = histogram.get('cluster', {})
    result = {int(k): round(v * 0.01, 2) for k, v in class_freq.items()}  # hectares

    return result, clustered

