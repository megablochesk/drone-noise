import folium
import geopandas as gpd
import numpy as np
from shapely.geometry import box

# Step 1: Load GeoJSON File
geojson_path = "/Users/georgemccrae/Desktop/drone-noise-collab/src/recourses/results/experiments/v2_o100_d5_p0_z100geojson.geojson"  # Update with the correct path
gdf = gpd.read_file(geojson_path)
print(f"Loaded GeoJSON with {len(gdf)} features.")

# Step 2: Check and Ensure CRS
gdf = gdf.to_crs("EPSG:4326")  # Ensure it's in WGS84 for Folium compatibility
print(f"GeoJSON CRS: {gdf.crs}")

# Step 3: Create a Grid of Squares
# Use predefined bounds for London
minx, miny, maxx, maxy = -0.5103751, 51.2867602, 0.3340155, 51.6918741
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
# Perform spatial join (points to polygons)
grid = gpd.sjoin(grid, gdf, how="left", predicate="contains")
grid["average_noise"] = grid["average_noise"].fillna(0)  # Fill NaNs with 0
print(grid.head())

# Step 5: Fill Missing Noise Values with Neighbors' Average
# Identify cells with no noise value
no_noise = grid[grid["average_noise"] == 0]
non_zero_noise = grid[grid["average_noise"] > 0]

# Spatial join to find neighbors for each "no noise" square
for idx, no_noise_row in no_noise.iterrows():
    neighbors = non_zero_noise[non_zero_noise.geometry.intersects(no_noise_row.geometry.buffer(grid_size))]
    if not neighbors.empty:
        avg_noise = neighbors["average_noise"].mean()
        grid.loc[idx, "average_noise"] = avg_noise  # Update with average noise

print("Missing noise values filled.")

# Step 6: Debugging
# Print basic stats for noise values
print(grid["average_noise"].describe())

# Step 7: Visualize on Folium Map
# Create Folium map centered on data
m = folium.Map(location=[51.5074, -0.1278], zoom_start=10, tiles="CartoDB Positron")

# Define a color scale
min_noise, max_noise = grid["average_noise"].min(), grid["average_noise"].max()
colormap = folium.LinearColormap(colors=["blue", "green", "yellow", "orange", "red"], vmin=min_noise, vmax=max_noise)
colormap.caption = "Average Noise Level"

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
        tooltip=f"Noise: {row['average_noise']:.2f}"
    ).add_to(m)

# Add the colormap legend
colormap.add_to(m)

# Save and display the map
m.save("visual_1km_folium_squares_noblank.html")
print("Map saved to visual_1km_folium_squares_noblank.html.")
