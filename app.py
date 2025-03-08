from flask import Flask, jsonify, request, g
from flask_cors import CORS
from pyairtable import Api
import os
from dotenv import load_dotenv
import logging
import time
from typing import Union
import threading

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
RESIDENTIAL_TABLE_NAME = os.environ.get('RESIDENTIAL_TABLE_NAME') # projects_residential
COMMERCIAL_TABLE_NAME = os.environ.get('COMMERCIAL_TABLE_NAME') # projects_commercial
INVENTORY_BASE_ID = os.environ.get('INVENTORY_BASE_ID')
RESIDENTIAL_PROPERTIES_TABLE_ID = os.environ.get('RESIDENTIAL_RENT_PROPERTIES_TABLE_ID') # residential_inventory
LOCALITIES_TABLE_ID = os.environ.get('LOCALITIES_TABLE_ID')
# Validate required environment variables
if not all([AIRTABLE_API_KEY, BASE_ID, RESIDENTIAL_TABLE_NAME, COMMERCIAL_TABLE_NAME]):
    logger.error("Missing required environment variables. Please check your app.yaml configuration.")
    raise ValueError("Missing required environment variables: AIRTABLE_API_KEY, BASE_ID, RESIDENTIAL_TABLE_NAME, or COMMERCIAL_TABLE_NAME")

# Initialize Airtable
try:
    api = Api(AIRTABLE_API_KEY)
    localities_table = api.table(INVENTORY_BASE_ID, LOCALITIES_TABLE_ID)
    projects_residential_table = api.table(INVENTORY_BASE_ID, "residential projects")
    projects_commercial_table = api.table(BASE_ID, COMMERCIAL_TABLE_NAME)
    residential_inventory_table = api.table(INVENTORY_BASE_ID, RESIDENTIAL_PROPERTIES_TABLE_ID)
    logger.info("Airtable connection initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Airtable connection: {str(e)}")
    raise

# Global cache for projects
RESIDENTIAL_PROJECTS_CACHE = []
COMMERCIAL_PROJECTS_CACHE = []
RESIDENTIAL_PROPERTIES_CACHE = []
LOCALITIES_CACHE = []
COMMERCIAL_PROJECTS_NAME_INDEX = {}
RESIDENTIAL_PROJECTS_NAME_INDEX = {}

# Global flag to track initialization status
CACHE_INITIALIZATION_STARTED = False
CACHE_INITIALIZED = False

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
            "airtable_id": record["id"]
        }
 except Exception as e:
        logger.error(f"Error formatting commercial project record: {str(e)}")
        logger.error(f"Record that caused error: {record}")
        return None
 
def format_locality(record):
    """Format a single locality record"""
    try:
        fields = record["fields"]
        return {
            "name": fields.get("Name", ""),
        }
    except Exception as e:
        logger.error(f"Error formatting locality record: {str(e)}")
        logger.error(f"Record that caused error: {record}")
        return None

def get_linked_project_photos(rera_number: str):
    """Get photos from the linked project"""
    print(f"Searching for linked project with rera number {rera_number}")
    for project in RESIDENTIAL_PROJECTS_CACHE:
        if project.get("rera") == rera_number[0]:
            photos =  project.get("photos", "")
            print(f"Found linked project {project.get('name')} with photos {photos}")
            return photos.split(",")
    return None

