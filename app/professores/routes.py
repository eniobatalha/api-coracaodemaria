"""CRUD de professores — acessível apenas por secretaria e diretoria."""
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, validate, ValidationError
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.funcionario import Funcionario, TipoFuncionario
from app.utils.auth_helpers import requer_secretaria

professores_bp = Blueprint("professores", __name__)


# ── Schemas ────────────────────────────────────────────────────────────────────

class CriarProfessorSchema(Schema):
    nome    = fields.Str(required=True, validate=validate.Length(min=3, max=200))
    usuario = fields.Str(required=True, validate=validate.Length(min=3, max=100))
    email   = fields.Email(required=True)
    cargo   = fields.Str(load_default="Professor(a)", validate=validate.Length(max=100))
    senha   = fields.Str(required=True, validate=validate.Length(min=6, max=128))

class EditarProfessorSchema(Schema):
    nome    = fields.Str(validate=validate.Length(min=3, max=200))
    usuario = fields.Str(validate=validate.Length(min=3, max=100))
    email   = fields.Email()
    cargo   = fields.Str(validate=validate.Length(max=100))
    senha   = fields.Str(validate=validate.Length(min=6, max=128))  # opcional
    ativo   = fields.Bool()

_criar  = CriarProfessorSchema()
_editar = EditarProfessorSchema()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prof_query():
    return (
        db.select(Funcionario)
        .where(Funcionario.tipo == TipoFuncionario.professor)
        .order_by(Funcionario.nome)
    )


# ── Rotas ─────────────────────────────────────────────────────────────────────

@professores_bp.get("")
@requer_secretaria
def listar_professores():
    """
    Listar todos os professores
    ---
    tags:
      - Professores
    summary: Retorna a lista de professores ativos
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: incluir_inativos
        type: boolean
        default: false
        description: Se true, inclui professores desativados
    responses:
      200:
        description: Lista de professores
        schema:
          type: object
          properties:
            professores:
              type: array
              items:
                type: object
                properties:
                  id:       { type: integer, example: 3 }
                  nome:     { type: string,  example: Luana Marcela }
                  usuario:  { type: string,  example: luana.marcela }
                  email:    { type: string,  example: luana.marcela@escola.edu.br }
                  cargo:    { type: string,  example: Professora }
                  ativo:    { type: boolean, example: true }
            total: { type: integer, example: 2 }
      401:
        description: Token ausente ou inválido
      403:
        description: Acesso restrito à secretaria/diretoria
    """
    incluir_inativos = request.args.get("incluir_inativos", "false").lower() == "true"
    q = _prof_query()
    if not incluir_inativos:
        q = q.where(Funcionario.ativo == True)

    profs = db.session.scalars(q).all()
    return jsonify({"professores": [p.to_dict() for p in profs], "total": len(profs)}), 200


