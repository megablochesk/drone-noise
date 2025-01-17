# I HAD 600MB geojson which crashes to this pulls out a sample

# Open your GeoJSON file and print the first 150 lines
file_path = "/Users/georgemccrae/Desktop/crucial/london_left_nm.geojson"  # Update this with your file path

# with open(file_path, 'r') as file:
#     # Read the first 150 lines
#     for _ in range(150):
#         print(file.readline().strip())
        
        
# chunk_size = 150

# with open(file_path, 'r') as file:
#     lines = file.readlines()
#     for i in range(0, len(lines), chunk_size):
#         print(''.join(lines[i:i + chunk_size]))
#         input("Press Enter to continue...")  # Pause after each chunk


import json

# Load a sample of the GeoJSON file and save it to a new file
def load_sample_and_save(file_path, output_file_path, num_features=10):
    with open(file_path, 'r') as f:
        geojson_data = json.load(f)
        
    # Extract a small subset of features
    sample_features = geojson_data['features'][:num_features]
    
    # Create a new GeoJSON structure with the sample
    sample_geojson = {
        "type": "FeatureCollection",
        "features": sample_features
    }
    
    # Save the sample data to a new file
    with open(output_file_path, 'w') as out_file:
        json.dump(sample_geojson, out_file, indent=2)

# Specify file paths
input_file_path = file_path # Change this to your original file path
output_file_path = 'sample_output.geojson'  # The file where the sample will be saved

# Load a sample and save it to a new file
load_sample_and_save(input_file_path, output_file_path)

print(f"Sample saved to {output_file_path}")
