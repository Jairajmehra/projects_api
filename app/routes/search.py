from flask import jsonify, request
from app import app
import logging
from app.services.cache_service import (
    ensure_cache_initialized,
    RESIDENTIAL_PROJECTS_CACHE,
    COMMERCIAL_PROJECTS_CACHE,
    RESIDENTIAL_PROJECTS_NAME_INDEX,
    COMMERCIAL_PROJECTS_NAME_INDEX
)

logger = logging.getLogger(__name__)

@app.route("/search_commercial_projects", methods=["GET"])
def search_commercial_projects():
    """Search commercial projects by name with pagination and offset"""
    try:
        # Check cache initialization first
        if not ensure_cache_initialized():
            return jsonify({
                "status": "initializing",
                "message": "Data is being loaded. Please try again in a few minutes."
            }), 202

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
        # Check cache initialization first
        if not ensure_cache_initialized():
            return jsonify({
                "status": "initializing",
                "message": "Data is being loaded. Please try again in a few minutes."
            }), 202

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
