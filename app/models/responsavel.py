"""Model do Responsável — pai, mãe ou guardião do aluno."""
import secrets
from datetime import datetime, timezone, timedelta

from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class Responsavel(db.Model):
    """
    Responsável legal de um ou mais alunos.

    Fluxo de e-mail:
      1. Secretaria cria o cadastro → token_confirmacao gerado → e-mail enviado
      2. Responsável clica no link → define senha → email_confirmado = True
      3. Secretaria pode alterar e-mail a qualquer momento:
         - Antes de confirmar: troca direta + novo token_confirmacao
         - Após confirmar: email_pendente + token_troca_email → link enviado ao novo endereço
      4. Responsável confirma troca → email = email_pendente → pendente limpo
    """

    __tablename__ = "responsaveis"

    id    = db.Column(db.Integer, primary_key=True)
    nome  = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)

    senha_hash        = db.Column(db.String(255), nullable=True)
    email_confirmado  = db.Column(db.Boolean, default=False, nullable=False)

    # Primeiro acesso
    token_confirmacao     = db.Column(db.String(100), nullable=True, unique=True, index=True)
    token_confirmacao_exp = db.Column(db.DateTime(timezone=True), nullable=True)

    # Recuperação de senha
    token_reset_senha     = db.Column(db.String(100), nullable=True, unique=True, index=True)
    token_reset_senha_exp = db.Column(db.DateTime(timezone=True), nullable=True)

    # Troca de e-mail (após confirmação)
    email_pendente        = db.Column(db.String(255), nullable=True)
    token_troca_email     = db.Column(db.String(100), nullable=True, unique=True, index=True)
    token_troca_email_exp = db.Column(db.DateTime(timezone=True), nullable=True)

    ativo         = db.Column(db.Boolean, default=True, nullable=False)
    criado_em     = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    atualizado_em = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())

    def __repr__(self) -> str:
        return f"<Responsavel id={self.id} email={self.email}>"

    # ── Senha ──────────────────────────────────────────────────────────────────

    def set_senha(self, senha: str) -> None:
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha: str) -> bool:
        if not self.senha_hash:
            return False
        return check_password_hash(self.senha_hash, senha)

    # ── Token de confirmação de conta (primeiro acesso) ────────────────────────

    def gerar_token_confirmacao(self, horas: int = 48) -> str:
        token = secrets.token_urlsafe(48)
        self.token_confirmacao     = token
        self.token_confirmacao_exp = datetime.now(timezone.utc) + timedelta(hours=horas)
        return token

    def validar_token_confirmacao(self, token: str) -> bool:
        if not self.token_confirmacao or self.token_confirmacao != token:
            return False
        return datetime.now(timezone.utc) <= self.token_confirmacao_exp

    def usar_token_confirmacao(self) -> None:
        self.email_confirmado      = True
        self.token_confirmacao     = None
        self.token_confirmacao_exp = None

    # ── Token de reset de senha ────────────────────────────────────────────────

    def gerar_token_reset_senha(self, horas: int = 2) -> str:
        token = secrets.token_urlsafe(48)
        self.token_reset_senha     = token
        self.token_reset_senha_exp = datetime.now(timezone.utc) + timedelta(hours=horas)
        return token

    def validar_token_reset_senha(self, token: str) -> bool:
        if not self.token_reset_senha or self.token_reset_senha != token:
            return False
        return datetime.now(timezone.utc) <= self.token_reset_senha_exp

    def usar_token_reset_senha(self) -> None:
        self.token_reset_senha     = None
        self.token_reset_senha_exp = None

    # ── Troca de e-mail (pós-confirmação) ─────────────────────────────────────

    def gerar_token_troca_email(self, novo_email: str, horas: int = 48) -> str:
        token = secrets.token_urlsafe(48)
        self.email_pendente        = novo_email
        self.token_troca_email     = token
        self.token_troca_email_exp = datetime.now(timezone.utc) + timedelta(hours=horas)
        return token

    def validar_token_troca_email(self, token: str) -> bool:
        if not self.token_troca_email or self.token_troca_email != token:
            return False
        return datetime.now(timezone.utc) <= self.token_troca_email_exp

    def confirmar_troca_email(self) -> None:
        self.email                 = self.email_pendente
        self.email_pendente        = None
        self.token_troca_email     = None
        self.token_troca_email_exp = None

    def limpar_troca_email(self) -> None:
        self.email_pendente        = None
        self.token_troca_email     = None
        self.token_troca_email_exp = None

    # ── Status calculado ──────────────────────────────────────────────────────

    @property
    def status_email(self) -> str:
        if self.email_pendente:
            return "troca_pendente"
        if self.email_confirmado:
            return "confirmado"
        return "aguardando"

    # ── Serialização ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "nome":             self.nome,
            "email":            self.email,
            "email_confirmado": self.email_confirmado,
            "email_pendente":   self.email_pendente,
            "status_email":     self.status_email,
            "ativo":            self.ativo,
            "criado_em":        self.criado_em.isoformat() if self.criado_em else None,
        }
