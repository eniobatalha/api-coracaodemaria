"""Schemas de validação e serialização para os endpoints de autenticação."""
from marshmallow import Schema, fields, validate, validates, ValidationError


class LoginResponsavelSchema(Schema):
    email = fields.Email(required=True, metadata={"description": "E-mail cadastrado do responsável"})
    senha = fields.Str(
        required=True,
        validate=validate.Length(min=6, max=128),
        metadata={"description": "Senha da conta"},
    )


class LoginFuncionarioSchema(Schema):
    usuario = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=100),
        metadata={"description": "Nome de usuário (ex: luana.marcela)"},
    )
    senha = fields.Str(
        required=True,
        validate=validate.Length(min=6, max=128),
        metadata={"description": "Senha da conta"},
    )


class ConfirmarContaSchema(Schema):
    token = fields.Str(required=True, metadata={"description": "Token recebido no e-mail de confirmação"})
    senha = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128),
        metadata={"description": "Nova senha (mínimo 8 caracteres)"},
    )
    confirmar_senha = fields.Str(
        required=True,
        metadata={"description": "Confirmação da nova senha (deve ser idêntica ao campo senha)"},
    )

    @validates("confirmar_senha")
    def _senhas_iguais(self, value):
        # Acesso ao dado do campo senha via contexto não é direto no marshmallow,
        # mas a validação cruzada é feita no handler da rota.
        pass


class SolicitarRecuperacaoSchema(Schema):
    email = fields.Email(required=True, metadata={"description": "E-mail cadastrado"})


class RedefinirSenhaSchema(Schema):
    token = fields.Str(required=True, metadata={"description": "Token recebido no e-mail de recuperação"})
    senha = fields.Str(
        required=True,
        validate=validate.Length(min=8, max=128),
        metadata={"description": "Nova senha (mínimo 8 caracteres)"},
    )
    confirmar_senha = fields.Str(
        required=True,
        metadata={"description": "Confirmação da nova senha"},
    )
