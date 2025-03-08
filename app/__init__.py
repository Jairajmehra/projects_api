from flask import Flask
from flask_cors import CORS
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create and configure the Flask app
app = Flask(__name__)
CORS(app)

# Import routes after app is defined to avoid circular imports
from app.routes import health, projects, properties, search

# Import and initialize services
from app.services.airtable_service import init_airtable_connection
from app.services.cache_service import init_app_cache

# Initialize services (without starting cache loading - lazy loading)
init_airtable_connection()
init_app_cache(app)
