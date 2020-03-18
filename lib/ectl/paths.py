import os

# --------------------------------------------------------------
try:
    default_template = os.environ['MODELE_TEMPLATE_PATH'].split(os.pathsep)
except:
    default_template = ['.']

# Search for input files
try:
    default_file = os.environ['MODELE_FILE_PATH'].split(os.pathsep)
except Exception as e:
    default_file = ['.']
# --------------------------------------------------------------
