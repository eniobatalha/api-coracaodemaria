"""Configurações da aplicação por ambiente."""
import os
from datetime import timedelta


class Config:
    # ── Flask ──────────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-troque-em-producao")
    DEBUG = False
    TESTING = False

    # ── Banco de dados ─────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://cma_user:cma_pass_dev@localhost:5432/coracaodemaria",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # ── JWT ────────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key-troque-em-producao")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get("JWT_EXPIRES_HOURS", 1)))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # ── E-mail ─────────────────────────────────────────────────────────────────
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@coracaodemaria.edu.br")
    MAIL_SUPPRESS_SEND = os.environ.get("MAIL_SUPPRESS_SEND", "false").lower() == "true"

    # ── Aplicação ──────────────────────────────────────────────────────────────
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    TOKEN_CONFIRMACAO_EXPIRACAO_HORAS = int(os.environ.get("TOKEN_CONFIRMACAO_EXPIRACAO_HORAS", 48))
    TOKEN_RESET_SENHA_EXPIRACAO_HORAS = int(os.environ.get("TOKEN_RESET_SENHA_EXPIRACAO_HORAS", 2))


class DevelopmentConfig(Config):
    DEBUG = True
    MAIL_SUPPRESS_SEND = True  # Não envia e-mails em dev — apenas loga no console


class ProductionConfig(Config):
    DEBUG = False
    MAIL_SUPPRESS_SEND = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    MAIL_SUPPRESS_SEND = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
