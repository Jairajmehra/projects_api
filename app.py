from flask import Flask, jsonify, request
from flask_cors import CORS
from pyairtable import Api
import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
# Load configuration from environment variables
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')
BASE_ID = os.environ.get('BASE_ID')
RESIDENTIAL_TABLE_NAME = os.environ.get('RESIDENTIAL_TABLE_NAME')
COMMERCIAL_RESIDENTIAL_TABLE_NAME = os.environ.get('COMMERCIAL_TABLE_NAME')
# Validate required environment variables
if not all([AIRTABLE_API_KEY, BASE_ID, RESIDENTIAL_TABLE_NAME, COMMERCIAL_RESIDENTIAL_TABLE_NAME]):
    logger.error("Missing required environment variables. Please check your app.yaml configuration.")
    raise ValueError("Missing required environment variables: AIRTABLE_API_KEY, BASE_ID, RESIDENTIAL_TABLE_NAME, or COMMERCIAL_RESIDENTIAL_TABLE_NAME")

# Initialize Airtable
try:
    api = Api(AIRTABLE_API_KEY)
    table = api.table(BASE_ID, RESIDENTIAL_TABLE_NAME)
    commercial_table = api.table(BASE_ID, COMMERCIAL_RESIDENTIAL_TABLE_NAME)
    logger.info("Airtable connection initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Airtable connection: {str(e)}")
    raise

# Global cache for projects
RESIDENTIAL_PROJECTS_CACHE = []
COMMERCIAL_PROJECTS_CACHE = []
COMMERCIAL_PROJECTS_NAME_INDEX = {}
RESIDENTIAL_PROJECTS_NAME_INDEX = {}

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

def is_point_in_viewport(coords: ProjectCoordinates, viewport: ViewportParams) -> bool:
    """Check if a point falls within the viewport"""
    return (viewport.min_lat <= coords.lat <= viewport.max_lat and 
            viewport.min_lng <= coords.lng <= viewport.max_lng)

def filter_projects_by_viewport(projects: list, viewport: ViewportParams) -> list:
    """Filter projects based on viewport boundaries"""
    filtered_projects = []
    
    for project in projects:
        try:
            # Try both coordinate field names
            coord_str = project.get("coordinates", "") or project.get("Coordinates", "")
            if not coord_str:
                continue
                
            coords = ProjectCoordinates(coord_str)
            if is_point_in_viewport(coords, viewport):
                filtered_projects.append(project)
        except ValueError:
            # Skip projects with invalid coordinates
            continue
            
    return filtered_projects

def format_residential_project(record):
 """Format a single commercial project record"""
 try:
        fields = record["fields"]
        brochure_url = ""
        cover_photo_url = ""
        certificate_url = ""
        
        if "Brochure Storage URL" in fields and fields["Brochure Storage URL"]:
            brochure_url = fields["Brochure Storage URL"]

        if "Cover Photo Storage URL" in fields and fields["Cover Photo Storage URL"]:
            cover_photo_url = fields["Cover Photo Storage URL"]

        if "Certificate Storage URL" in fields and fields["Certificate Storage URL"]:
            certificate_url = fields["Certificate Storage URL"]

        if fields.get("Photos"):
            cover_photo_url = fields.get("Photos").split(",")[0]

        return {
            "rera": fields.get("RERA Number", ""),
            "name": fields.get("Project Name", ""),
            "brochureLink": brochure_url,
            "coverPhotoLink": cover_photo_url,
            "certificateLink": certificate_url,
            "promoterName": fields.get("Promoter Name", ""),
            "mobile": fields.get("Mobile", ""),
            "projectType": fields.get("Project Type", ""),
            "startDate": fields.get("Project Start Date", ""),
            "endDate": fields.get("Project End Date", ""),
            "projectLandArea": fields.get("Land Area (Sqyrds)",""),
            "projectAddress": fields.get("Project Address",""),
            "projectStatus": fields.get("Project Status",""),
            "totalUnits": fields.get("Total Units",""),
            "totalUnitsAvailable": fields.get("Available Units",""),
            "numberOfTowers": fields.get("Total No Of Towers",""),
            "planPassingAuthority": fields.get("Plan Passing Authority",""),
            "coordinates": fields.get("coordinates",""),
            "photos": fields.get("Photos",""),
            "price": fields.get("Price",""),
            "bhk": fields.get("BHK",""),
            "planPassingAuthority": fields.get("Plan Passing Authority",""),
            "localityNames": fields.get("Name (from Locality)",""),
            "configuration": fields.get("Configuration",""),
        }
 except Exception as e:
        logger.error(f"Error formatting commercial project record: {str(e)}")
        logger.error(f"Record that caused error: {record}")
        return None

