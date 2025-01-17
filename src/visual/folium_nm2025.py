# -*- coding: utf-8 -*-

import folium
import geopandas as gpd
import numpy as np
from shapely.geometry import box



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

# Step 1: Load GeoJSON File
geojson_path = "/Users/georgemccrae/Desktop/drone-noise-collab/src/crucial_osm_geojson/2025londonCONTOURING.geojson"
gdf = gpd.read_file(geojson_path)
print(f"Loaded GeoJSON with {len(gdf)} features.")

# Step 2: Check and Ensure CRS
gdf = gdf.to_crs("EPSG:4326")  # Ensure it's in WGS84 for Folium compatibility
print(f"GeoJSON CRS: {gdf.crs}")

# Step 3: Convert ISOLVL to dB using the label_to_noise_map
def isolvl_to_db(isolvl):
    # Map the ISOLVL value to the corresponding noise level using the dictionary
    return label_to_noise_map.get(isolvl, 0)  # Default to 0 if ISOLVL is not found in the dictionary

gdf["average_noise"] = gdf["ISOLVL"].apply(isolvl_to_db)  # Assuming ISOLVL is the column with intensity values

# Step 4: Reduce GeoJSON File Size
# 4a: Simplify geometry
gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.001, preserve_topology=True)

# 4b: Remove unnecessary columns
columns_to_keep = ["geometry", "average_noise"]  # Keep only essential data
gdf = gdf[columns_to_keep]

# 4c: Optional: Downsample by taking every nth row
#gdf = gdf.iloc[::10]  # Adjust 10 to a different number for finer control
#print(f"Reduced GeoJSON now has {len(gdf)} features.")

# Save the smaller GeoJSON
#smaller_geojson_path = "reduced_london_left_nm.geojson"
#gdf.to_file(smaller_geojson_path, driver="GeoJSON")
#print(f"Smaller GeoJSON saved to {smaller_geojson_path}")


# Step 5: Create a Grid of Squares
minx, miny, maxx, maxy = -0.3489999, 51.415, 0.166, 51.624
grid_size = 0.01  # Approx 1km in degrees (adjust if needed)

# Generate grid
grid_cells = []
x = minx
while x < maxx:
    y = miny
    while y < maxy:
        grid_cells.append(box(x, y, x + grid_size, y + grid_size))
        y += grid_size
    x += grid_size

grid = gpd.GeoDataFrame({"geometry": grid_cells}, crs="EPSG:4326")
print(f"Generated grid with {len(grid)} cells.")

# Step 6: Spatial Join to Assign Noise Values to Grid Squares
grid = gpd.sjoin(grid, gdf, how="left", predicate="contains")
grid["average_noise"] = grid["average_noise"].fillna(0)  # Fill NaNs with 0
print(grid.head())

# Step 7: Fill Missing Noise Values with Neighbors' Average
no_noise = grid[grid["average_noise"] == 0]
non_zero_noise = grid[grid["average_noise"] > 0]

for idx, no_noise_row in no_noise.iterrows():
    neighbors = non_zero_noise[non_zero_noise.geometry.intersects(no_noise_row.geometry.buffer(grid_size))]
    if not neighbors.empty:
        avg_noise = neighbors["average_noise"].mean()
        grid.loc[idx, "average_noise"] = avg_noise

print("Missing noise values filled.")

# Step 8: Visualize on Folium Map
m = folium.Map(location=[51.5074, -0.1278], zoom_start=10, tiles="CartoDB Positron")

# Define a global color scale
global_min_noise = 35  # Adjusted minimum value
global_max_noise = 83  # Set to the highest value across both maps

# Create a consistent colormap from white (low noise) to orange (mid noise) to red (high noise)
colormap = folium.LinearColormap(
    colors=["white", "orange", "red"],
    vmin=global_min_noise,
    vmax=global_max_noise
)
colormap.caption = "Average Noise Level (dB)"

# Add the color scale to the map
colormap.add_to(m)

# Add grid cells to the map
for _, row in grid.iterrows():
    folium.GeoJson(
        row.geometry,
        style_function=lambda feature, avg_noise=row["average_noise"]: {
            "fillColor": colormap(avg_noise),
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.7,
        },
        tooltip=f"Noise: {row['average_noise']:.2f} dB"
    ).add_to(m)

# Add the colormap legend
colormap.add_to(m)

# Save and display the map
map_output_path = "visual_1km_nm.html"
m.save(map_output_path)
print(f"Map saved to {map_output_path}.")