def format_residential_property(record):
    """Format a single residential property record"""
    try:
        fields = record["fields"]
        photos = fields.get("Photos", "")
        print(f"Residential property Photos: {photos}")
        linked_project_rera = fields.get("RERA Number (from residential projects)", "")
        if (not photos or photos == "" or photos == []) and linked_project_rera:
            project_photos = get_linked_project_photos(linked_project_rera)
            if project_photos:
                photos = project_photos[0]

        return {
            "name": fields.get("Property Name", ""),
            "price": fields.get("Price", ""),
            "transactionType": fields.get("Transaction Type", ""),
            "locality": fields.get("Name (from Localities)", ""),
            "photos": photos,
            "size": fields.get("Size in Sqfts", ""),
            "propertyType": fields.get("Property Type", ""),
            "coordinates": fields.get("Property Coordinates", ""),
            "landmark": fields.get("Landmark", ""),
            "condition": fields.get("Condition", ""),
            "date": fields.get("Date", ""),
            "bhk": fields.get("BHK", ""),
            "airtable_id": record["id"],
            "linked_project_rera": fields.get("RERA Number (from residential projects)", "")
        }
    except Exception as e:
        logger.error(f"Error formatting residential property record: {str(e)}")
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
    global RESIDENTIAL_PROPERTIES_CACHE
    global LOCALITIES_CACHE
    global CACHE_INITIALIZED
    
    try:
        records = projects_residential_table.all(view="Production")
        print(f"Residential projects fetched successfully with {len(records)} records")
        time.sleep(10)
        commercial_records = projects_commercial_table.all()
        print(f"Commercial projects fetched successfully with {len(commercial_records)} records")
        time.sleep(11)
        residential_inventory_records = residential_inventory_table.all(view="Production")
        print(f"Residential properties fetched successfully with {len(residential_inventory_records)} records")
        time.sleep(12)
        localities_records = localities_table.all()
        print(f"Localities fetched successfully with {len(localities_records)} records")
        time.sleep(13)
        RESIDENTIAL_PROJECTS_CACHE = [format_residential_project(record) for record in records]
        COMMERCIAL_PROJECTS_CACHE = [format_commercial_project(record) for record in commercial_records]
        RESIDENTIAL_PROPERTIES_CACHE = [format_residential_property(record) for record in residential_inventory_records]
        LOCALITIES_CACHE = [format_locality(record) for record in localities_records]
        print('-'*100)
        build_commercial_projects_index()
        build_residential_projects_index()
        print(f"Cache initialized successfully with {len(RESIDENTIAL_PROPERTIES_CACHE)} residential properties")
        
        # Set memory flag instead of file flag
        CACHE_INITIALIZED = True
    except Exception as e:
        logger.error(f"Error initializing cache: {str(e)}")
        RESIDENTIAL_PROJECTS_CACHE = []
        COMMERCIAL_PROJECTS_CACHE = []
        RESIDENTIAL_PROPERTIES_CACHE = []
        LOCALITIES_CACHE = []

def ensure_cache_initialized():
    """Ensure cache is initialized without blocking requests"""
    global CACHE_INITIALIZATION_STARTED, CACHE_INITIALIZED
    
    # If already initialized, do nothing
    if CACHE_INITIALIZED:
        return True
    
    # If initialization is in progress, just return
    if CACHE_INITIALIZATION_STARTED:
        return False
    
    # Start initialization in a background thread
    CACHE_INITIALIZATION_STARTED = True
    threading.Thread(target=_initialize_cache_in_background).start()
    return False

def _initialize_cache_in_background():
    """Initialize cache in background thread"""
    global CACHE_INITIALIZED
    try:
        init_cache()
        # CACHE_INITIALIZED is now set in init_cache()
        print("Cache initialization completed successfully")
    except Exception as e:
        logger.error(f"Background cache initialization failed: {str(e)}")

# Update route handlers to use lazy loading
@app.route("/status", methods=["GET"])
def status():
    """Health check endpoint"""
    try:
         # Add cache initialization check
        if not ensure_cache_initialized():
            # Return a response indicating cache is loading
            return jsonify({
                "status": "initializing",
                "message": "Data is being loaded. Please try again in a few minutes."
            }), 202  # 202 Accepted status code
    except Exception as e:
        return jsonify({
            "status": "warning",
            "message": "Service running but cache not initialized",
            "error": str(e)
        })

@app.route("/get_localities", methods=["GET"])
def get_localities():
    """Get all localities, properly formatted and sorted alphabetically"""

    try:
            # Add cache initialization check
        if not ensure_cache_initialized():
        # Return a response indicating cache is loading
            return jsonify({
            "status": "initializing",
            "message": "Data is being loaded. Please try again in a few minutes."
        }), 202  # 202 Accepted status code
        # Convert all localities to title case and sort
        formatted_localities = sorted(
            [loc['name'].strip().title() for loc in LOCALITIES_CACHE if loc.get("name")]
        )
        return jsonify({
            "status": "success",
            "localities": formatted_localities
        })
    except Exception as e:
        logger.error(f"Error fetching localities: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to fetch localities"
        }), 500

