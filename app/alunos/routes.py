"""CRUD de alunos — acessível apenas por secretaria e diretoria."""
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, validate, ValidationError
from sqlalchemy import func, cast, Integer as SAInt
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.aluno import Aluno
from app.models.turma import Turma
from app.models.responsavel import Responsavel
from app.utils.auth_helpers import requer_secretaria

alunos_bp = Blueprint("alunos", __name__)


# ── Schemas ────────────────────────────────────────────────────────────────────

class CriarAlunoSchema(Schema):
    nome            = fields.Str(required=True, validate=validate.Length(min=3, max=200))
    genero          = fields.Str(required=True, validate=validate.OneOf(["M","F"]))
    turma_id        = fields.Int(load_default=None)
    responsavel_id  = fields.Int(load_default=None)

class EditarAlunoSchema(Schema):
    nome            = fields.Str(validate=validate.Length(min=3, max=200))
    genero          = fields.Str(validate=validate.OneOf(["M","F"]))
    turma_id        = fields.Int(allow_none=True)
    responsavel_id  = fields.Int(allow_none=True)
    ativo           = fields.Bool()

_criar  = CriarAlunoSchema()
_editar = EditarAlunoSchema()


def _proximo_matricula() -> str:
    """Retorna a próxima matrícula disponível (maior existente + 1, mínimo 401)."""
    max_mat = db.session.scalar(
        db.select(func.max(cast(Aluno.matricula, SAInt)))
    ) or 400
    return str(max_mat + 1)


# ── Rotas ─────────────────────────────────────────────────────────────────────

@alunos_bp.get("")
@requer_secretaria
def listar_alunos():
    """
    Listar alunos
    ---
    tags:
      - Alunos
    summary: Retorna todos os alunos ativos com turma e responsável
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: turma_id
        type: integer
        description: Filtrar por turma específica
      - in: query
        name: incluir_inativos
        type: boolean
        default: false
    responses:
      200:
        description: Lista de alunos
        schema:
          type: object
          properties:
            alunos:
              type: array
              items:
                type: object
                properties:
                  id:            { type: integer }
                  nome:          { type: string }
                  genero:        { type: string, enum: [M, F] }
                  matricula:     { type: string }
                  turma_id:      { type: integer }
                  turma:         { type: object }
                  responsavel_id: { type: integer }
                  responsavel:   { type: object }
                  ativo:         { type: boolean }
            total: { type: integer }
    """
    incluir_inativos = request.args.get("incluir_inativos", "false").lower() == "true"
    turma_id_filtro  = request.args.get("turma_id", type=int)

    q = (
        db.select(Aluno)
        .options(selectinload(Aluno.turma), selectinload(Aluno.responsavel))
        .order_by(Aluno.nome)
    )
    if not incluir_inativos:
        q = q.where(Aluno.ativo == True)
    if turma_id_filtro:
        q = q.where(Aluno.turma_id == turma_id_filtro)

    alunos = db.session.scalars(q).all()
    return jsonify({
        "alunos": [a.to_dict(include_related=True) for a in alunos],
        "total":  len(alunos),
    }), 200


