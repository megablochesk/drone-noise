import folium
import geopandas as gpd
from folium import LinearColormap
import math

# Path to your GeoJSON file
geojson_path = "/Users/georgemccrae/Desktop/bethygsmall_CONTOURING_NOISE_MAP.geojson"  # Update with the actual path
gdf = gpd.read_file(geojson_path)
print(f"Loaded GeoJSON with {len(gdf)} features.")

# Ensure the CRS is compatible with folium (WGS84)
gdf = gdf.to_crs("EPSG:4326")
print(f"GeoJSON CRS: {gdf.crs}")

# Convert label_to_noise_map to decibels
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

# Convert noise levels to decibels (dB)
label_to_db_map = {key: 10 * math.log10(value) for key, value in label_to_noise_map.items()}

# Step 1: Create a Folium Map
m = folium.Map(location=[51.5074, -0.1278], zoom_start=10, tiles="CartoDB Positron")

# Step 2: Define a Color Scale for ISOLVL (now based on the converted dB values)
min_db = min(label_to_db_map.values())
max_db = max(label_to_db_map.values())
colormap = LinearColormap(
    colors=["blue", "green", "yellow", "orange", "red"],
    vmin=min_db,
    vmax=max_db,
    caption="Noise Level (dB)"
)

# Step 3: Add GeoJSON Features to the Map
for _, row in gdf.iterrows():
    # Convert the ISOLVL to dB
    isolvl = row["ISOLVL"]
    db_value = label_to_db_map.get(isolvl, None)  # Default to None if not found
    
    folium.GeoJson(
        row.geometry,
        style_function=lambda feature, db_value=db_value: {
            "fillColor": colormap(db_value),
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.7,
        },
        tooltip=f"Noise Level (dB): {db_value:.2f}, Label: {row['ISOLABEL']}"
    ).add_to(m)

# Step 4: Add the Color Scale to the Map
colormap.add_to(m)

# Step 5: Save and Display the Map
output_map_path = "bethygsmall_noise_map.html"
m.save(output_map_path)
print(f"Map saved to {output_map_path}.")
