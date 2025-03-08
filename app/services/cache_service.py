import threading
import time
import logging
from app.services.airtable_service import get_residential_projects, get_commercial_projects, get_residential_properties, get_commercial_properties, get_localities
from app.services.formatter_service import (
    format_residential_project, format_commercial_project,
    format_residential_property, format_commercial_property, format_locality
)

logger = logging.getLogger(__name__)

# Global cache variables
RESIDENTIAL_PROJECTS_CACHE = []
COMMERCIAL_PROJECTS_CACHE = []
RESIDENTIAL_PROPERTIES_CACHE = []
COMMERCIAL_PROPERTIES_CACHE = []
LOCALITIES_CACHE = []
COMMERCIAL_PROJECTS_NAME_INDEX = {}
RESIDENTIAL_PROJECTS_NAME_INDEX = {}

# Cache initialization flags
CACHE_INITIALIZATION_STARTED = False
CACHE_INITIALIZED = False

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
    global COMMERCIAL_PROPERTIES_CACHE
    global LOCALITIES_CACHE
    global CACHE_INITIALIZED
    
    try:
        # Fetch data from Airtable
        records = get_residential_projects()
        print(f"Residential projects fetched successfully with {len(records)} records")
        time.sleep(10)
        
        commercial_records = get_commercial_projects()
        print(f"Commercial projects fetched successfully with {len(commercial_records)} records")
        time.sleep(11)
        
        residential_inventory_records = get_residential_properties()
        print(f"Residential properties fetched successfully with {len(residential_inventory_records)} records")
        time.sleep(12)
        
        commercial_inventory_records = get_commercial_properties()
        print(f"Commercial properties fetched successfully with {len(commercial_inventory_records)} records")
        time.sleep(13)
        
        localities_records = get_localities()
        print(f"Localities fetched successfully with {len(localities_records)} records")
        time.sleep(14)
        
        # Process and format the data
        RESIDENTIAL_PROJECTS_CACHE = [format_residential_project(record) for record in records]
        COMMERCIAL_PROJECTS_CACHE = [format_commercial_project(record) for record in commercial_records]
        
        # For residential properties, we need to pass RESIDENTIAL_PROJECTS_CACHE to get linked photos
        RESIDENTIAL_PROPERTIES_CACHE = [
            format_residential_property(record, RESIDENTIAL_PROJECTS_CACHE) 
            for record in residential_inventory_records
        ]

        COMMERCIAL_PROPERTIES_CACHE = [
            format_commercial_property(record, COMMERCIAL_PROJECTS_CACHE)
            for record in commercial_inventory_records
        ]
        
        LOCALITIES_CACHE = [format_locality(record) for record in localities_records]
        print('-'*100)
        
        # Build search indices
        build_commercial_projects_index()
        build_residential_projects_index()
        # Set memory flag
        CACHE_INITIALIZED = True
    except Exception as e:
        logger.error(f"Error initializing cache: {str(e)}")
        RESIDENTIAL_PROJECTS_CACHE = []
        COMMERCIAL_PROJECTS_CACHE = []
        RESIDENTIAL_PROPERTIES_CACHE = []
        COMMERCIAL_PROPERTIES_CACHE = []
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

def update_cache():
    """Manually update the cache"""
    init_cache()
    return {
        "status": "success",
        "message": "Cache updated successfully",
        "total_projects": len(RESIDENTIAL_PROJECTS_CACHE)
    }

def init_app_cache(app):
    """Initialize the cache when the app starts"""
    # This is just a placeholder for module initialization
    pass

# Add new accessor functions for cache variables
def get_residential_projects_cache():
    """Return the global residential projects cache"""
    global RESIDENTIAL_PROJECTS_CACHE
    return RESIDENTIAL_PROJECTS_CACHE

def get_commercial_projects_cache():
    """Return the global commercial projects cache"""
    global COMMERCIAL_PROJECTS_CACHE
    return COMMERCIAL_PROJECTS_CACHE

def get_residential_properties_cache():
    """Return the global residential properties cache"""
    global RESIDENTIAL_PROPERTIES_CACHE
    return RESIDENTIAL_PROPERTIES_CACHE

def get_commercial_properties_cache():
    """Return the global commercial properties cache"""
    global COMMERCIAL_PROPERTIES_CACHE
    return COMMERCIAL_PROPERTIES_CACHE

def get_localities_cache():
    """Return the global localities cache"""
    global LOCALITIES_CACHE
    return LOCALITIES_CACHE

def get_residential_projects_name_index():
    """Return the global residential projects name index"""
    global RESIDENTIAL_PROJECTS_NAME_INDEX
    return RESIDENTIAL_PROJECTS_NAME_INDEX

def get_commercial_projects_name_index():
    """Return the global commercial projects name index"""
    global COMMERCIAL_PROJECTS_NAME_INDEX
    return COMMERCIAL_PROJECTS_NAME_INDEX

def get_cache_size():
    """Return the size of the residential properties cache"""
    global RESIDENTIAL_PROPERTIES_CACHE, COMMERCIAL_PROPERTIES_CACHE
    return len(RESIDENTIAL_PROPERTIES_CACHE), len(COMMERCIAL_PROPERTIES_CACHE)

def debug_cache_status():
    """Print debug info about cache status"""
    global RESIDENTIAL_PROJECTS_CACHE, COMMERCIAL_PROJECTS_CACHE, RESIDENTIAL_PROPERTIES_CACHE, COMMERCIAL_PROPERTIES_CACHE, CACHE_INITIALIZED
    
    cache_info = {
        "CACHE_INITIALIZED": CACHE_INITIALIZED,
        "RESIDENTIAL_PROJECTS_CACHE size": len(RESIDENTIAL_PROJECTS_CACHE),
        "COMMERCIAL_PROJECTS_CACHE size": len(COMMERCIAL_PROJECTS_CACHE),
        "RESIDENTIAL_PROPERTIES_CACHE size": len(RESIDENTIAL_PROPERTIES_CACHE),
        "COMMERCIAL_PROPERTIES_CACHE size": len(COMMERCIAL_PROPERTIES_CACHE)
    }
    
    print("=== CACHE DEBUG INFO ===")
    for key, value in cache_info.items():
        print(f"{key}: {value}")
    print("=======================")
    return cache_info
