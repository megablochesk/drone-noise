# -*- coding: utf-8 -*-

import folium
import geopandas as gpd
import numpy as np
from shapely.geometry import box

# CHANGE THIS IF WAREHOUSES CHANGE LOCATION OR LONDON BOUNDS ON LINE 32
LONDON_WAREHOUSES = [
    [51.4303, -0.1276],  # Streatham
    [51.4613, -0.3037],  # Richmond
    [51.5380, -0.1022],  # Islington
    [51.4875, -0.0595]    # Bermondsey
]

# Step 1: Load GeoJSON File
#geojson_path = "/Users/georgemccrae/Desktop/drone-noise-collab/src/recourses/results/experiments/v2_o500_d200_p0_z100geojson.geojson"  
geojson_path = "/Users/georgemccrae/Desktop/drone-noise-collab/src/recourses/results/experiments/v2_o1000_d200_p0_z100geojson.geojson"  


gdf = gpd.read_file(geojson_path)
print(f"Loaded GeoJSON with {len(gdf)} features.")

# Step 2: Check and Ensure CRS
gdf = gdf.to_crs("EPSG:4326")  # Ensure it's in WGS84 for Folium compatibility
print(f"GeoJSON CRS: {gdf.crs}")

# Step 3: Create a Grid of Squares
# Use predefined bounds for London
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

# Step 4: Spatial Join to Assign Noise Values to Grid Squares
grid = gpd.sjoin(grid, gdf, how="left", predicate="contains")
grid["average_noise"] = grid["average_noise"].fillna(0)  # Fill NaNs with 0
print(grid.head())

# Step 5: Fill Missing Noise Values with Neighbors' Average
no_noise = grid[grid["average_noise"] == 0]
non_zero_noise = grid[grid["average_noise"] > 0]

for idx, no_noise_row in no_noise.iterrows():
    neighbors = non_zero_noise[non_zero_noise.geometry.intersects(no_noise_row.geometry.buffer(grid_size))]
    if not neighbors.empty:
        avg_noise = neighbors["average_noise"].mean()
        grid.loc[idx, "average_noise"] = avg_noise

print("Missing noise values filled.")

# Step 6: Set all noise values below 35 to 35
grid["average_noise"] = grid["average_noise"].apply(lambda x: max(x, 35))
print("Noise levels below 35 set to 35.")

# Step 7: Debugging
print(grid["average_noise"].describe())

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




# Add warehouse markers to the map
for warehouse in LONDON_WAREHOUSES:
    folium.Marker(
        location=warehouse,
        popup="Tesco Warehouse",
        icon=folium.Icon(color="blue", icon="info-sign"),
    ).add_to(m)
    
# Save and display the map
m.save("visual_1km_drone.html")

print("Map saved to visual_1km_drone.html.")