def format_commercial_project(record):
    """Format a single commercial project record"""
    try:
        fields = record["fields"]
        brochure_url = ""
        cover_photo_url = ""
        certificate_url = ""
        
        if "Brochure Storage URL" in fields and fields["Brochure Storage URL"]:
            brochure_url = fields["Brochure Storage URL"]

        if "Cover Photo Storage URL" in fields and fields["Cover Photo Storage URL"]:
            cover_photo_url = fields["Cover Photo Storage URL"]

        if "Certificate Storage URL" in fields and fields["Certificate Storage URL"]:
            certificate_url = fields["Certificate Storage URL"]

        return {
            "rera": fields.get("RERA Number", ""),
            "name": fields.get("Project Name", ""),
            "brochureLink": brochure_url,
            "coverPhotoLink": cover_photo_url,
            "certificateLink": certificate_url,
            "promoterName": fields.get("Promoter Name", ""),
            "email": fields.get("Email Id", ""),
            "promoterPhone": fields.get("Promoter Phone", ""),
            "promoterAddress": fields.get("Promoter Address", ""),
            "mobile": fields.get("Mobile", ""),
            "projectType": fields.get("Project Type", ""),
            "district": fields.get("District", ""),
            "approvedDate": fields.get("Approved on", ""),
            "originalEndDate": fields.get("Project Original End Date",""),
            "extendedEndDate": fields.get("Project Extended End Date",""),
            "projectLandArea": fields.get("Project Land Area (Sq Mtrs)",""),
            "averageCarpetArea": fields.get("Average Carpet Area of Units (Sq Mtrs)",""),
            "totalOpenArea": fields.get("Total Open Area (Sq Mtrs)",""),
            "totalCoveredArea": fields.get("Total Covered Area (Sq Mtrs)",""),
            "projectAddress": fields.get("Project Address",""),
            "aboutProject": fields.get("About Property",""),
            "startDate": fields.get("Project Start Date",""),
            "endDate": fields.get("Project End Date",""),
            "projectStatus": fields.get("Project Status",""),
            "type": fields.get("Type",""),
            "totalUnits": fields.get("Total Units",""),
            "totalUnitsAvailable": fields.get("Available Units",""),
            "numberOfTowers": fields.get("Total No Of Towers",""),
            "planPassingAuthority": fields.get("Plan Passing Authority",""),
            "Coordinates": fields.get("Coordinates",""),
            
        }
    except Exception as e:
        logger.error(f"Error formatting commercial project record: {str(e)}")
        logger.error(f"Record that caused error: {record}")
        return None

def build_commercial_projects_index():
    """Build an in-memory index for fast project name searches"""
    global COMMERCIAL_PROJECTS_NAME_INDEX
    COMMERCIAL_PROJECTS_NAME_INDEX = {}
    
    for idx, project in enumerate(COMMERCIAL_PROJECTS_CACHE):
        if project and project.get('name'):
            # Create normalized key for case-insensitive search
            name_key = project['name'].lower()
            if name_key not in COMMERCIAL_PROJECTS_NAME_INDEX:
                COMMERCIAL_PROJECTS_NAME_INDEX[name_key] = []
            COMMERCIAL_PROJECTS_NAME_INDEX[name_key].append(idx)

