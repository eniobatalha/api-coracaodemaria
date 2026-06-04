"""CRUD de Comunicados — acessível apenas por secretaria e diretoria."""
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, validate, ValidationError

from app.extensions import db
from app.models.comunicado import Comunicado
from app.utils.auth_helpers import requer_secretaria

comunicados_bp = Blueprint("comunicados", __name__)

# ── Schemas ────────────────────────────────────────────────────────────────────

class CriarComunicadoSchema(Schema):
    titulo             = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    conteudo           = fields.Str(required=True, validate=validate.Length(min=1))
    urgente            = fields.Bool(load_default=False)
    destinatario       = fields.Str(load_default="all", validate=validate.Length(max=50))
    destinatario_label = fields.Str(load_default="Todos os alunos", validate=validate.Length(max=100))

_criar = CriarComunicadoSchema()


# ── Rotas ──────────────────────────────────────────────────────────────────────

@comunicados_bp.get("")
@requer_secretaria
def listar_comunicados():
    """
    Listar comunicados
    ---
    tags:
      - Comunicados
    summary: Retorna todos os comunicados ativos, do mais recente ao mais antigo
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: incluir_inativos
        type: boolean
        default: false
    responses:
      200:
        description: Lista de comunicados
        schema:
          type: object
          properties:
            comunicados:
              type: array
              items:
                type: object
                properties:
                  id:                 { type: integer }
                  titulo:             { type: string }
                  conteudo:           { type: string }
                  urgente:            { type: boolean }
                  destinatario:       { type: string }
                  destinatario_label: { type: string }
                  ativo:              { type: boolean }
                  criado_em:          { type: string }
            total: { type: integer }
    """
    incluir_inativos = request.args.get("incluir_inativos", "false").lower() == "true"
    q = db.select(Comunicado).order_by(Comunicado.criado_em.desc())
    if not incluir_inativos:
        q = q.where(Comunicado.ativo == True)

    comunicados = db.session.scalars(q).all()
    return jsonify({"comunicados": [c.to_dict() for c in comunicados], "total": len(comunicados)}), 200


@comunicados_bp.post("")
@requer_secretaria
def criar_comunicado():
    """
    Publicar comunicado
    ---
    tags:
      - Comunicados
    summary: Publica um novo comunicado para os responsáveis
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [titulo, conteudo]
          properties:
            titulo:             { type: string, example: "Reunião de Pais — 10/06" }
            conteudo:           { type: string, example: "A reunião acontecerá..." }
            urgente:            { type: boolean, example: false }
            destinatario:       { type: string, example: "all" }
            destinatario_label: { type: string, example: "Todos os alunos" }
    responses:
      201:
        description: Comunicado publicado
      400:
        description: Dados inválidos
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo inválido"}), 400

    try:
        dados = _criar.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    comunicado = Comunicado(
        titulo=dados["titulo"],
        conteudo=dados["conteudo"],
        urgente=dados.get("urgente", False),
        destinatario=dados.get("destinatario", "all"),
        destinatario_label=dados.get("destinatario_label", "Todos os alunos"),
    )
    db.session.add(comunicado)
    db.session.commit()
    db.session.refresh(comunicado)

    return jsonify({"mensagem": "Comunicado publicado com sucesso", "comunicado": comunicado.to_dict()}), 201


@comunicados_bp.delete("/<int:comunicado_id>")
@requer_secretaria
def excluir_comunicado(comunicado_id: int):
    """
    Remover comunicado
    ---
    tags:
      - Comunicados
    summary: Desativa um comunicado (soft delete)
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: comunicado_id
        type: integer
        required: true
    responses:
      200:
        description: Comunicado removido
      404:
        description: Comunicado não encontrado
    """
    comunicado = db.session.get(Comunicado, comunicado_id)
    if not comunicado:
        return jsonify({"erro": "Comunicado não encontrado"}), 404

    comunicado.ativo = False
    db.session.commit()
    return jsonify({"mensagem": "Comunicado removido com sucesso"}), 200
