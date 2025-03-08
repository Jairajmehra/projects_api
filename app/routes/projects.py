from flask import jsonify, request
from app import app
import logging

from app.services.cache_service import (
    ensure_cache_initialized,
    get_residential_projects_cache,
    get_commercial_projects_cache,
    RESIDENTIAL_PROJECTS_NAME_INDEX,
    COMMERCIAL_PROJECTS_NAME_INDEX
)
from app.utils.pagination_utils import get_projects_in_viewport

logger = logging.getLogger(__name__)

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
        limit = max(1, int(request.args.get("limit", 12)))
        offset = max(0, int(request.args.get("offset", 0)))
        
        # Get commercial projects using the accessor function
        commercial_projects = get_commercial_projects_cache()
        
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
                get_commercial_projects_cache(),
                viewport_params,
                pagination_params
            )
            return jsonify(result)
        else:
            # Regular pagination without viewport
            start = offset
            end = offset + limit
            
            # Check if offset exceeds total available data
            if offset >= len(commercial_projects):
                return jsonify({
                    "status": "success",
                    "projects": [],
                    "total": len(commercial_projects),
                    "limit": limit,
                    "offset": offset,
                    "has_more": False,
                    "message": "Offset exceeds available data"
                })
            
            return jsonify({
                "status": "success",
                "projects": commercial_projects[start:end],
                "total": len(commercial_projects),
                "limit": limit,
                "offset": offset,
                "has_more": end < len(commercial_projects)
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
        limit = max(1, int(request.args.get("limit", 12)))
        offset = max(0, int(request.args.get("offset", 0)))
        
        # Get residential projects using the accessor function
        residential_projects = get_residential_projects_cache()
        
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
                get_residential_projects_cache(),
                viewport_params,
                pagination_params
            )
            return jsonify(result)
        else:
            # Regular pagination without viewport
            start = offset
            end = offset + limit
            
            # Check if offset exceeds total available data
            if offset >= len(residential_projects):
                return jsonify({
                    "status": "success",
                    "projects": [],
                    "total": len(residential_projects),
                    "limit": limit,
                    "offset": offset,
                    "has_more": False,
                    "message": "Offset exceeds available data"
                })
            
            return jsonify({
                "status": "success",
                "projects": residential_projects[start:end],
                "total": len(residential_projects),
                "limit": limit,
                "offset": offset,
                "has_more": end < len(residential_projects)
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
            
        from app.services.cache_service import LOCALITIES_CACHE
        
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