def build_residential_projects_index():
    """Build an in-memory index for fast residential project name searches"""
    global RESIDENTIAL_PROJECTS_NAME_INDEX
    RESIDENTIAL_PROJECTS_NAME_INDEX = {}
    
    for idx, project in enumerate(RESIDENTIAL_PROJECTS_CACHE):
        if project and project.get('name'):
            # Create normalized key for case-insensitive search
            name_key = project['name'].lower()
            if name_key not in RESIDENTIAL_PROJECTS_NAME_INDEX:
                RESIDENTIAL_PROJECTS_NAME_INDEX[name_key] = []
            RESIDENTIAL_PROJECTS_NAME_INDEX[name_key].append(idx)

def init_cache():
    """Initialize the cache without using Flask context"""
    global RESIDENTIAL_PROJECTS_CACHE
    global COMMERCIAL_PROJECTS_CACHE
    try:
        records = table.all(view="Production")
        commercial_records = commercial_table.all()
        RESIDENTIAL_PROJECTS_CACHE = [format_residential_project(record) for record in records]
        print(RESIDENTIAL_PROJECTS_CACHE[0])
        COMMERCIAL_PROJECTS_CACHE = [format_commercial_project(record) for record in commercial_records]
        build_commercial_projects_index()
        build_residential_projects_index()
        print(f"Cache initialized successfully with {len(RESIDENTIAL_PROJECTS_CACHE)} residential projects and {len(COMMERCIAL_PROJECTS_CACHE)} commercial projects")
    except Exception as e:
        logger.error(f"Error initializing cache: {str(e)}")
        RESIDENTIAL_PROJECTS_CACHE = []
        COMMERCIAL_PROJECTS_CACHE = []

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "cache_size": len(RESIDENTIAL_PROJECTS_CACHE)
    })

@app.route("/update_cache", methods=["GET"])
def update_cache():
    """Endpoint to manually update the cache"""
    try:
        init_cache()
        return jsonify({
            "status": "success",
            "message": "Cache updated successfully",
            "total_projects": len(RESIDENTIAL_PROJECTS_CACHE)
        })
    except Exception as e:
        logger.error(f"Cache update failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/commercial_projects", methods=["GET"])
