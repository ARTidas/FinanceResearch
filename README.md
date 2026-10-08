Install dependencies:
pip install beautifulsoup4 PyMySQL pandas numpy openpyxl

Project requires database connection:
create a config.py file in PythonScripts:
# config.py

DB_CONFIG = {
    'host':     'XXXXXXXXXXXXXXX',
    'port':      XXXXXXXXXXXXXXX,
    'user':     'XXXXXXXXXXXXXXX',
    'password': 'XXXXXXXXXXXXXXX',  # Password here!!!
    'database': 'XXXXXXXXXXXXXXX'
}
