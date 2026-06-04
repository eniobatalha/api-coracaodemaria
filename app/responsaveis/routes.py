"""CRUD de responsáveis — acessível apenas por secretaria e diretoria."""
from flask import Blueprint, request, jsonify, current_app
from marshmallow import Schema, fields, validate, ValidationError

from app.extensions import db
from app.models.responsavel import Responsavel
from app.utils.auth_helpers import requer_secretaria
from app.utils.email import (
    enviar_confirmacao_responsavel,
    enviar_troca_email_responsavel,
)

responsaveis_bp = Blueprint("responsaveis", __name__)


# ── Schemas ────────────────────────────────────────────────────────────────────

class CriarResponsavelSchema(Schema):
    nome  = fields.Str(required=True, validate=validate.Length(min=3, max=200))
    email = fields.Email(required=True)

class EditarNomeSchema(Schema):
    nome = fields.Str(required=True, validate=validate.Length(min=3, max=200))

class AlterarEmailSchema(Schema):
    novo_email = fields.Email(required=True)

_criar       = CriarResponsavelSchema()
_editar_nome = EditarNomeSchema()
_alterar_email = AlterarEmailSchema()


# ── Rotas ─────────────────────────────────────────────────────────────────────

@responsaveis_bp.get("")
@requer_secretaria
def listar_responsaveis():
    """
    Listar responsáveis
    ---
    tags:
      - Responsáveis
    summary: Retorna todos os responsáveis com status de e-mail
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: incluir_inativos
        type: boolean
        default: false
    responses:
      200:
        description: Lista de responsáveis
        schema:
          type: object
          properties:
            responsaveis:
              type: array
              items:
                type: object
                properties:
                  id:               { type: integer }
                  nome:             { type: string }
                  email:            { type: string }
                  email_confirmado: { type: boolean }
                  email_pendente:   { type: string, description: "Novo e-mail aguardando confirmação" }
                  status_email:
                    type: string
                    enum: [confirmado, aguardando, troca_pendente]
                    description: |
                      confirmado    — conta ativa e e-mail verificado
                      aguardando    — link de ativação ainda não clicado
                      troca_pendente — novo e-mail aguardando confirmação
                  ativo: { type: boolean }
            total: { type: integer }
    """
    incluir_inativos = request.args.get("incluir_inativos", "false").lower() == "true"
    q = db.select(Responsavel).order_by(Responsavel.nome)
    if not incluir_inativos:
        q = q.where(Responsavel.ativo == True)

    resp = db.session.scalars(q).all()
    return jsonify({"responsaveis": [r.to_dict() for r in resp], "total": len(resp)}), 200