def get_commercial_projects():
    """
    Get commercial projects with optional viewport filtering and pagination.
    
    Query params:
    - Regular pagination: limit, offset
    - Viewport filtering: minLat, maxLat, minLng, maxLng (all optional)
    """
    try:
        # If cache is empty, initialize it
        if not COMMERCIAL_PROJECTS_CACHE:
            init_cache()
            
        # Parse pagination parameters
        #limit = min(500, max(1, int(request.args.get("limit", 12))))
        limit = max(1, int(request.args.get("limit", 12)))
        offset = max(0, int(request.args.get("offset", 0)))
        
        # Check if viewport parameters are provided
        has_viewport = all(request.args.get(param) for param in ["minLat", "maxLat", "minLng", "maxLng"])
        
        if has_viewport:
            # Use viewport filtering
            viewport_params = {
                "minLat": request.args.get("minLat"),
                "maxLat": request.args.get("maxLat"),
                "minLng": request.args.get("minLng"),
                "maxLng": request.args.get("maxLng")
            }
            
            pagination_params = {
                "page": 1,  # Always use page 1 since we're using offset
                "limit": limit,
                "offset": offset
            }
            
            result = get_projects_in_viewport(
                COMMERCIAL_PROJECTS_CACHE,
                viewport_params,
                pagination_params
            )
            return jsonify(result)
        else:
            # Regular pagination without viewport
            start = offset
            end = offset + limit
            
            # Check if offset exceeds total available data
            if offset >= len(COMMERCIAL_PROJECTS_CACHE):
                return jsonify({
                    "status": "success",
                    "projects": [],
                    "total": len(COMMERCIAL_PROJECTS_CACHE),
                    "limit": limit,
                    "offset": offset,
                    "has_more": False,
                    "message": "Offset exceeds available data"
                })
            
            return jsonify({
                "status": "success",
                "projects": COMMERCIAL_PROJECTS_CACHE[start:end],
                "total": len(COMMERCIAL_PROJECTS_CACHE),
                "limit": limit,
                "offset": offset,
                "has_more": end < len(COMMERCIAL_PROJECTS_CACHE)
            })
            
    except ValueError as e:
        logger.error(f"Invalid parameters: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error fetching commercial projects: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

@app.route("/residential_projects", methods=["GET"])
def get_residential_projects():
    """
    Get residential projects with optional viewport filtering and pagination.
    
    Query params:
    - Regular pagination: limit, offset
    - Viewport filtering: minLat, maxLat, minLng, maxLng (all optional)
    """
    try:
        # If cache is empty, initialize it
        if not RESIDENTIAL_PROJECTS_CACHE:
            init_cache()
            
        # Parse pagination parameters
        #limit = min(500, max(1, int(request.args.get("limit", 12))))
        limit = max(1, int(request.args.get("limit", 12)))
        offset = max(0, int(request.args.get("offset", 0)))
        
        # Check if viewport parameters are provided
        has_viewport = all(request.args.get(param) for param in ["minLat", "maxLat", "minLng", "maxLng"])
        
        if has_viewport:
            # Use viewport filtering
            viewport_params = {
                "minLat": request.args.get("minLat"),
                "maxLat": request.args.get("maxLat"),
                "minLng": request.args.get("minLng"),
                "maxLng": request.args.get("maxLng")
            }
            
            pagination_params = {
                "page": 1,  # Always use page 1 since we're using offset
                "limit": limit,
                "offset": offset
            }
            
            result = get_projects_in_viewport(
                RESIDENTIAL_PROJECTS_CACHE,
                viewport_params,
                pagination_params
            )
            return jsonify(result)
        else:
            # Regular pagination without viewport
            start = offset
            end = offset + limit
            
            # Check if offset exceeds total available data
            if offset >= len(RESIDENTIAL_PROJECTS_CACHE):
                return jsonify({
                    "status": "success",
                    "projects": [],
                    "total": len(RESIDENTIAL_PROJECTS_CACHE),
                    "limit": limit,
                    "offset": offset,
                    "has_more": False,
                    "message": "Offset exceeds available data"
                })
            
            return jsonify({
                "status": "success",
                "projects": RESIDENTIAL_PROJECTS_CACHE[start:end],
                "total": len(RESIDENTIAL_PROJECTS_CACHE),
                "limit": limit,
                "offset": offset,
                "has_more": end < len(RESIDENTIAL_PROJECTS_CACHE)
            })
            
    except ValueError as e:
        logger.error(f"Invalid parameters: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error fetching residential projects: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

@app.route("/search_commercial_projects", methods=["GET"])
def search_commercial_projects():
    """Search commercial projects by name with pagination and offset"""
    try:
        search_term = request.args.get("q", "").lower().strip()
        limit = min(100, max(1, int(request.args.get("limit", 12))))
        offset = max(0, int(request.args.get("offset", 0)))
        
        if not search_term:
            return jsonify({
                "status": "error",
                "message": "Search term is required"
            }), 400

        # Find matching projects
        matching_indices = set()
        for name_key in COMMERCIAL_PROJECTS_NAME_INDEX:
            if name_key.startswith(search_term):
                matching_indices.update(COMMERCIAL_PROJECTS_NAME_INDEX[name_key])
        
        # Convert to list and sort
        matching_projects = [COMMERCIAL_PROJECTS_CACHE[idx] for idx in matching_indices]
        matching_projects.sort(key=lambda x: x['name'].lower())
        
        # Apply offset and limit
        start = offset
        end = offset + limit
        
        # Check if offset exceeds total available data
        if offset >= len(matching_projects):
            return jsonify({
                "status": "success",
                "projects": [],
                "total": len(matching_projects),
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "message": "Offset exceeds available data"
            })
        
        return jsonify({
            "status": "success",
            "projects": matching_projects[start:end],
            "total": len(matching_projects),
            "limit": limit,
            "offset": offset,
            "has_more": end < len(matching_projects)
        })
        
    except ValueError as e:
        logger.error(f"Invalid search parameters: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Invalid parameters for limit or offset"
        }), 400
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

@app.route("/search_residential_projects", methods=["GET"])
def search_residential_projects():
    """Search residential projects by name with pagination and offset"""
    try:
        search_term = request.args.get("q", "").lower().strip()
        limit = min(100, max(1, int(request.args.get("limit", 12))))
        offset = max(0, int(request.args.get("offset", 0)))
        
        if not search_term:
            return jsonify({
                "status": "error",
                "message": "Search term is required"
            }), 400

        # Find matching projects
        matching_indices = set()
        for name_key in RESIDENTIAL_PROJECTS_NAME_INDEX:
            if name_key.startswith(search_term):
                matching_indices.update(RESIDENTIAL_PROJECTS_NAME_INDEX[name_key])
        
        # Convert to list and sort
        matching_projects = [RESIDENTIAL_PROJECTS_CACHE[idx] for idx in matching_indices]
        matching_projects.sort(key=lambda x: x['name'].lower())
        
        # Apply offset and limit
        start = offset
        end = offset + limit
        
        # Check if offset exceeds total available data
        if offset >= len(matching_projects):
            return jsonify({
                "status": "success",
                "projects": [],
                "total": len(matching_projects),
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "message": "Offset exceeds available data"
            })
        
        return jsonify({
            "status": "success",
            "projects": matching_projects[start:end],
            "total": len(matching_projects),
            "limit": limit,
            "offset": offset,
            "has_more": end < len(matching_projects)
        })
        
    except ValueError as e:
        logger.error(f"Invalid search parameters: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Invalid parameters for limit or offset"
        }), 400
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

