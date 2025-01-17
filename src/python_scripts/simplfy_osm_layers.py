# code below helps find the osmium command in your system's PATH.
# it essential makes a .osm.pbf file smaller and more managable



# import subprocess

# input_file = "/Users/georgemccrae/Desktop/right_half.osm.pbf"
# lines_output = "/Users/georgemccrae/Desktop/lines_output.osm.pbf"

# # Run osmium command
# subprocess.run(["/opt/homebrew/bin/osmium", "tags-filter", input_file, "w/highway", "-o", lines_output])

    
import os
import subprocess

# Update with the correct path to your input .osm.pbf file
input_file = "/Users/georgemccrae/Desktop/london_new.osm.pbf"
lines_output = "/Users/georgemccrae/Desktop/lines.osm.pbf"  # Output for lines
multipolygons_output = "/Users/georgemccrae/Desktop/multipolygons.osm.pbf"  # Output for multipolygons
buildings_output = "/Users/georgemccrae/Desktop/buildings.osm.pbf"  # Output for buildings
combined_output = "/Users/georgemccrae/Desktop/london_simple.osm.pbf"  # Combined output

# Function to extract and filter OSM data using osmium (you can customize filters)
def extract_osm_layers(input_file, output_file, filter_tags=None):
    try:
        command = ["/opt/homebrew/bin/osmium", "tags-filter", input_file]
        
        # Apply filters if provided (e.g., "w/highway", "w/building", or "w/multipolygon")
        if filter_tags:
            command.extend(filter_tags)

        # Add --overwrite to ensure it overwrites existing files
        command.extend(["--overwrite", "-o", output_file])
        subprocess.run(command, check=True)
        print(f"Extracted layers to {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error during osmium command execution: {e}")

# Function to combine OSM layers into one .osm.pbf file
def combine_layers(input_files, combined_output):
    try:
        command = ["/opt/homebrew/bin/osmium", "merge"] + input_files + ["--overwrite", "-o", combined_output]
        subprocess.run(command, check=True)
        print(f"Combined layers into {combined_output}")
    except subprocess.CalledProcessError as e:
        print(f"Error during combining layers: {e}")

# Main processing
if __name__ == "__main__":
    # Step 1: Extract lines layer from OSM data
    extract_osm_layers(input_file, lines_output, filter_tags=["w/highway"])

    # Step 2: Extract multipolygons layer from OSM data
    extract_osm_layers(input_file, multipolygons_output, filter_tags=["w/multipolygon"])

    # Step 3: Extract buildings layer from OSM data
    extract_osm_layers(input_file, buildings_output, filter_tags=["w/building"])

    # Step 4: Combine layers into one .osm.pbf file
    input_files = [lines_output, multipolygons_output, buildings_output]  # Files to combine
    combine_layers(input_files, combined_output)
