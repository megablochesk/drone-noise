import pandas as pd

# Define map boundaries
MAP_LEFT = -0.3489999
MAP_RIGHT = 0.166
MAP_TOP = 51.624
MAP_BOTTOM = 51.415

# Load the CSV file
input_file = "drone_delivery_orders.csv"  # Replace with your input CSV file path
output_file = "drone_delivery_orders2.csv"  # Replace with your output CSV file path

# Read the CSV file into a DataFrame
orders = pd.read_csv(input_file)

# Function to check if a coordinate is within the map boundaries
def is_within_bounds(lat, lon):
    return MAP_BOTTOM <= lat <= MAP_TOP and MAP_LEFT <= lon <= MAP_RIGHT

# Filter orders where both start and end coordinates are within the map boundaries
filtered_orders = orders[
    orders.apply(
        lambda row: is_within_bounds(row["Start Latitude"], row["Start Longitude"]) and
                    is_within_bounds(row["End Latitude"], row["End Longitude"]),
        axis=1
    )
]

# Save the filtered orders to a new CSV file
filtered_orders.to_csv(output_file, index=False)

print(f"Filtered orders saved to {output_file}")
