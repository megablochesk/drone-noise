import geopandas as gpd
import folium
from folium.plugins import HeatMap

# Load the GeoJSON file into a GeoDataFrame
geojson_path = "/Users/georgemccrae/Desktop/drone-noise-collab/src/recourses/results/experiments/v2_o100_d5_p0_z100geojson.geojson"  
gdf = gpd.read_file(geojson_path)

# Ensure the GeoDataFrame has a geometry column
if "geometry" not in gdf.columns:
    raise ValueError("GeoDataFrame does not have a geometry column.")

# Create base map centered around London
m = folium.Map(location=[51.5, -0.1], zoom_start=10, tiles="CartoDB Positron")

# Extract points and noise values
points = []
for _, row in gdf.iterrows():
    if row.geometry.type == "Point":  # Ensure the geometry type is Point
        points.append([row.geometry.y, row.geometry.x, row["average_noise"]])
    else:
        print(f"Non-point geometry found: {row.geometry.type}")

# Add heat map layer if points are available
if points:
    HeatMap(points, min_opacity=0.2, radius=15, blur=10, max_zoom=1).add_to(m)
else:
    print("No valid points found to add to the heat map.")

# Save the map as an HTML file
output_path = "visual_1km_folium.html"  # Update path
m.save(output_path)
print(f"Interactive map saved to {output_path}")

# To display the map, return the map object (useful in Jupyter or IPython)
m


"""

Specifies the initial center of the map.
[latitude, longitude] format, where:
51.5 is the latitude (around central London).
-0.1 is the longitude.
zoom_start=10:

Sets the initial zoom level when the map loads.
A value of 10 provides a city-wide view. You can adjust this to a smaller or larger number:
Higher values (e.g., 12-15) zoom in closer.
Lower values (e.g., 5-8) zoom out for a broader perspective.
tiles="CartoDB Positron":

Specifies the tile style for the map's background.
"CartoDB Positron" is a minimalist, modern, and light-colored tile set that works well for overlays like heat maps.
Alternatives include:
"OpenStreetMap": A standard open-source map style.
"Stamen Toner": High-contrast black-and-white tiles.
"Stamen Terrain": Terrain-focused tiles.
"CartoDB Dark_Matter": A dark background for nighttime-style visualizations.
"""



