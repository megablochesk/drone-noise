import folium
import geopandas as gpd
from folium import LinearColormap

# Path to your GeoJSON file
geojson_path = "/Users/georgemccrae/Desktop/bethygsmall_CONTOURING_NOISE_MAP.geojson"  # Update with the actual path
gdf = gpd.read_file(geojson_path)
print(f"Loaded GeoJSON with {len(gdf)} features.")

# Ensure the CRS is compatible with folium (WGS84)
gdf = gdf.to_crs("EPSG:4326")
print(f"GeoJSON CRS: {gdf.crs}")

# Step 1: Create a Folium Map
m = folium.Map(location=[51.5074, -0.1278], zoom_start=10, tiles="CartoDB Positron")

# Step 2: Define a Color Scale for ISOLVL
min_isolvl = gdf["ISOLVL"].min()
max_isolvl = gdf["ISOLVL"].max()
colormap = LinearColormap(
    colors=["blue", "green", "yellow", "orange", "red"],
    vmin=min_isolvl,
    vmax=max_isolvl,
    caption="Noise Level (ISOLVL)"
)

# Step 3: Add GeoJSON Features to the Map
for _, row in gdf.iterrows():
    folium.GeoJson(
        row.geometry,
        style_function=lambda feature, isolvl=row["ISOLVL"]: {
            "fillColor": colormap(isolvl),
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.7,
        },
        tooltip=f"Noise Level: {row['ISOLVL']}, Label: {row['ISOLABEL']}"
    ).add_to(m)

# Step 4: Add the Color Scale to the Map
colormap.add_to(m)

# Step 5: Save and Display the Map
output_map_path = "bethygsmall_noise_map.html"
m.save(output_map_path)
print(f"Map saved to {output_map_path}.")
