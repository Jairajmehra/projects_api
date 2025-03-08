from app.models.schemas import ViewportParams
from app.utils.location_utils import filter_projects_by_viewport
import logging

logger = logging.getLogger(__name__)

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