def get_projects_in_viewport(projects_cache: list, viewport_params: dict, pagination_params: dict):
    """
    Reusable function to get projects within a viewport with pagination
    
    Args:
        projects_cache: List of projects to filter
        viewport_params: Dict containing minLat, maxLat, minLng, maxLng
        pagination_params: Dict containing page, limit, offset
    
    Returns:
        Dict containing filtered and paginated results with metadata
    """
    try:
        # Parse and validate viewport parameters
        viewport = ViewportParams(
            min_lat=float(viewport_params.get("minLat", 0)),
            max_lat=float(viewport_params.get("maxLat", 0)),
            min_lng=float(viewport_params.get("minLng", 0)),
            max_lng=float(viewport_params.get("maxLng", 0))
        )
    except ValueError as e:
        raise ValueError(f"Invalid viewport parameters: {str(e)}")

    # Filter projects by viewport
    in_viewport_projects = filter_projects_by_viewport(projects_cache, viewport)
    
    # Parse pagination parameters
    page = max(1, int(pagination_params.get("page", 1)))
    limit = min(500, max(1, int(pagination_params.get("limit", 12))))
    offset = max(0, int(pagination_params.get("offset", 0)))
    
    # Apply pagination
    start = ((page - 1) * limit) + offset
    end = start + limit
    
    # Prepare response
    response = {
        "status": "success",
        "total": len(in_viewport_projects),
        "page": page,
        "limit": limit,
        "offset": offset,
        "viewport": {
            "minLat": viewport.min_lat,
            "maxLat": viewport.max_lat,
            "minLng": viewport.min_lng,
            "maxLng": viewport.max_lng
        }
    }
    
    # Handle pagination overflow
    if start >= len(in_viewport_projects):
        response.update({
            "projects": [],
            "has_more": False,
            "message": "Page number exceeds available data for this viewport"
        })
    else:
        response.update({
            "projects": in_viewport_projects[start:end],
            "has_more": end < len(in_viewport_projects)
        })
    
    return response

if __name__ == "__main__":
    # Initialize cache at startup
    init_cache()
    # Development server
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
    
