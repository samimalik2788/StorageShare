"""
StorageShare - Mobile Storage Sharing App
Entry point for the application
"""

import os
import sys

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main_app import StorageShareApp

if __name__ == '__main__':
    StorageShareApp().run()