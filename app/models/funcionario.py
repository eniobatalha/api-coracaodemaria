"""Model do Funcionário — professor, secretária ou diretora."""
import enum
import secrets
from datetime import datetime, timezone, timedelta

from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class TipoFuncionario(str, enum.Enum):
    professor = "professor"
    secretaria = "secretaria"
    diretora = "diretora"


class Funcionario(db.Model):
    """
    Funcionário da escola.

    O cadastro é feito pela secretaria. O username segue o padrão nome.sobrenome
    (ex: luana.marcela). A senha é definida no ato do cadastro pela secretaria
    ou pode ser redefinida via e-mail.
    """

    __tablename__ = "funcionarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    usuario = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    cargo = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.Enum(TipoFuncionario), nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)

    # Token para recuperação de senha
    token_reset_senha = db.Column(db.String(100), nullable=True, unique=True, index=True)
    token_reset_senha_exp = db.Column(db.DateTime(timezone=True), nullable=True)

    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    atualizado_em = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())

    def __repr__(self) -> str:
        return f"<Funcionario id={self.id} usuario={self.usuario} tipo={self.tipo}>"

    # ── Senha ──────────────────────────────────────────────────────────────────

    def set_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha: str) -> bool:
        return check_password_hash(self.senha_hash, senha)

    # ── Token de reset de senha ────────────────────────────────────────────────

    def gerar_token_reset_senha(self, horas: int = 2) -> str:
        token = secrets.token_urlsafe(48)
        self.token_reset_senha = token
        self.token_reset_senha_exp = datetime.now(timezone.utc) + timedelta(hours=horas)
        return token

    def validar_token_reset_senha(self, token: str) -> bool:
        if not self.token_reset_senha or self.token_reset_senha != token:
            return False
        if datetime.now(timezone.utc) > self.token_reset_senha_exp:
            return False
        return True

    def usar_token_reset_senha(self) -> None:
        self.token_reset_senha = None
        self.token_reset_senha_exp = None

    # ── Serialização ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "usuario": self.usuario,
            "email": self.email,
            "cargo": self.cargo,
            "tipo": self.tipo.value,
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
