import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uniflow-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:root@localhost/uniflow_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Dev convenience: allow auto-creating missing tables on startup.
    # Keep this enabled by default to avoid breaking local runs.
    AUTO_CREATE_TABLES = os.environ.get('AUTO_CREATE_TABLES', '1') not in ('0', 'false', 'False')