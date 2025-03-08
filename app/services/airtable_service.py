from pyairtable import Api
import logging
from app.config import (
    AIRTABLE_API_KEY, PROJECTS_BASE_ID, RESIDENTIAL_PROJECTS_TABLE_ID, COMMERCIAL_PROJECTS_TABLE_ID,
    INVENTORY_BASE_ID, RESIDENTIAL_PROPERTIES_TABLE_ID, LOCALITIES_TABLE_ID, COMMERCIAL_PROPERTIES_TABLE_ID
)

logger = logging.getLogger(__name__)

# Initialize Airtable client
api = None
projects_residential_table = None
projects_commercial_table = None
residential_inventory_table = None
commercial_inventory_table = None
localities_table = None

def init_airtable_connection():
    """Initialize the Airtable API connection"""
    global api, projects_residential_table, projects_commercial_table, residential_inventory_table, commercial_inventory_table, localities_table
    
    try:
        api = Api(AIRTABLE_API_KEY)
        localities_table = api.table(INVENTORY_BASE_ID, LOCALITIES_TABLE_ID)
        projects_residential_table = api.table(INVENTORY_BASE_ID, "residential projects")
        projects_commercial_table = api.table(PROJECTS_BASE_ID, COMMERCIAL_PROJECTS_TABLE_ID)
        residential_inventory_table = api.table(INVENTORY_BASE_ID, RESIDENTIAL_PROPERTIES_TABLE_ID)
        commercial_inventory_table = api.table(INVENTORY_BASE_ID, COMMERCIAL_PROPERTIES_TABLE_ID)
        logger.info("Airtable connection initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Airtable connection: {str(e)}")
        return False

def get_residential_projects():
    """Get all residential projects from Airtable"""
    if not api:
        init_airtable_connection()
    return projects_residential_table.all(view="Production")

def get_commercial_properties():
    """Get all commercial properties from Airtable"""
    if not api:
        init_airtable_connection()
    return commercial_inventory_table.all(view="Production")

def get_commercial_projects():
    """Get all commercial projects from Airtable"""
    if not api:
        init_airtable_connection()
    return projects_commercial_table.all()

def get_residential_properties():
    """Get all residential properties from Airtable"""
    if not api:
        init_airtable_connection()
    return residential_inventory_table.all(view="Production")

def get_localities():
    """Get all localities from Airtable"""
    if not api:
        init_airtable_connection()
    return localities_table.all()
