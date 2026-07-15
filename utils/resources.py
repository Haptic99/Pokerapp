# utils/resources.py

import os

def get_base_path():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_image_path(filename):
    return os.path.join(get_base_path(), 'images', filename)

def get_style_path(filename):
    return os.path.join(get_base_path(), 'styles', filename)
