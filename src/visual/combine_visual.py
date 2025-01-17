import folium
import geopandas as gpd
import numpy as np
from shapely.geometry import box

# Define the file paths for input and output
geojson_path_nm = "/Users/georgemccrae/Desktop/drone-noise-collab/src/crucial_osm_geojson/2025londonCONTOURING.geojson"
geojson_path_drone = "/Users/georgemccrae/Desktop/drone-noise-collab/src/recourses/results/experiments/v2_o1000_d200_p0_z100geojson.geojson"
output_map_path = "/Users/georgemccrae/Desktop/drone-noise-collab/combined_visualization.html"

# ISOLVL to noise (dB) conversion map
label_to_noise_map = {
    0: 35,
    1: 37.5,
    2: 42.5,
    3: 47.5,
    4: 52.5,
    5: 57.5,
    6: 62.5,
    7: 67.5,
    8: 72.5,
    9: 77.5,
    10: 82.5
}

# Step 1: Load both GeoJSON files into GeoDataFrames
gdf_nm = gpd.read_file(geojson_path_nm)
gdf_drone = gpd.read_file(geojson_path_drone)

# Step 2: Align the CRS (Coordinate Reference System) if needed
if gdf_nm.crs != gdf_drone.crs:
    gdf_drone = gdf_drone.to_crs(gdf_nm.crs)

# Step 3: Convert ISOLVL labels to noise (dB)
gdf_nm["average_noise"] = gdf_nm["ISOLVL"].map(label_to_noise_map)

# Step 4: Reduce GeoJSON File Size
# 4a: Simplify geometry
gdf_nm["geometry"] = gdf_nm["geometry"].simplify(tolerance=0.001, preserve_topology=True)

# 4b: Remove unnecessary columns
columns_to_keep = ["geometry", "average_noise"]  # Keep only essential data
gdf_nm = gdf_nm[columns_to_keep]

# 4c: Optional: Downsample by taking every nth row
#gdf = gdf.iloc[::10]  # Adjust 10 to a different number for finer control
#print(f"Reduced GeoJSON now has {len(gdf)} features.")

# Step 4: Combine the two GeoDataFrames with noise calculation
def combine_noise(row_nm, row_drone):
    """Combine noise levels from two sources using the decibel formula."""
    if np.isnan(row_nm) and np.isnan(row_drone):
        return np.nan
    elif np.isnan(row_nm):
        return row_drone
    elif np.isnan(row_drone):
        return row_nm
    else:
        # Decibel addition: L = 10 * log10(10^(L1/10) + 10^(L2/10))
        return 10 * np.log10(10 ** (row_nm / 10) + 10 ** (row_drone / 10))

# Perform a spatial join with explicit suffixes
combined_gdf = gpd.sjoin(
    gdf_nm, gdf_drone, how="inner", predicate="intersects", suffixes=("_nm", "_drone")
)

# Combine noise levels
combined_gdf["combined_noise"] = combined_gdf.apply(
    lambda row: combine_noise(row["noise_nm"], row["noise_drone"]),
    axis=1
)

# Check combined noise stats
print(combined_gdf["combined_noise"].describe())


# Step 5: Prepare the map
# Define global min and max noise for consistent color scale
global_min_noise = combined_gdf["combined_noise"].min()
global_max_noise = combined_gdf["combined_noise"].max()

# Create a colormap (white -> orange -> red)
colormap = folium.LinearColormap(
    colors=["white", "orange", "red"],
    vmin=global_min_noise,
    vmax=global_max_noise,
    caption="Combined Noise Level (dB)"
)

# Initialize the map
m = folium.Map(location=[51.5074, -0.1278], zoom_start=11)  # Centered on London

# Add grid cells with combined noise levels
for _, row in combined_gdf.iterrows():
    if row["geometry"] and not row["geometry"].is_empty:
        folium.GeoJson(
            row["geometry"],
            style_function=lambda feature, noise=row["combined_noise"]: {
                "fillColor": colormap(noise) if not np.isnan(noise) else "gray",
                "color": "black",
                "weight": 0.5,
                "fillOpacity": 0.7,
            },
            tooltip=f"Noise: {row['combined_noise']:.2f} dB" if not np.isnan(row["combined_noise"]) else "No Data"
        ).add_to(m)

# Add the colormap to the map
colormap.add_to(m)

# Save the combined visualization to an HTML file
m.save(output_map_path)

print(f"Combined map saved to {output_map_path}")
