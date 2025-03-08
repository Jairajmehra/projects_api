import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Airtable Configuration
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')
PROJECTS_BASE_ID = os.environ.get('PROJECTS_BASE_ID')
RESIDENTIAL_PROJECTS_TABLE_ID = os.environ.get('RESIDENTIAL_PROJECTS_TABLE_ID')
COMMERCIAL_PROJECTS_TABLE_ID = os.environ.get('COMMERCIAL_PROJECTS_TABLE_ID')
INVENTORY_BASE_ID = os.environ.get('INVENTORY_BASE_ID')
RESIDENTIAL_PROPERTIES_TABLE_ID = os.environ.get('RESIDENTIAL_PROPERTIES_TABLE_ID')
COMMERCIAL_PROPERTIES_TABLE_ID = os.environ.get('COMMERCIAL_PROPERTIES_TABLE_ID')
LOCALITIES_TABLE_ID = os.environ.get('LOCALITIES_TABLE_ID')

# API Configuration
DEFAULT_LIMIT = 12
MAX_LIMIT = 500

# Cache Configuration
ENABLE_CACHING = True
