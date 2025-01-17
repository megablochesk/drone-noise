# -*- coding: utf-8 -*-

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

# Coordinates of Tesco warehouses in London
WAREHOUSES = [
    [51.4912, -0.2476],  # Tesco Distribution Centre, Greenford
    [51.5141, 0.2012],  # Tesco Distribution Centre, Dagenham
]

def process_geojson(input_file, output_file, sample_size=100, grid_size=0.01):
    # Step 1: Load GeoJSON File
    gdf = gpd.read_file(input_file)
    print(f"Loaded GeoJSON with {len(gdf)} features.")

    # Step 2: Check and Ensure CRS (assuming the input GeoJSON is not in WGS84)
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")  # Convert to WGS84 (lat/lon)
    print(f"GeoJSON CRS: {gdf.crs}")

    # Step 3: Add 'average_noise' column to the GeoDataFrame (calculate it)
    # Assuming 'noise_column' exists in the dataset and holds the noise values
    if 'noise_column' in gdf.columns:  # Replace 'noise_column' with actual column name
        gdf['average_noise'] = gdf['noise_column'].mean()  # Calculate the average noise across all features
        print("Calculated 'average_noise' for each feature.")
    else:
        print("Noise column not found. Ensure your dataset includes a column with noise values.")
        return

    # Fill missing values in 'average_noise' with 0
    gdf['average_noise'] = gdf['average_noise'].fillna(0)

    # Step 4: Create a Grid of Squares
    minx, miny, maxx, maxy = gdf.total_bounds  # Get the bounds of the GeoDataFrame
    grid_cells = []

    for x0 in np.arange(minx, maxx, grid_size):
        for y0 in np.arange(miny, maxy, grid_size):
            grid_cells.append(box(x0, y0, x0 + grid_size, y0 + grid_size))

    grid = gpd.GeoDataFrame({'geometry': grid_cells})
    grid.crs = 'EPSG:4326'  # Set CRS for the grid
    print(f"Generated grid with {len(grid)} cells.")

    # Step 5: Sample a Smaller Subset of the Grid
    grid_small = grid.sample(n=sample_size, random_state=42)  # Adjust sample size as needed

    # Step 6: Save the Smaller Grid to a New GeoJSON File
    grid_small.to_file(output_file, driver='GeoJSON')
    print(f"Smaller GeoJSON file saved as '{output_file}'")

    # Optional: Plotting the Grid (if you want a visual check)
    map_center = [51.5074, -0.1278]  # London center coordinates
    folium_map = folium.Map(location=map_center, zoom_start=12)
    
    # Add the grid as GeoJSON to the map
    folium.GeoJson(grid_small).add_to(folium_map)
    
    # Add Tesco warehouse markers to the map
    for warehouse in WAREHOUSES:
        folium.Marker(location=warehouse, popup="Tesco Warehouse").add_to(folium_map)
    
    # Save the map as HTML
    folium_map.save("grid_map.html")
    print("Map with grid and warehouses saved as 'grid_map.html'.")

# Run the function with input file, output file, and sample size
input_geojson = "/Users/georgemccrae/Desktop/crucial/london_left_nm.geojson"  # Update with the correct path
output_geojson = "smaller_output.geojson"  # The output file you want to generate
process_geojson(input_geojson, output_geojson, sample_size=100)
