"""Application factory — cria e configura o app Flask."""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from .config import config
from .extensions import db, migrate, jwt, mail, swagger


# ── Template do Swagger (título, descrição, segurança, tags) ──────────────────
# A config da UI (rotas, specs_route) fica em extensions.py no construtor.

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "API Coração de Maria",
        "description": (
            "## API REST do Sistema Escolar Coração de Maria\n\n"
            "Esta API fornece os serviços de backend para os portais do **aluno** (responsável) "
            "e do **funcionário** (professor, secretaria e diretoria).\n\n"
            "### Autenticação\n"
            "A maioria dos endpoints protegidos requer um **JWT Bearer Token**. "
            "Obtenha o token através dos endpoints de login e inclua-o no header:\n\n"
            "```\nAuthorization: Bearer {seu_token_aqui}\n```\n\n"
            "### Ambientes\n"
            "- **Desenvolvimento:** `http://localhost:5000`\n"
            "- **Documentação:** `http://localhost:5000/docs`\n\n"
            "### Contato\n"
            "Para dúvidas sobre a API, entre em contato com a equipe de TI."
        ),
        "version": "1.0.0",
        "contact": {
            "name": "Enio Batalha",
            "email": "eniobatalha@gmail.com",
        },
        "license": {
            "name": "Uso interno — Colégio Coração de Maria",
        },
    },
    "basePath": "/api/v1",
    "schemes": ["http", "https"],
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "securityDefinitions": {
        "BearerAuth": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": (
                "Token JWT no formato: **Bearer {token}**\n\n"
                "Obtenha o token via `/api/v1/auth/responsavel/login` "
                "ou `/api/v1/auth/funcionario/login`."
            ),
        }
    },
    "tags": [
        {
            "name": "Auth — Responsável",
            "description": (
                "Endpoints de autenticação para **responsáveis** (pais, mães e guardiões). "
                "O acesso usa e-mail como identificador. "
                "A conta é criada pela secretaria e ativada via link enviado por e-mail."
            ),
        },
        {
            "name": "Auth — Funcionário",
            "description": (
                "Endpoints de autenticação para **funcionários** da escola "
                "(professor, secretária e diretora). "
                "O acesso usa nome de usuário no formato `nome.sobrenome`."
            ),
        },
    ],
}


def create_app(env_name: str = "default") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config[env_name])

    # ── CORS — permite apenas o frontend configurado ──────────────────────────
    CORS(
        app,
        resources={r"/api/*": {
            "origins": os.environ.get("FRONTEND_URL", "http://localhost:3000"),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }},
        supports_credentials=False,
    )

    # ── Inicializa extensões ───────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    mail.init_app(app)
    app.config["SWAGGER"] = SWAGGER_TEMPLATE
    swagger.init_app(app)

    # ── Registra blueprints ───────────────────────────────────────────────────
    from .auth.routes          import auth_bp
    from .professores.routes   import professores_bp
    from .turmas.routes        import turmas_bp
    from .alunos.routes        import alunos_bp
    from .responsaveis.routes  import responsaveis_bp
    from .agenda.routes        import agenda_bp
    from .comunicados.routes   import comunicados_bp

    app.register_blueprint(auth_bp,          url_prefix="/api/v1/auth")
    app.register_blueprint(professores_bp,   url_prefix="/api/v1/professores")
    app.register_blueprint(turmas_bp,        url_prefix="/api/v1/turmas")
    app.register_blueprint(alunos_bp,        url_prefix="/api/v1/alunos")
    app.register_blueprint(responsaveis_bp,  url_prefix="/api/v1/responsaveis")
    app.register_blueprint(agenda_bp,        url_prefix="/api/v1/agenda")
    app.register_blueprint(comunicados_bp,   url_prefix="/api/v1/comunicados")

    # ── Importa models (necessário para Alembic detectar as tabelas) ──────────
    from . import models  # noqa: F401

    # ── Handlers de erro globais ──────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"erro": "Endpoint não encontrado"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"erro": "Método HTTP não permitido neste endpoint"}), 405

    @app.errorhandler(500)
    def internal_error(_):
        return jsonify({"erro": "Erro interno do servidor"}), 500

    @jwt.unauthorized_loader
    def unauthorized_callback(reason):
        return jsonify({"erro": "Token ausente ou inválido", "detalhe": reason}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        return jsonify({"erro": "Token expirado. Faça login novamente."}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return jsonify({"erro": "Token inválido", "detalhe": reason}), 422

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health")
    def health():
        """
        Health check da API
        ---
        tags:
          - Health
        summary: Verifica se a API está no ar
        responses:
          200:
            description: API operacional
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: ok
                versao:
                  type: string
                  example: "1.0.0"
        """
        return jsonify({"status": "ok", "versao": "1.0.0"})

    # ── CLI seeds ─────────────────────────────────────────────────────────────
    from seeds import register_commands
    register_commands(app)

    return app