@professores_bp.post("")
@requer_secretaria
def criar_professor():
    """
    Criar professor
    ---
    tags:
      - Professores
    summary: Cria um novo professor com login e senha definidos pela secretaria
    description: |
      A secretaria é responsável por criar o login (`usuario`) e a senha inicial do professor.
      O professor usará essas credenciais para acessar o Portal do Funcionário.

      ### Regras
      - `usuario` deve ser único (formato sugerido: `nome.sobrenome`)
      - `email` deve ser único
      - `senha` mínimo 6 caracteres
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [nome, usuario, email, senha]
          properties:
            nome:    { type: string, example: Maria da Silva }
            usuario: { type: string, example: maria.silva }
            email:   { type: string, example: maria.silva@escola.edu.br }
            cargo:   { type: string, example: Professora, description: "Padrão: Professor(a)" }
            senha:   { type: string, example: senha123 }
    responses:
      201:
        description: Professor criado com sucesso
        schema:
          type: object
          properties:
            mensagem:   { type: string }
            professor:  { type: object }
      400:
        description: Dados inválidos ou usuário/e-mail já existem
      403:
        description: Acesso negado
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo inválido"}), 400

    try:
        dados = _criar.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    if Funcionario.query.filter_by(usuario=dados["usuario"].lower()).first():
        return jsonify({"erro": f"Usuário '{dados['usuario']}' já existe"}), 400
    if Funcionario.query.filter_by(email=dados["email"].lower()).first():
        return jsonify({"erro": f"E-mail '{dados['email']}' já está em uso"}), 400

    prof = Funcionario(
        nome=dados["nome"],
        usuario=dados["usuario"].lower(),
        email=dados["email"].lower(),
        cargo=dados["cargo"],
        tipo=TipoFuncionario.professor,
    )
    prof.set_senha(dados["senha"])
    db.session.add(prof)
    db.session.commit()

    return jsonify({"mensagem": "Professor criado com sucesso", "professor": prof.to_dict()}), 201


@professores_bp.get("/<int:professor_id>")
@requer_secretaria
def obter_professor(professor_id: int):
    """
    Obter professor por ID
    ---
    tags:
      - Professores
    summary: Retorna os dados de um professor específico
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: professor_id
        type: integer
        required: true
        example: 3
    responses:
      200:
        description: Dados do professor + turmas que leciona
        schema:
          type: object
          properties:
            professor: { type: object }
      404:
        description: Professor não encontrado
    """
    prof = db.session.scalar(
        db.select(Funcionario)
        .options(selectinload(Funcionario.turmas_lecionadas))
        .where(Funcionario.id == professor_id, Funcionario.tipo == TipoFuncionario.professor)
    )
    if not prof:
        return jsonify({"erro": "Professor não encontrado"}), 404

    dados = prof.to_dict()
    dados["turmas"] = [t.to_dict() for t in prof.turmas_lecionadas if t.ativo]
    return jsonify({"professor": dados}), 200


@professores_bp.put("/<int:professor_id>")
@requer_secretaria
def editar_professor(professor_id: int):
    """
    Editar professor
    ---
    tags:
      - Professores
    summary: Atualiza dados do professor (incluindo login e senha opcionalmente)
    description: |
      Todos os campos são opcionais. Envie apenas os que deseja alterar.

      Para redefinir a senha do professor, inclua o campo `senha` no body.
      Se `senha` for omitido, a senha atual permanece inalterada.
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: professor_id
        type: integer
        required: true
        example: 3
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            nome:    { type: string }
            usuario: { type: string }
            email:   { type: string }
            cargo:   { type: string }
            senha:   { type: string, description: "Opcional — redefine a senha" }
            ativo:   { type: boolean }
    responses:
      200:
        description: Professor atualizado
        schema:
          type: object
          properties:
            mensagem:  { type: string }
            professor: { type: object }
      400:
        description: Dados inválidos
      404:
        description: Professor não encontrado
    """
    prof = db.session.get(Funcionario, professor_id)
    if not prof or prof.tipo != TipoFuncionario.professor:
        return jsonify({"erro": "Professor não encontrado"}), 404

    dados = request.get_json(silent=True) or {}
    try:
        dados = _editar.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    if "usuario" in dados and dados["usuario"].lower() != prof.usuario:
        if Funcionario.query.filter_by(usuario=dados["usuario"].lower()).first():
            return jsonify({"erro": f"Usuário '{dados['usuario']}' já existe"}), 400
        prof.usuario = dados["usuario"].lower()

    if "email" in dados and dados["email"].lower() != prof.email:
        if Funcionario.query.filter_by(email=dados["email"].lower()).first():
            return jsonify({"erro": f"E-mail '{dados['email']}' já está em uso"}), 400
        prof.email = dados["email"].lower()

    if "nome"  in dados: prof.nome  = dados["nome"]
    if "cargo" in dados: prof.cargo = dados["cargo"]
    if "ativo" in dados: prof.ativo = dados["ativo"]
    if "senha" in dados: prof.set_senha(dados["senha"])

    db.session.commit()
    return jsonify({"mensagem": "Professor atualizado", "professor": prof.to_dict()}), 200


@professores_bp.delete("/<int:professor_id>")
@requer_secretaria
def excluir_professor(professor_id: int):
    """
    Desativar professor
    ---
    tags:
      - Professores
    summary: Desativa um professor (soft delete — não remove do banco)
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: professor_id
        type: integer
        required: true
        example: 3
    responses:
      200:
        description: Professor desativado
      404:
        description: Professor não encontrado
    """
    prof = db.session.get(Funcionario, professor_id)
    if not prof or prof.tipo != TipoFuncionario.professor:
        return jsonify({"erro": "Professor não encontrado"}), 404

    prof.ativo = False
    db.session.commit()
    return jsonify({"mensagem": f"Professor '{prof.nome}' desativado com sucesso"}), 200
