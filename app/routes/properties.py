from flask import jsonify, request
from app import app
import logging
from app.services.cache_service import (
    ensure_cache_initialized,
    get_residential_properties_cache,
    get_commercial_properties_cache
)
from app.utils.pagination_utils import get_properties_in_viewport
from app.utils.filter_utils import (filter_residential_properties, filter_commercial_properties)

logger = logging.getLogger(__name__)

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
        # Get the cache using accessor function
        properties_cache = get_residential_properties_cache()
        
        for property in properties_cache:
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
    
@app.route("/commercial_property_by_id", methods=["GET"])
def get_commercial_property_by_id():
    """
    Get commercial property by ID
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
        # Get the cache using accessor function
        properties_cache = get_commercial_properties_cache()
        
        for property in properties_cache:
            if property["airtable_id"] == property_id:
                return jsonify(property)
        return jsonify({
            "status": "error",
            "message": "Property not found"
        }), 404
    except Exception as e:
        logger.error(f"Error fetching commercial property by ID: {str(e)}")
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
    - Additional filters: priceMin, priceMax, bhk, transactionType, propertyType, locality
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
        
        # Get the cache using accessor function
        properties_cache = get_residential_properties_cache()
        
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

        # Apply filters to the properties from cache
        filtered_properties = filter_residential_properties(
            properties_cache,
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
    
@app.route("/commercial_properties", methods=["GET"])
def get_commercial_properties():
    """
    Get commercial properties with optional viewport filtering and pagination.
    
    Query params:
    - Regular pagination: limit, offset
    - Viewport filtering: minLat, maxLat, minLng, maxLng (all optional)
    - Additional filters: priceMin, priceMax, transactionType, propertyType, locality
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
        
        # Get the cache using accessor function
        properties_cache = get_commercial_properties_cache()
        
        # Parse price filters
        price_min = request.args.get("priceMin")
        price_max = request.args.get("priceMax")
        price_min = float(price_min) if price_min else None
        price_max = float(price_max) if price_max else None

        # Parse list filters (handle both single values and comma-separated lists)
        propertyType = request.args.get("propertyType")
        propertyType = propertyType.split(",") if propertyType and "," in propertyType else propertyType

        locality = request.args.get("locality")
        locality = locality.split(",") if locality and "," in locality else locality

        # Parse single value filters
        transaction_type = request.args.get("transactionType")

        # Apply filters to the properties from cache
        filtered_properties = filter_commercial_properties(
            properties_cache,
            price_min=price_min,
            price_max=price_max,
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
