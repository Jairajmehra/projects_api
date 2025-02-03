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
TABLE_NAME = os.environ.get('TABLE_NAME')
COMMERCIAL_TABLE_NAME = os.environ.get('COMMERCIAL_TABLE_NAME')
# Validate required environment variables
if not all([AIRTABLE_API_KEY, BASE_ID, TABLE_NAME, COMMERCIAL_TABLE_NAME]):
    logger.error("Missing required environment variables. Please check your app.yaml configuration.")
    raise ValueError("Missing required environment variables: AIRTABLE_API_KEY, BASE_ID, TABLE_NAME, or COMMERCIAL_TABLE_NAME")

# Initialize Airtable
try:
    api = Api(AIRTABLE_API_KEY)
    table = api.table(BASE_ID, TABLE_NAME)
    commercial_table = api.table(BASE_ID, COMMERCIAL_TABLE_NAME)
    logger.info("Airtable connection initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Airtable connection: {str(e)}")
    raise

# Global cache for projects
PROJECTS_CACHE = []
COMMERCIAL_PROJECTS_CACHE = []
COMMERCIAL_PROJECTS_NAME_INDEX = {}
RESIDENTIAL_PROJECTS_NAME_INDEX = {}

def format_project(record):
    """Format a single project record"""
    try:
        fields = record["fields"]
        brochure_url = ""
        if "Brochure" in fields and fields["Brochure"]:
            brochure_url = fields["Brochure"][0].get("url", "")

        return {
            "rera": fields.get("RERA Number", ""),
            "name": fields.get("Project Name", ""),
            "locality": fields.get("District", ""),
            "propertyType": fields.get("Type", ""),
            "unitSizes": fields.get("Average Carpet Area of Units (Sq Mtrs)", ""),
            "brochureLink": brochure_url,
            "bhk": "3 BHK"
        }
    except Exception as e:
        logger.error(f"Error formatting project record: {str(e)}")
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
    
    for idx, project in enumerate(PROJECTS_CACHE):
        if project and project.get('name'):
            # Create normalized key for case-insensitive search
            name_key = project['name'].lower()
            if name_key not in RESIDENTIAL_PROJECTS_NAME_INDEX:
                RESIDENTIAL_PROJECTS_NAME_INDEX[name_key] = []
            RESIDENTIAL_PROJECTS_NAME_INDEX[name_key].append(idx)

def init_cache():
    """Initialize the cache without using Flask context"""
    global PROJECTS_CACHE
    global COMMERCIAL_PROJECTS_CACHE
    try:
        records = table.all()
        commercial_records = commercial_table.all()
        PROJECTS_CACHE = [format_project(record) for record in records]
        COMMERCIAL_PROJECTS_CACHE = [format_commercial_project(record) for record in commercial_records]
        build_commercial_projects_index()
        build_residential_projects_index()
        print(f"Cache initialized successfully with {len(PROJECTS_CACHE)} residential projects and {len(COMMERCIAL_PROJECTS_CACHE)} commercial projects")
    except Exception as e:
        logger.error(f"Error initializing cache: {str(e)}")
        PROJECTS_CACHE = []
        COMMERCIAL_PROJECTS_CACHE = []

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "cache_size": len(PROJECTS_CACHE)
    })

@app.route("/update_cache", methods=["GET"])
def update_cache():
    """Endpoint to manually update the cache"""
    try:
        init_cache()
        return jsonify({
            "status": "success",
            "message": "Cache updated successfully",
            "total_projects": len(PROJECTS_CACHE)
        })
    except Exception as e:
        logger.error(f"Cache update failed: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/commercial_projects", methods=["GET"])
