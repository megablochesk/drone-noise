# SOMETHING TO DO WITH LSOA

import geopandas as gpd
import pandas as pd

# Step 1: Load your GeoJSON file into a GeoDataFrame
geo = gpd.read_file("/Users/georgemccrae/Desktop/drone-noise-collab/src/recourses/data/geo/uk.geojson")

# Step 2: Load the CSV that contains the LSOA11CD column
csv_data = pd.read_csv("/Users/georgemccrae/Desktop/drone-noise-collab/src/recourses/data/population/newing_propensity_shop_online.csv")

# Step 3: Extract the list of LSOA11CD values from the CSV
lsoa_codes = csv_data['id'].tolist()

# Step 4: Filter the GeoDataFrame to only include rows with LSOA11CD in the CSV
filtered_geo = geo[geo['LSOA11CD'].isin(lsoa_codes)]

# Step 5: Save the filtered GeoDataFrame back to a GeoJSON file
filtered_geo.to_file("london_lsoa.geojson", driver='GeoJSON')

print("GeoJSON filtered and saved as filtered_lsoa.geojson")
