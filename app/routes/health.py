from flask import jsonify
from app import app
import logging
from app.services.cache_service import ensure_cache_initialized, get_cache_size, debug_cache_status

logger = logging.getLogger(__name__)

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
        
        # Get cache size using the accessor function
        cache_size = get_cache_size()
        
        # Print debug info to logs
        debug_info = debug_cache_status()
        
        return jsonify({
            "status": "healthy",
            "cache_size": cache_size,
            "debug_info": debug_info
        })
    except Exception as e:
        logger.error(f"Error in status endpoint: {str(e)}")
        return jsonify({
            "status": "warning",
            "message": "Service running but cache not initialized",
            "error": str(e)
        })