def get_commercial_projects():
    """Get paginated commercial projects from cache with offset"""
    try:
        # If cache is empty, initialize it
        if not COMMERCIAL_PROJECTS_CACHE:
            init_cache()
            
        page = max(1, int(request.args.get("page", 1)))
        limit = min(50, max(1, int(request.args.get("limit", 12))))
        offset = max(0, int(request.args.get("offset", 0)))
        
        # Calculate start and end indices with offset
        start = ((page - 1) * limit) + offset
        end = start + limit
        
        # Ensure we don't exceed array bounds
        if start >= len(COMMERCIAL_PROJECTS_CACHE):
            return jsonify({
                "status": "success",
                "projects": [],
                "total": len(COMMERCIAL_PROJECTS_CACHE),
                "page": page,
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "message": "Page number exceeds available data"
            })
        
        return jsonify({
            "status": "success",
            "projects": COMMERCIAL_PROJECTS_CACHE[start:end],
            "total": len(COMMERCIAL_PROJECTS_CACHE),
            "page": page,
            "limit": limit,
            "offset": offset,
            "has_more": end < len(COMMERCIAL_PROJECTS_CACHE)
        })
    except ValueError as e:
        logger.error(f"Invalid pagination parameters: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Invalid page, limit, or offset parameter"
        }), 400
    except Exception as e:
        logger.error(f"Error fetching commercial projects: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500
    
@app.route("/projects", methods=["GET"])
def get_projects():
    """Get paginated projects from cache with offset"""
    try:
        # If cache is empty, initialize it
        if not PROJECTS_CACHE:
            init_cache()
            
        page = max(1, int(request.args.get("page", 1)))
        limit = min(50, max(1, int(request.args.get("limit", 12))))
        offset = max(0, int(request.args.get("offset", 0)))
        
        # Calculate start and end indices with offset
        start = ((page - 1) * limit) + offset
        end = start + limit
        
        # Check if offset exceeds total available data
        if offset >= len(PROJECTS_CACHE):
            return jsonify({
                "status": "success",
                "projects": [],
                "total": len(PROJECTS_CACHE),
                "page": page,
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "message": "Offset exceeds available data"
            })
        
        # Ensure we don't exceed array bounds
        if start >= len(PROJECTS_CACHE):
            return jsonify({
                "status": "success",
                "projects": [],
                "total": len(PROJECTS_CACHE),
                "page": page,
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "message": "Page number exceeds available data"
            })
        
        return jsonify({
            "status": "success",
            "projects": PROJECTS_CACHE[start:end],
            "total": len(PROJECTS_CACHE),
            "page": page,
            "limit": limit,
            "offset": offset,
            "has_more": end < len(PROJECTS_CACHE)
        })
    except ValueError as e:
        logger.error(f"Invalid pagination parameters: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Invalid page, limit, or offset parameter"
        }), 400
    except Exception as e:
        logger.error(f"Error fetching projects: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

@app.route("/search_commercial_projects", methods=["GET"])
def search_commercial_projects():
    """Search commercial projects by name with pagination"""
    try:
        search_term = request.args.get("q", "").lower().strip()
        limit = min(100, max(1, int(request.args.get("limit", 12))))
        
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
        
        return jsonify({
            "status": "success",
            "projects": matching_projects[:limit],
            "total": len(matching_projects),
            "limit": limit,
            "has_more": len(matching_projects) > limit
        })
        
    except ValueError as e:
        logger.error(f"Invalid search parameters: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Invalid parameters"
        }), 400
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

@app.route("/search_residential_projects", methods=["GET"])
def search_residential_projects():
    """Search residential projects by name with pagination"""
    try:
        search_term = request.args.get("q", "").lower().strip()
        limit = min(100, max(1, int(request.args.get("limit", 12))))
        
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
        matching_projects = [PROJECTS_CACHE[idx] for idx in matching_indices]
        matching_projects.sort(key=lambda x: x['name'].lower())
        
        return jsonify({
            "status": "success",
            "projects": matching_projects[:limit],
            "total": len(matching_projects),
            "limit": limit,
            "has_more": len(matching_projects) > limit
        })
        
    except ValueError as e:
        logger.error(f"Invalid search parameters: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Invalid parameters"
        }), 400
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

if __name__ == "__main__":
    # Initialize cache at startup
    init_cache()
    # Development server
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8086)))
    
