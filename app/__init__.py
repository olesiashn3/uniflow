from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Будь ласка, увійдіть для доступу до цієї сторінки.'

def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes.auth import auth
    from app.routes.events import events
    from app.routes.admin import admin
    from app.routes.favorites import favorites
    from app.routes.profile import profile

    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(events, url_prefix='/')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(favorites, url_prefix='/favorites')
    app.register_blueprint(profile, url_prefix='/')

    return app