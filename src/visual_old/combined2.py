import folium
import geopandas as gpd
import math
from folium import LinearColormap
from shapely.geometry import box

# Function to convert noise levels to decibels
def convert_to_db(noise_map):
    return {key: 10 * math.log10(value) for key, value in noise_map.items()}

# Function to convert decibels to linear scale
def db_to_linear(db_value):
    return 10**(db_value / 10)

# Function to convert linear noise back to decibels
def linear_to_db(linear_value):
    return 10 * math.log10(linear_value)

# Load the GeoJSON files
geojson_path_1 = "/Users/georgemccrae/Desktop/bethygsmall_CONTOURING_NOISE_MAP.geojson"
geojson_path_2 = "/Users/georgemccrae/Desktop/drone-noise-collab/src/recourses/results/experiments/v2_o100_d5_p0_z100geojson.geojson"

gdf_1 = gpd.read_file(geojson_path_1)
gdf_2 = gpd.read_file(geojson_path_2)

# Debugging: Check the range of average_noise values in gdf_2
print("Average Noise Data (gdf_2):")
print(gdf_2['average_noise'].describe())

# Convert noise values to decibels for comparison (example noise map for dataset 1)
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

label_to_db_map = convert_to_db(label_to_noise_map)

# Create the color map (ensure it's defined before use)
colormap = LinearColormap(
    colors=["blue", "green", "yellow", "orange", "red"],
    vmin=min(label_to_db_map.values()),
    vmax=max(label_to_db_map.values()),
    caption="Noise Level (dB)"
)

# Step 1: Create the Base Map for "noisemodelling.html" (Baseline Noise Map)
m1 = folium.Map(location=[51.5074, -0.1278], zoom_start=10, tiles="CartoDB Positron")

# Add GeoJSON Features for Dataset 1 (Noise map)
for _, row in gdf_1.iterrows():
    isolvl = row["ISOLVL"]
    db_value = label_to_db_map.get(isolvl, None)
    
    if db_value is not None:
        folium.GeoJson(
            row.geometry,
            style_function=lambda feature, db_value=db_value: {
                "fillColor": colormap(db_value),
                "color": "black",
                "weight": 0.5,
                "fillOpacity": 0.7,
            },
            tooltip=f"Noise Level (dB): {db_value:.2f}, Label: {row['ISOLABEL']}"
        ).add_to(m1)

# Add the color scale for the baseline noise map
colormap.add_to(m1)

# Save "noisemodelling.html" for the baseline map
m1.save("noisemodelling.html")
print("Baseline Noise Map saved to noisemodelling.html.")

# Step 2: Create the Base Map for "drone_noise.html" (Drone Noise Map)
m2 = folium.Map(location=[51.5074, -0.1278], zoom_start=10, tiles="CartoDB Positron")

# Add GeoJSON Features for Dataset 2 (Drone Noise)
for _, row in gdf_2.iterrows():
    average_noise = row["average_noise"]  # Use 'average_noise' instead of 'ISOLVL'
    db_value = label_to_db_map.get(average_noise, None)  # Get dB value based on 'average_noise'
    
    # Debugging: Print out the average_noise value and the corresponding db_value
    print(f"average_noise: {average_noise}, db_value: {db_value}")

    # Only add the feature if db_value is not None
    if db_value is not None:
        folium.GeoJson(
            row.geometry,
            style_function=lambda feature, db_value=db_value: {
                "fillColor": colormap(db_value),
                "color": "black",
                "weight": 0.5,
                "fillOpacity": 0.7,
            },
            tooltip=f"Noise Level (dB): {db_value:.2f}, Label: {row['ISOLABEL']}"
        ).add_to(m2)

# Add the color scale for the drone noise map
colormap.add_to(m2)

# Save "drone_noise.html" for the drone noise map
m2.save("drone_noise.html")
print("Drone Noise Map saved to drone_noise.html.")

# Step 3: Create the Base Map for "combined_noise.html" (Combined Noise Map)
m3 = folium.Map(location=[51.5074, -0.1278], zoom_start=10, tiles="CartoDB Positron")

# Add GeoJSON Features for both Datasets 1 and 2 (Combined Noise Map)
for _, row in gdf_1.iterrows():
    isolvl_1 = row["ISOLVL"]
    db_value_1 = label_to_db_map.get(isolvl_1, None)

    for _, row_2 in gdf_2.iterrows():
        average_noise_2 = row_2["average_noise"]  # Use 'average_noise' for second dataset
        db_value_2 = label_to_db_map.get(average_noise_2, None)

        # Only proceed if db_value_1 is not None and db_value_2 is not None
        if db_value_1 is not None and db_value_2 is not None:
            # Convert each dataset's dB values to linear scale
            linear_1 = db_to_linear(db_value_1)
            linear_2 = db_to_linear(db_value_2)

            # Add the linear noise values together
            combined_linear = linear_1 + linear_2

            # Convert the summed linear value back to dB
            combined_db = linear_to_db(combined_linear)

            # Add the combined noise to the map
            folium.GeoJson(
                row_2.geometry,
                style_function=lambda feature, db_value=combined_db: {
                    "fillColor": colormap(db_value),
                    "color": "black",
                    "weight": 0.5,
                    "fillOpacity": 0.7,
                },
                tooltip=f"Combined Noise Level (dB): {combined_db:.2f}"
            ).add_to(m3)

# Add the color scale for the combined noise map
colormap.add_to(m3)

# Save "combined_noise.html" for the combined noise map
m3.save("combined_noise.html")
print("Combined Noise Map saved to combined_noise.html.")
