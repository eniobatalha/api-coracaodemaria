"""CRUD da Agenda Escolar — acessível apenas por secretaria e diretoria."""
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, validate, ValidationError

from app.extensions import db
from app.models.evento_escolar import EventoEscolar, CATEGORIAS_VALIDAS
from app.utils.auth_helpers import requer_secretaria

agenda_bp = Blueprint("agenda", __name__)

# ── Schemas ────────────────────────────────────────────────────────────────────

class CriarEventoSchema(Schema):
    titulo    = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    descricao = fields.Str(load_default="")
    data      = fields.Date(required=True)
    categoria = fields.Str(required=True, validate=validate.OneOf(CATEGORIAS_VALIDAS))

_criar = CriarEventoSchema()


# ── Rotas ──────────────────────────────────────────────────────────────────────

@agenda_bp.get("")
@requer_secretaria
def listar_eventos():
    """
    Listar eventos da agenda escolar
    ---
    tags:
      - Agenda Escolar
    summary: Retorna todos os eventos ativos ordenados por data
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: incluir_inativos
        type: boolean
        default: false
    responses:
      200:
        description: Lista de eventos
        schema:
          type: object
          properties:
            eventos:
              type: array
              items:
                type: object
                properties:
                  id:        { type: integer }
                  titulo:    { type: string }
                  descricao: { type: string }
                  data:      { type: string, example: "2026-06-10" }
                  categoria: { type: string, example: "Evento" }
                  ativo:     { type: boolean }
            total: { type: integer }
    """
    incluir_inativos = request.args.get("incluir_inativos", "false").lower() == "true"
    q = db.select(EventoEscolar).order_by(EventoEscolar.data)
    if not incluir_inativos:
        q = q.where(EventoEscolar.ativo == True)

    eventos = db.session.scalars(q).all()
    return jsonify({"eventos": [e.to_dict() for e in eventos], "total": len(eventos)}), 200


@agenda_bp.post("")
@requer_secretaria
def criar_evento():
    """
    Criar evento na agenda escolar
    ---
    tags:
      - Agenda Escolar
    summary: Cadastra um novo evento
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [titulo, data, categoria]
          properties:
            titulo:    { type: string, example: "Reunião de Pais" }
            descricao: { type: string, example: "Reunião do 3º bimestre" }
            data:      { type: string, example: "2026-06-10" }
            categoria: { type: string, example: "Reunião" }
    responses:
      201:
        description: Evento criado
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

    evento = EventoEscolar(
        titulo=dados["titulo"],
        descricao=dados.get("descricao") or "",
        data=dados["data"],
        categoria=dados["categoria"],
    )
    db.session.add(evento)
    db.session.commit()
    db.session.refresh(evento)

    return jsonify({"mensagem": "Evento criado com sucesso", "evento": evento.to_dict()}), 201


@agenda_bp.delete("/<int:evento_id>")
@requer_secretaria
def excluir_evento(evento_id: int):
    """
    Remover evento da agenda
    ---
    tags:
      - Agenda Escolar
    summary: Desativa um evento (soft delete)
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: evento_id
        type: integer
        required: true
    responses:
      200:
        description: Evento removido
      404:
        description: Evento não encontrado
    """
    evento = db.session.get(EventoEscolar, evento_id)
    if not evento:
        return jsonify({"erro": "Evento não encontrado"}), 404

    evento.ativo = False
    db.session.commit()
    return jsonify({"mensagem": "Evento removido com sucesso"}), 200
