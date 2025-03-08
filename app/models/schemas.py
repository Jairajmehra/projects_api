class ViewportParams:
    """Class to handle viewport parameters validation and parsing"""
    def __init__(self, min_lat: float, max_lat: float, min_lng: float, max_lng: float):
        if not all(isinstance(x, (int, float)) for x in [min_lat, max_lat, min_lng, max_lng]):
            raise ValueError("All viewport parameters must be numeric")
        if min_lat > max_lat or min_lng > max_lng:
            raise ValueError("Min values cannot be greater than max values")
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180):
            raise ValueError("Longitude must be between -180 and 180 degrees")
            
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lng = min_lng
        self.max_lng = max_lng

class ProjectCoordinates:
    """Class to handle project coordinate parsing and validation"""
    def __init__(self, coord_str: str):
        if not coord_str or not isinstance(coord_str, str):
            raise ValueError("Invalid coordinates string")
            
        try:
            lat_str, lng_str = coord_str.split(",")
            self.lat = float(lat_str.strip())
            self.lng = float(lng_str.strip())
            
            if not (-90 <= self.lat <= 90):
                raise ValueError("Latitude must be between -90 and 90 degrees")
            if not (-180 <= self.lng <= 180):
                raise ValueError("Longitude must be between -180 and 180 degrees")
        except Exception as e:
            raise ValueError(f"Failed to parse coordinates: {str(e)}")
