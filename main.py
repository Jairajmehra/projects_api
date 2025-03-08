"""
Main entry point for the application.
This file is used by App Engine to start the server.
"""
import os
from app import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=int(os.environ.get('PORT', 8080)))