@responsaveis_bp.post("")
@requer_secretaria
def criar_responsavel():
    """
    Criar responsável
    ---
    tags:
      - Responsáveis
    summary: Cria o cadastro e envia link de ativação por e-mail
    description: |
      Cria o responsável com a conta inativa (`status_email: aguardando`).
      Um e-mail com link de ativação é enviado automaticamente para o endereço informado.

      O responsável clica no link, define sua senha e a conta é ativada.

      ### Em desenvolvimento
      O e-mail não é enviado — o **token aparece no console do servidor**.
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [nome, email]
          properties:
            nome:  { type: string, example: Ana Barbosa }
            email: { type: string, example: ana.barbosa@email.com }
    responses:
      201:
        description: Responsável criado e e-mail de ativação enviado
        schema:
          type: object
          properties:
            mensagem:     { type: string }
            responsavel:  { type: object }
      400:
        description: Dados inválidos ou e-mail já cadastrado
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo inválido"}), 400

    try:
        dados = _criar.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    if Responsavel.query.filter_by(email=dados["email"].lower()).first():
        return jsonify({"erro": f"E-mail '{dados['email']}' já está cadastrado"}), 400

    resp = Responsavel(nome=dados["nome"], email=dados["email"].lower())
    horas = current_app.config["TOKEN_CONFIRMACAO_EXPIRACAO_HORAS"]
    token = resp.gerar_token_confirmacao(horas=horas)
    db.session.add(resp)
    db.session.commit()

    enviar_confirmacao_responsavel(resp.nome, resp.email, token)

    return jsonify({
        "mensagem": f"Responsável criado. Link de ativação enviado para {resp.email}.",
        "responsavel": resp.to_dict(),
    }), 201


@responsaveis_bp.get("/<int:resp_id>")
@requer_secretaria
def obter_responsavel(resp_id: int):
    """
    Obter responsável por ID
    ---
    tags:
      - Responsáveis
    summary: Retorna dados completos de um responsável
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: resp_id
        type: integer
        required: true
    responses:
      200:
        description: Dados do responsável
      404:
        description: Responsável não encontrado
    """
    resp = db.session.get(Responsavel, resp_id)
    if not resp:
        return jsonify({"erro": "Responsável não encontrado"}), 404
    return jsonify({"responsavel": resp.to_dict()}), 200


@responsaveis_bp.put("/<int:resp_id>")
@requer_secretaria
def editar_nome_responsavel(resp_id: int):
    """
    Editar nome do responsável
    ---
    tags:
      - Responsáveis
    summary: Atualiza apenas o nome do responsável
    description: |
      Para alterar o e-mail, use o endpoint dedicado
      `POST /api/v1/responsaveis/{id}/alterar-email`.
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: resp_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [nome]
          properties:
            nome: { type: string, example: Ana Beatriz Barbosa }
    responses:
      200:
        description: Nome atualizado
      404:
        description: Responsável não encontrado
    """
    resp = db.session.get(Responsavel, resp_id)
    if not resp:
        return jsonify({"erro": "Responsável não encontrado"}), 404

    dados = request.get_json(silent=True) or {}
    try:
        dados = _editar_nome.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    resp.nome = dados["nome"]
    db.session.commit()
    return jsonify({"mensagem": "Nome atualizado", "responsavel": resp.to_dict()}), 200


@responsaveis_bp.post("/<int:resp_id>/reenviar-confirmacao")
@requer_secretaria
def reenviar_confirmacao(resp_id: int):
    """
    Reenviar e-mail de confirmação / ativação
    ---
    tags:
      - Responsáveis
    summary: Reenvia o e-mail de ativação (ou de troca, se houver uma pendente)
    description: |
      - Se `status_email = aguardando`: gera novo token e reenvia e-mail de ativação.
      - Se `status_email = troca_pendente`: reenvia o e-mail de troca para `email_pendente`.
      - Se `status_email = confirmado` (sem troca pendente): retorna erro 422.

      ### Em desenvolvimento
      O link aparece no console do servidor.
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: resp_id
        type: integer
        required: true
    responses:
      200:
        description: E-mail reenviado
      404:
        description: Responsável não encontrado
      422:
        description: Conta já confirmada e sem troca pendente — nada a reenviar
    """
    resp = db.session.get(Responsavel, resp_id)
    if not resp:
        return jsonify({"erro": "Responsável não encontrado"}), 404

    horas_conf  = current_app.config["TOKEN_CONFIRMACAO_EXPIRACAO_HORAS"]

    if resp.email_pendente:
        # Reenviar e-mail de troca
        token = resp.gerar_token_troca_email(resp.email_pendente, horas=horas_conf)
        db.session.commit()
        enviar_troca_email_responsavel(resp.nome, resp.email_pendente, token)
        return jsonify({
            "mensagem": f"E-mail de troca reenviado para {resp.email_pendente}."
        }), 200

    if not resp.email_confirmado:
        # Reenviar e-mail de ativação inicial
        token = resp.gerar_token_confirmacao(horas=horas_conf)
        db.session.commit()
        enviar_confirmacao_responsavel(resp.nome, resp.email, token)
        return jsonify({
            "mensagem": f"E-mail de ativação reenviado para {resp.email}."
        }), 200

    return jsonify({
        "erro": "A conta já está confirmada e não há troca de e-mail pendente."
    }), 422


@responsaveis_bp.post("/<int:resp_id>/alterar-email")
@requer_secretaria
def alterar_email(resp_id: int):
    """
    Alterar e-mail do responsável
    ---
    tags:
      - Responsáveis
    summary: Inicia o processo de troca de e-mail
    description: |
      O comportamento depende do estado atual da conta:

      ### Antes de confirmar (`status_email = aguardando`)
      O e-mail ainda não foi verificado — pode ter sido digitado errado.
      Neste caso a troca é **direta**: o e-mail é atualizado imediatamente e
      um novo link de ativação é enviado para o novo endereço.

      ### Após confirmar (`status_email = confirmado`)
      O novo endereço fica em `email_pendente` e um **link de confirmação de troca**
      é enviado para lá. Enquanto o responsável não clicar, o login continua
      funcionando com o e-mail antigo. Quando confirmar, o e-mail é trocado.

      ### Em desenvolvimento
      O link aparece no console do servidor.
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: resp_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [novo_email]
          properties:
            novo_email: { type: string, format: email, example: novo@email.com }
    responses:
      200:
        description: E-mail processado (ver mensagem para detalhes)
        schema:
          type: object
          properties:
            mensagem:    { type: string }
            responsavel: { type: object }
      400:
        description: E-mail inválido ou já em uso
      404:
        description: Responsável não encontrado
    """
    resp = db.session.get(Responsavel, resp_id)
    if not resp:
        return jsonify({"erro": "Responsável não encontrado"}), 404

    dados = request.get_json(silent=True) or {}
    try:
        dados = _alterar_email.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    novo = dados["novo_email"].lower()

    if novo == resp.email:
        return jsonify({"erro": "O novo e-mail é igual ao e-mail atual."}), 400

    # Verifica se já não está em uso por outro responsável
    outro = Responsavel.query.filter(
        Responsavel.email == novo,
        Responsavel.id != resp_id,
    ).first()
    if outro:
        return jsonify({"erro": f"O e-mail '{novo}' já está cadastrado para outro responsável."}), 400

    horas = current_app.config["TOKEN_CONFIRMACAO_EXPIRACAO_HORAS"]

    if not resp.email_confirmado:
        # Troca direta — conta ainda não foi ativada
        resp.email = novo
        resp.limpar_troca_email()
        token = resp.gerar_token_confirmacao(horas=horas)
        db.session.commit()
        enviar_confirmacao_responsavel(resp.nome, novo, token)
        return jsonify({
            "mensagem": f"E-mail atualizado para {novo}. Novo link de ativação enviado.",
            "responsavel": resp.to_dict(),
        }), 200

    # Conta já confirmada — troca com confirmação pelo novo e-mail
    token = resp.gerar_token_troca_email(novo, horas=horas)
    db.session.commit()
    enviar_troca_email_responsavel(resp.nome, novo, token)
    return jsonify({
        "mensagem": f"Link de confirmação enviado para {novo}. O e-mail atual permanece ativo até a confirmação.",
        "responsavel": resp.to_dict(),
    }), 200


@responsaveis_bp.delete("/<int:resp_id>")
@requer_secretaria
def excluir_responsavel(resp_id: int):
    """
    Desativar responsável
    ---
    tags:
      - Responsáveis
    summary: Desativa um responsável (soft delete)
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: resp_id
        type: integer
        required: true
    responses:
      200:
        description: Responsável desativado
      404:
        description: Responsável não encontrado
    """
    resp = db.session.get(Responsavel, resp_id)
    if not resp:
        return jsonify({"erro": "Responsável não encontrado"}), 404

    resp.ativo = False
    db.session.commit()
    return jsonify({"mensagem": f"Responsável '{resp.nome}' desativado com sucesso"}), 200
