"""Instâncias das extensões Flask (inicializadas sem app — padrão factory)."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flasgger import Swagger

db       = SQLAlchemy()
migrate  = Migrate()
jwt      = JWTManager()
mail     = Mail()

# Config da UI do Swagger (rotas, specs) — deve ir no construtor, não no init_app
_SWAGGER_UI_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs",
}

swagger = Swagger(config=_SWAGGER_UI_CONFIG)
