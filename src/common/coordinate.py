class Coordinate:
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude    # y
        self.longitude = longitude  # x
    
    def __eq__(self, other):
        return self.latitude == other.latitude and self.longitude == other.longitude
    
    def __sub__(self, other):
        return self.latitude - other.latitude, self.longitude - other.longitude
    
    def __str__(self):
        return f"[la={self.latitude}, lo={self.longitude}]"