# @app.route("/update_cache", methods=["GET"])
# def update_cache():
#     """Endpoint to manually update the cache"""
#     try:
#         init_cache()
#         return jsonify({
#             "status": "success",
#             "message": "Cache updated successfully",
#             "total_projects": len(RESIDENTIAL_PROJECTS_CACHE)
#         })
#     except Exception as e:
#         logger.error(f"Cache update failed: {str(e)}")
#         return jsonify({
#             "status": "error",
#             "message": str(e)
#         }), 500

        
    except Exception as e:
        logger.error(f"Error in matching properties to projects: {str(e)}")
        return []

def filter_residential_properties(properties: list, 
    price_min: float = None, 
    price_max: float = None, 
    bhk: Union[str, list] = None,
    transaction_type: str = None,
    propertyType: Union[str, list] = None,
    locality: Union[str, list] = None
) -> list:
    """
    Filters the list of properties based on various criteria.
    
    Sample property structure:
    {
        'name': 'Kalhaar Blues And Greens',
        'price': 150000,
        'transactionType': 'rent',
        'locality': ['Sanand'],  # Note: locality is a list
        'property_type': 'Bungalow/Villa',
        'bhk': '4 BHK',
        ...
    }
    """
    # Convert single values to lists for consistent handling
    # Convert bhk parameter to a list of lowercase strings
    if bhk:
        if isinstance(bhk, str):
            bhk_values = [bhk.lower()]
        else:  # it's already a list
            bhk_values = [b.lower() for b in bhk]
    else:
        bhk_values = None
    propertyTypes = [propertyType] if isinstance(propertyType, str) else propertyType if propertyType else None
    localities = [locality] if isinstance(locality, str) else locality if locality else None

    if localities:
        localities = [loc.strip().lower() for loc in localities]

    if propertyTypes:
        propertyTypes = [prop_type.strip().lower() for prop_type in propertyTypes]

    filtered = []
    for prop in properties:
        try:
            # Price handling
            prop_price = prop.get("price")
            if isinstance(prop_price, str):
                try:
                    prop_price = float(prop_price.replace(',', '').replace('₹', '').strip())
                except (ValueError, TypeError):
                    prop_price = None

            # Apply filters only if they are provided
            # Price filter
            if price_min is not None and (prop_price is None or prop_price < price_min):
                continue
            if price_max is not None and (prop_price is None or prop_price > price_max):
                continue

            # BHK filter (exact match including "BHK")
            if bhk_values:
                prop_bhk = prop.get("bhk", "").lower()
                if not any(bhk_val in prop_bhk for bhk_val in bhk_values):
                    continue

            # Transaction type filter (exact match)
            if transaction_type and prop.get("transactionType") != transaction_type:
                continue

            # Property type filter (exact match)
            if propertyTypes:
                prop_type = prop.get("propertyType", "").lower()
                # Skip this property if its type doesn't match any requested types
                if prop_type not in propertyTypes:
                    continue

            # Locality filter (check if any requested locality is in the property's locality list)
            if localities:
                  # Get the property locality and ensure it's a list
                prop_locality = prop.get("locality", "")
                # If it's a string, convert it to a list
                if isinstance(prop_locality, str):
                    prop_localities = [prop_locality.lower()]  # Convert string to list with lowercase
                else:
                    prop_localities = [loc.lower() for loc in prop_locality]  # Assume it's a list

                if not any(loc in prop_localities for loc in localities):
                    continue

            filtered.append(prop)

        except Exception as e:
            logger.error(f"Error filtering property: {str(e)}")
            logger.error(f"Problematic property: {prop}")
            continue

    return filtered

@app.route("/commercial_projects", methods=["GET"])
def get_commercial_projects():
    """
    Get commercial projects with optional viewport filtering and pagination.
    
    Query params:
    - Regular pagination: limit, offset
    - Viewport filtering: minLat, maxLat, minLng, maxLng (all optional)
    """
    
    try:
            # Add cache initialization check
        if not ensure_cache_initialized():
        # Return a response indicating cache is loading
            return jsonify({
            "status": "initializing",
            "message": "Data is being loaded. Please try again in a few minutes."
        }), 202  # 202 Accepted status code
            
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
            # Add cache initialization check
        if not ensure_cache_initialized():
        # Return a response indicating cache is loading
            return jsonify({
            "status": "initializing",
            "message": "Data is being loaded. Please try again in a few minutes."
        }), 202  # 202 Accepted status code

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

