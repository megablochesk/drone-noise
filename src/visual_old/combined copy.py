import geopandas as gpd
import folium
import numpy as np
from shapely.geometry import Point

# File paths for the GeoJSON files
script_geojson_path = "/Users/georgemccrae/Desktop/bethygsmall_CONTOURING_NOISE_MAP.geojson"
provided_geojson_path = "/Users/georgemccrae/Desktop/drone-noise-collab/src/recourses/results/experiments/v2_o1000_d200_p0_z100geojson.geojson"

# Dictionary for ISOLVL to noise mapping
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
    10: 82.5,
}

# Function to convert ISOLVL to decibels
def isolvl_to_db(isolvl):
    return label_to_noise_map.get(isolvl, 0)

# Step 1: Load both GeoJSON datasets
script_gdf = gpd.read_file(script_geojson_path)
provided_gdf = gpd.read_file(provided_geojson_path)

# Step 2: Convert ISOLVL to decibels for baseline dataset (if ISOLVL exists)
if "ISOLVL" in script_gdf.columns:
    script_gdf["average_noise"] = script_gdf["ISOLVL"].apply(isolvl_to_db)

# Step 3: Ensure CRS compatibility
script_gdf = script_gdf.to_crs("EPSG:4326")
provided_gdf = provided_gdf.to_crs("EPSG:4326")

# Step 4: Perform a spatial join to combine datasets
# Use 'inner' join and ensure geometry compatibility
combined_gdf = gpd.sjoin(provided_gdf, script_gdf, how="inner", predicate="intersects")

# Rename columns for clarity
combined_gdf.rename(
    columns={
        "average_noise_left": "provided_avg_noise",
        "max_noise_left": "provided_max_noise",
        "average_noise_right": "script_avg_noise",
        "max_noise_right": "script_max_noise",
    },
    inplace=True,
)

# Step 5: Calculate combined noise metrics
# Use mean and max of the overlapping noise values
combined_gdf["combined_average_noise"] = combined_gdf[
    ["provided_avg_noise", "script_avg_noise"]
].mean(axis=1, skipna=True)
combined_gdf["combined_max_noise"] = combined_gdf[
    ["provided_max_noise", "script_max_noise"]
].max(axis=1, skipna=True)

# Step 6: Create a heatmap visualization using Folium
m = folium.Map(location=[51.5074, -0.1278], zoom_start=10, tiles="CartoDB Positron")

# Define a color scale
min_noise = combined_gdf["combined_average_noise"].min()
max_noise = combined_gdf["combined_average_noise"].max()
colormap = folium.LinearColormap(
    colors=["blue", "green", "yellow", "orange", "red"], vmin=min_noise, vmax=max_noise
)
colormap.caption = "Combined Average Noise Level"

# Add grid cells to the map
for _, row in combined_gdf.iterrows():
    folium.GeoJson(
        row.geometry,
        style_function=lambda feature, avg_noise=row["combined_average_noise"]: {
            "fillColor": colormap(avg_noise),
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.7,
        },
        tooltip=(
            f"Combined Avg Noise: {row['combined_average_noise']:.2f}<br>"
            f"Combined Max Noise: {row['combined_max_noise']:.2f}"
        ),
    ).add_to(m)

# Add the colormap legend
colormap.add_to(m)

# Step 7: Save and display the map
output_map_path = "combined_noise_heatmap.html"
m.save(output_map_path)
print(f"Map saved to {output_map_path}.")
