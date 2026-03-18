import sys
import os
from pathlib import Path

def resource_path(relative_path):
    """ 
    Get absolute path to resource, works for dev and for PyInstaller
    Enhanced with pathlib for better Chinese path support
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
    except Exception:
        base_path = os.path.abspath(".")

    # Use pathlib for better Unicode/Chinese path support
    return str((Path(base_path) / relative_path).resolve())