def get_properties_in_viewport(properties_cache: list, viewport_params: dict, pagination_params: dict):
    """
    Reusable function to get properties within a viewport with pagination
    Similar to get_projects_in_viewport but returns properties instead of projects
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

    # Filter properties by viewport
    in_viewport_properties = filter_projects_by_viewport(properties_cache, viewport)
    
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
        "total": len(in_viewport_properties),
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
    if start >= len(in_viewport_properties):
        response.update({
            "properties": [],  # Changed from "projects" to "properties"
            "has_more": False,
            "message": "Page number exceeds available data for this viewport"
        })
    else:
        response.update({
            "properties": in_viewport_properties[start:end],  # Changed from "projects" to "properties"
            "has_more": end < len(in_viewport_properties)
        })
    
    return response

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

@app.route("/residential_property_by_id", methods=["GET"])
def get_residential_property_by_id():
    """
    Get residential property by ID
    """
    try:
            # Add cache initialization check
        if not ensure_cache_initialized():
        # Return a response indicating cache is loading
            return jsonify({
            "status": "initializing",
            "message": "Data is being loaded. Please try again in a few minutes."
        }), 202  # 202 Accepted status code
        
        property_id = request.args.get("propertyId")
        for property in RESIDENTIAL_PROPERTIES_CACHE:
            if property["airtable_id"] == property_id:
                return jsonify(property)
        return jsonify({
            "status": "error",
            "message": "Property not found"
        }), 404
    except Exception as e:
        logger.error(f"Error fetching residential property by ID: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

@app.route("/residential_properties", methods=["GET"])
def get_residential_properties():
    """
    Get residential properties with optional viewport filtering and pagination.
    
    Query params:
    - Regular pagination: limit, offset
    - Viewport filtering: minLat, maxLat, minLng, maxLng (all optional)
    """
    try:
        # Start initialization if needed but don't wait for it
        if not ensure_cache_initialized():
            # Return a response indicating cache is loading
            return jsonify({
                "status": "initializing",
                "message": "Data is being loaded. Please try again in a few minutes.",
                "properties": [],
                "total": 0
            }), 202  # 202 Accepted status code
        
        # Parse price filters
        price_min = request.args.get("priceMin")
        price_max = request.args.get("priceMax")
        price_min = float(price_min) if price_min else None
        price_max = float(price_max) if price_max else None

        # Parse list filters (handle both single values and comma-separated lists)
        bhk = request.args.get("bhk")
        bhk = bhk.split(",") if bhk and "," in bhk else bhk

        propertyType = request.args.get("propertyType")
        propertyType = propertyType.split(",") if propertyType and "," in propertyType else propertyType

        locality = request.args.get("locality")
        locality = locality.split(",") if locality and "," in locality else locality

        # Parse single value filters
        transaction_type = request.args.get("transactionType")

        # Apply filters
        filtered_properties = filter_residential_properties(
            RESIDENTIAL_PROPERTIES_CACHE,
            price_min=price_min,
            price_max=price_max,
            bhk=bhk,
            transaction_type=transaction_type,
            propertyType=propertyType,
            locality=locality
        ) 

        # Parse pagination parameters
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
            
            result = get_properties_in_viewport(
                filtered_properties,
                viewport_params,
                pagination_params
            )
            return jsonify(result)
        else:
            # Regular pagination without viewport
            start = offset
            end = offset + limit
            
            # Check if offset exceeds total available data
            if offset >= len(filtered_properties):
                return jsonify({
                    "status": "success",
                    "properties": [],
                    "total": len(filtered_properties),
                    "limit": limit,
                    "offset": offset,
                    "has_more": False,
                    "message": "Offset exceeds available data"
                })
            
            return jsonify({
                "status": "success",
                "properties": filtered_properties[start:end],
                "total": len(filtered_properties),
                "limit": limit,
                "offset": offset,
                "has_more": end < len(filtered_properties)
            })
            
    except ValueError as e:
        logger.error(f"Invalid parameters: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error fetching residential properties: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

if __name__ == "__main__":
    # Don't initialize cache at startup
    # Let it initialize on first request instead
    app.run(host='0.0.0.0', debug=True, port=int(os.environ.get('PORT', 8080)))
    