@alunos_bp.post("")
@requer_secretaria
def criar_aluno():
    """
    Criar aluno
    ---
    tags:
      - Alunos
    summary: Cria um novo aluno com matrícula gerada automaticamente
    description: |
      A **matrícula** é gerada automaticamente em ordem crescente.

      O `turma_id` e o `responsavel_id` são opcionais — podem ser associados depois via PUT.
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [nome, genero]
          properties:
            nome:           { type: string, example: João Pedro da Silva }
            genero:         { type: string, enum: [M, F], example: M }
            turma_id:       { type: integer, example: 1 }
            responsavel_id: { type: integer, example: 2 }
    responses:
      201:
        description: Aluno criado com matrícula gerada
        schema:
          type: object
          properties:
            mensagem: { type: string }
            aluno:    { type: object }
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

    if dados.get("turma_id") and not db.session.get(Turma, dados["turma_id"]):
        return jsonify({"erro": "turma_id inválido"}), 400
    if dados.get("responsavel_id") and not db.session.get(Responsavel, dados["responsavel_id"]):
        return jsonify({"erro": "responsavel_id inválido"}), 400

    aluno = Aluno(
        nome=dados["nome"],
        genero=dados["genero"],
        matricula=_proximo_matricula(),
        turma_id=dados.get("turma_id"),
        responsavel_id=dados.get("responsavel_id"),
    )
    db.session.add(aluno)
    db.session.commit()

    return jsonify({
        "mensagem": f"Aluno criado com matrícula {aluno.matricula}",
        "aluno": aluno.to_dict(include_related=True),
    }), 201


@alunos_bp.get("/<int:aluno_id>")
@requer_secretaria
def obter_aluno(aluno_id: int):
    """
    Obter aluno por ID
    ---
    tags:
      - Alunos
    summary: Retorna dados completos de um aluno
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: aluno_id
        type: integer
        required: true
    responses:
      200:
        description: Dados do aluno
      404:
        description: Aluno não encontrado
    """
    aluno = db.session.scalar(
        db.select(Aluno)
        .options(selectinload(Aluno.turma), selectinload(Aluno.responsavel))
        .where(Aluno.id == aluno_id)
    )
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado"}), 404

    return jsonify({"aluno": aluno.to_dict(include_related=True)}), 200


@alunos_bp.put("/<int:aluno_id>")
@requer_secretaria
def editar_aluno(aluno_id: int):
    """
    Editar aluno
    ---
    tags:
      - Alunos
    summary: Atualiza dados do aluno (inclusive troca de turma ou responsável)
    description: |
      Todos os campos são opcionais.

      Para remover a turma ou responsável, envie o respectivo campo como `null`.
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: aluno_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            nome:           { type: string }
            genero:         { type: string, enum: [M, F] }
            turma_id:       { type: integer, description: "null para desassociar" }
            responsavel_id: { type: integer, description: "null para desassociar" }
            ativo:          { type: boolean }
    responses:
      200:
        description: Aluno atualizado
      400:
        description: Dados inválidos
      404:
        description: Aluno não encontrado
    """
    aluno = db.session.get(Aluno, aluno_id)
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado"}), 404

    dados = request.get_json(silent=True) or {}
    try:
        dados = _editar.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    if "turma_id" in dados:
        tid = dados["turma_id"]
        if tid is not None and not db.session.get(Turma, tid):
            return jsonify({"erro": "turma_id inválido"}), 400
        aluno.turma_id = tid

    if "responsavel_id" in dados:
        rid = dados["responsavel_id"]
        if rid is not None and not db.session.get(Responsavel, rid):
            return jsonify({"erro": "responsavel_id inválido"}), 400
        aluno.responsavel_id = rid

    if "nome"   in dados: aluno.nome   = dados["nome"]
    if "genero" in dados: aluno.genero = dados["genero"]
    if "ativo"  in dados: aluno.ativo  = dados["ativo"]

    db.session.commit()
    return jsonify({"mensagem": "Aluno atualizado", "aluno": aluno.to_dict(include_related=True)}), 200


@alunos_bp.delete("/<int:aluno_id>")
@requer_secretaria
def excluir_aluno(aluno_id: int):
    """
    Desativar aluno
    ---
    tags:
      - Alunos
    summary: Desativa um aluno (soft delete)
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: aluno_id
        type: integer
        required: true
    responses:
      200:
        description: Aluno desativado
      404:
        description: Aluno não encontrado
    """
    aluno = db.session.get(Aluno, aluno_id)
    if not aluno:
        return jsonify({"erro": "Aluno não encontrado"}), 404

    aluno.ativo = False
    db.session.commit()
    return jsonify({"mensagem": f"Aluno '{aluno.nome}' desativado com sucesso"}), 200
