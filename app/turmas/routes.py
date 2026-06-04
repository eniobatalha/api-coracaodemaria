"""CRUD de turmas — acessível apenas por secretaria e diretoria."""
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, validate, ValidationError
from sqlalchemy.orm import selectinload

from sqlalchemy import func

from app.extensions import db
from app.models.turma import Turma
from app.models.aluno import Aluno
from app.models.funcionario import Funcionario, TipoFuncionario
from app.utils.auth_helpers import requer_secretaria

turmas_bp = Blueprint("turmas", __name__)

SERIES_VALIDAS = [
    "Maternal I","Maternal II","Pré I","Pré II",
    "1º Ano","2º Ano","3º Ano","4º Ano","5º Ano",
    "6º Ano","7º Ano","8º Ano","9º Ano",
    "1º Médio","2º Médio","3º Médio",
]
LETRAS_VALIDAS  = ["A","B","C","D"]
TURNOS_VALIDOS  = ["Manhã","Tarde"]
UNIDADES_VALIDAS = ["Cabo","Gaibu"]


# ── Schemas ────────────────────────────────────────────────────────────────────

class CriarTurmaSchema(Schema):
    serie       = fields.Str(required=True, validate=validate.OneOf(SERIES_VALIDAS))
    turma       = fields.Str(required=True, validate=validate.OneOf(LETRAS_VALIDAS))
    turno       = fields.Str(required=True, validate=validate.OneOf(TURNOS_VALIDOS))
    unidade     = fields.Str(required=True, validate=validate.OneOf(UNIDADES_VALIDAS))
    professor_id = fields.Int(load_default=None)

class EditarTurmaSchema(Schema):
    serie       = fields.Str(validate=validate.OneOf(SERIES_VALIDAS))
    turma       = fields.Str(validate=validate.OneOf(LETRAS_VALIDAS))
    turno       = fields.Str(validate=validate.OneOf(TURNOS_VALIDOS))
    unidade     = fields.Str(validate=validate.OneOf(UNIDADES_VALIDAS))
    professor_id = fields.Int(allow_none=True)
    ativo       = fields.Bool()

_criar  = CriarTurmaSchema()
_editar = EditarTurmaSchema()


def _make_label(serie: str, turma: str, turno: str) -> str:
    return f"{serie} {turma} — {turno}"


# ── Rotas ─────────────────────────────────────────────────────────────────────

@turmas_bp.get("")
@requer_secretaria
def listar_turmas():
    """
    Listar turmas
    ---
    tags:
      - Turmas
    summary: Retorna todas as turmas ativas com dados do professor vinculado
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: incluir_inativos
        type: boolean
        default: false
    responses:
      200:
        description: Lista de turmas
        schema:
          type: object
          properties:
            turmas:
              type: array
              items:
                type: object
                properties:
                  id:           { type: integer }
                  serie:        { type: string, example: "1º Ano" }
                  turma:        { type: string, example: A }
                  turno:        { type: string, example: "Manhã" }
                  unidade:      { type: string, example: Gaibu }
                  label:        { type: string, example: "1º Ano A — Manhã" }
                  professor_id: { type: integer }
                  professor:    { type: object }
                  ativo:        { type: boolean }
            total: { type: integer }
    """
    incluir_inativos = request.args.get("incluir_inativos", "false").lower() == "true"
    q = (
        db.select(Turma)
        .options(selectinload(Turma.professor))
        .order_by(Turma.serie, Turma.turma, Turma.turno)
    )
    if not incluir_inativos:
        q = q.where(Turma.ativo == True)

    turmas = db.session.scalars(q).all()

    # Contagem de alunos por turma em uma única query (sem N+1)
    counts: dict[int, int] = dict(
        db.session.execute(
            db.select(Aluno.turma_id, func.count(Aluno.id))
            .where(Aluno.ativo == True, Aluno.turma_id != None)
            .group_by(Aluno.turma_id)
        ).all()
    )

    result = []
    for t in turmas:
        td = t.to_dict(include_professor=True)
        td["total_alunos"] = counts.get(t.id, 0)
        result.append(td)

    return jsonify({"turmas": result, "total": len(result)}), 200


