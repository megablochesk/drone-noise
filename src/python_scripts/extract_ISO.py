# THIS IS TO CHECK THE MAPPINGS ARE EXHAUSTIVE FOR ISOLABEL TO DECIBEl

import json
from collections import defaultdict

# Load the GeoJSON file
with open('/Users/georgemccrae/Desktop/bethygsmall_CONTOURING_NOISE_MAP.geojson', 'r') as file:
    data = json.load(file)

# Create a dictionary to map ISOLABEL to noise levels
label_to_noise_map = {
    "< 35": 35,
    "35-40": 37.5,
    "40-45": 42.5,
    "45-50": 47.5,
    "50-55": 52.5,
    "55-60": 57.5,
    "60-65": 62.5,
    "65-70": 67.5,
    "> 70": 75
}

# Create a dictionary to group features by ISOLVL and ISOLABEL
grouped_features = defaultdict(list)

# Group features by ISOLVL and ISOLABEL
for feature in data["features"]:
    isolvl = feature["properties"].get("ISOLVL")
    isolabel = feature["properties"].get("ISOLABEL")
    
    # Get the noise level from the label-to-noise dictionary
    noise_level = label_to_noise_map.get(isolabel, None)  # If label is not found, default to None
    
    # Replace ISOLABEL with the corresponding noise level
    feature["properties"]["ISOLABEL"] = noise_level
    
    # Create a string key from ISOLVL and ISOLABEL
    key = f"{isolvl}_{noise_level}"  # e.g., "0_35"
    
    # Add feature to the corresponding key
    grouped_features[key].append(feature)

# Print the grouped features dictionary
print(dict(grouped_features))