@turmas_bp.post("")
@requer_secretaria
def criar_turma():
    """
    Criar turma
    ---
    tags:
      - Turmas
    summary: Cria uma nova turma e associa a um professor (opcional)
    description: |
      O `label` é gerado automaticamente no formato `{serie} {turma} — {turno}`.

      O `professor_id` deve ser o ID de um funcionário com `tipo = professor`.
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [serie, turma, turno, unidade]
          properties:
            serie:        { type: string, example: "1º Ano" }
            turma:        { type: string, example: A }
            turno:        { type: string, example: "Manhã" }
            unidade:      { type: string, example: Gaibu }
            professor_id: { type: integer, example: 3 }
    responses:
      201:
        description: Turma criada
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

    if dados.get("professor_id"):
        prof = db.session.get(Funcionario, dados["professor_id"])
        if not prof or prof.tipo != TipoFuncionario.professor:
            return jsonify({"erro": "professor_id inválido — professor não encontrado"}), 400

    turma = Turma(
        serie=dados["serie"],
        turma=dados["turma"],
        turno=dados["turno"],
        unidade=dados["unidade"],
        label=_make_label(dados["serie"], dados["turma"], dados["turno"]),
        professor_id=dados.get("professor_id"),
    )
    db.session.add(turma)
    db.session.commit()
    db.session.refresh(turma)

    # Carrega professor para incluir no retorno
    if turma.professor_id:
        db.session.refresh(turma, ["professor"])

    return jsonify({
        "mensagem": "Turma criada com sucesso",
        "turma": turma.to_dict(include_professor=True),
    }), 201


@turmas_bp.get("/<int:turma_id>")
@requer_secretaria
def obter_turma(turma_id: int):
    """
    Obter turma por ID
    ---
    tags:
      - Turmas
    summary: Retorna dados de uma turma com professor e contagem de alunos
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: turma_id
        type: integer
        required: true
    responses:
      200:
        description: Dados da turma
      404:
        description: Turma não encontrada
    """
    turma = db.session.scalar(
        db.select(Turma)
        .options(selectinload(Turma.professor), selectinload(Turma.alunos_matriculados))
        .where(Turma.id == turma_id)
    )
    if not turma:
        return jsonify({"erro": "Turma não encontrada"}), 404

    dados = turma.to_dict(include_professor=True)
    dados["total_alunos"] = sum(1 for a in turma.alunos_matriculados if a.ativo)
    return jsonify({"turma": dados}), 200


@turmas_bp.put("/<int:turma_id>")
@requer_secretaria
def editar_turma(turma_id: int):
    """
    Editar turma
    ---
    tags:
      - Turmas
    summary: Atualiza dados de uma turma (inclusive troca de professor)
    description: |
      Todos os campos são opcionais. O `label` é recalculado automaticamente
      sempre que `serie`, `turma` ou `turno` forem alterados.

      Para remover o professor vinculado, envie `"professor_id": null`.
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: turma_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            serie:        { type: string }
            turma:        { type: string }
            turno:        { type: string }
            unidade:      { type: string }
            professor_id: { type: integer, description: "null para remover professor" }
            ativo:        { type: boolean }
    responses:
      200:
        description: Turma atualizada
      400:
        description: Dados inválidos
      404:
        description: Turma não encontrada
    """
    turma = db.session.get(Turma, turma_id)
    if not turma:
        return jsonify({"erro": "Turma não encontrada"}), 404

    dados = request.get_json(silent=True) or {}
    try:
        dados = _editar.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    if "professor_id" in dados:
        pid = dados["professor_id"]
        if pid is not None:
            prof = db.session.get(Funcionario, pid)
            if not prof or prof.tipo != TipoFuncionario.professor:
                return jsonify({"erro": "professor_id inválido"}), 400
        turma.professor_id = pid

    if "serie"   in dados: turma.serie   = dados["serie"]
    if "turma"   in dados: turma.turma   = dados["turma"]
    if "turno"   in dados: turma.turno   = dados["turno"]
    if "unidade" in dados: turma.unidade = dados["unidade"]
    if "ativo"   in dados: turma.ativo   = dados["ativo"]

    turma.label = _make_label(turma.serie, turma.turma, turma.turno)
    db.session.commit()

    return jsonify({"mensagem": "Turma atualizada", "turma": turma.to_dict(include_professor=True)}), 200


@turmas_bp.delete("/<int:turma_id>")
@requer_secretaria
def excluir_turma(turma_id: int):
    """
    Desativar turma
    ---
    tags:
      - Turmas
    summary: Desativa uma turma (soft delete)
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: turma_id
        type: integer
        required: true
    responses:
      200:
        description: Turma desativada
      404:
        description: Turma não encontrada
    """
    turma = db.session.get(Turma, turma_id)
    if not turma:
        return jsonify({"erro": "Turma não encontrada"}), 404

    turma.ativo = False
    db.session.commit()
    return jsonify({"mensagem": f"Turma '{turma.label}' desativada com sucesso"}), 200
