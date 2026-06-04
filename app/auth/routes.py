"""
Endpoints de autenticação — Portal do Responsável e Portal do Funcionário.

Todos os endpoints estão documentados com Swagger (Flasgger).
Acesse a documentação interativa em: http://localhost:5000/docs
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.extensions import db
from app.models.responsavel import Responsavel
from app.models.funcionario import Funcionario
from app.auth.schemas import (
    LoginResponsavelSchema,
    LoginFuncionarioSchema,
    ConfirmarContaSchema,
    SolicitarRecuperacaoSchema,
    RedefinirSenhaSchema,
)
from app.utils.email import (
    enviar_confirmacao_responsavel,
    enviar_reset_senha_responsavel,
    enviar_reset_senha_funcionario,
)

auth_bp = Blueprint("auth", __name__)

# ── Instâncias dos schemas ─────────────────────────────────────────────────────
_login_responsavel_schema   = LoginResponsavelSchema()
_login_funcionario_schema   = LoginFuncionarioSchema()
_confirmar_conta_schema     = ConfirmarContaSchema()
_solicitar_recuperacao_schema = SolicitarRecuperacaoSchema()
_redefinir_senha_schema     = RedefinirSenhaSchema()


# ════════════════════════════════════════════════════════════════════════════════
# PORTAL DO RESPONSÁVEL
# ════════════════════════════════════════════════════════════════════════════════

@auth_bp.post("/responsavel/login")
def login_responsavel():
    """
    Login do responsável (pai/mãe/guardião)
    ---
    tags:
      - Auth — Responsável
    summary: Autentica um responsável com e-mail e senha
    description: |
      Realiza o login de um **responsável** (pai, mãe ou guardião) no Portal do Aluno.

      ### Pré-requisitos
      - A conta deve ter sido criada pela secretaria.
      - O responsável deve ter confirmado a conta via link enviado por e-mail
        (endpoint `/auth/responsavel/confirmar-conta`).

      ### Retorno em caso de sucesso
      Retorna um **JWT Bearer Token** válido por 1 hora.
      Use-o no header de requisições protegidas:
      ```
      Authorization: Bearer {access_token}
      ```

      ### Códigos de erro comuns
      | Código | Motivo |
      |--------|--------|
      | 400 | JSON inválido ou campos obrigatórios faltando |
      | 401 | E-mail ou senha incorretos |
      | 403 | Conta não confirmada — o responsável precisa confirmar o e-mail |
      | 403 | Conta desativada — contate a secretaria |
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - senha
          properties:
            email:
              type: string
              format: email
              description: E-mail cadastrado do responsável
              example: larissa.batalha@email.com
            senha:
              type: string
              format: password
              description: Senha da conta (mínimo 6 caracteres)
              example: "minhasenha123"
    responses:
      200:
        description: Login realizado com sucesso
        schema:
          type: object
          properties:
            access_token:
              type: string
              description: JWT Bearer Token para usar em endpoints protegidos
              example: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            token_type:
              type: string
              example: Bearer
            expires_in:
              type: integer
              description: Tempo de expiração do token em segundos
              example: 3600
            responsavel:
              type: object
              description: Dados básicos do responsável autenticado
              properties:
                id:
                  type: integer
                  example: 1
                nome:
                  type: string
                  example: Larissa Barbosa Batalha
                email:
                  type: string
                  example: larissa.batalha@email.com
                email_confirmado:
                  type: boolean
                  example: true
      400:
        description: Dados inválidos na requisição
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Dados inválidos
            detalhes:
              type: object
              example:
                email: ["Not a valid email address."]
      401:
        description: E-mail ou senha incorretos
        schema:
          type: object
          properties:
            erro:
              type: string
              example: E-mail ou senha incorretos
      403:
        description: Conta não confirmada ou desativada
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Conta não confirmada. Verifique seu e-mail para ativar o acesso.
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição inválido ou Content-Type incorreto"}), 400

    try:
        dados = _login_responsavel_schema.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    responsavel = Responsavel.query.filter_by(email=dados["email"].lower()).first()

    if not responsavel or not responsavel.verificar_senha(dados["senha"]):
        return jsonify({"erro": "E-mail ou senha incorretos"}), 401

    if not responsavel.email_confirmado:
        return jsonify({
            "erro": "Conta não confirmada. Verifique seu e-mail para ativar o acesso."
        }), 403

    if not responsavel.ativo:
        return jsonify({
            "erro": "Conta desativada. Entre em contato com a secretaria."
        }), 403

    expires = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    access_token = create_access_token(
        identity=str(responsavel.id),
        additional_claims={"tipo": "responsavel"},
    )

    return jsonify({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": int(expires.total_seconds()),
        "responsavel": responsavel.to_dict(),
    }), 200


@auth_bp.post("/responsavel/confirmar-conta")
def confirmar_conta_responsavel():
    """
    Confirmação de conta do responsável (primeiro acesso)
    ---
    tags:
      - Auth — Responsável
    summary: Confirma a conta e define a senha no primeiro acesso
    description: |
      Ativa a conta do responsável e define sua senha.

      Este endpoint é chamado quando o responsável clica no link de confirmação
      recebido por e-mail após o cadastro feito pela secretaria.

      ### Fluxo completo
      1. Secretaria cadastra o responsável → sistema envia e-mail com link de confirmação
      2. Responsável clica no link → frontend extrai o `token` da URL
      3. Responsável escolhe uma senha → frontend chama este endpoint
      4. Conta ativada → responsável pode fazer login normalmente

      ### Observações
      - O token é válido por **48 horas** após o cadastro.
      - Após o uso, o token é invalidado (não pode ser reutilizado).
      - A senha deve ter no mínimo **8 caracteres**.
      - `senha` e `confirmar_senha` devem ser idênticos.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - token
            - senha
            - confirmar_senha
          properties:
            token:
              type: string
              description: Token recebido no e-mail de confirmação (extraído da URL)
              example: "dG9rZW5fZXhhbXBsZV9hcXVp..."
            senha:
              type: string
              format: password
              description: Nova senha (mínimo 8 caracteres)
              example: "minhaSenhaForte@2025"
            confirmar_senha:
              type: string
              format: password
              description: Confirmação da nova senha (deve ser idêntica ao campo senha)
              example: "minhaSenhaForte@2025"
    responses:
      200:
        description: Conta confirmada com sucesso
        schema:
          type: object
          properties:
            mensagem:
              type: string
              example: Conta confirmada com sucesso. Você já pode fazer login.
      400:
        description: Dados inválidos ou senhas divergentes
        schema:
          type: object
          properties:
            erro:
              type: string
              example: As senhas não coincidem
      404:
        description: Token inválido ou não encontrado
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Token inválido ou não encontrado
      410:
        description: Token expirado
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Token expirado. Solicite um novo link à secretaria.
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição inválido"}), 400

    try:
        dados = _confirmar_conta_schema.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    if dados["senha"] != dados["confirmar_senha"]:
        return jsonify({"erro": "As senhas não coincidem"}), 400

    responsavel = Responsavel.query.filter_by(token_confirmacao=dados["token"]).first()
    if not responsavel:
        return jsonify({"erro": "Token inválido ou não encontrado"}), 404

    if not responsavel.validar_token_confirmacao(dados["token"]):
        return jsonify({
            "erro": "Token expirado. Solicite um novo link de confirmação à secretaria."
        }), 410

    responsavel.set_senha(dados["senha"])
    responsavel.usar_token_confirmacao()
    db.session.commit()

    return jsonify({"mensagem": "Conta confirmada com sucesso. Você já pode fazer login."}), 200


@auth_bp.post("/responsavel/solicitar-recuperacao")
def solicitar_recuperacao_responsavel():
    """
    Solicitar recuperação de senha do responsável
    ---
    tags:
      - Auth — Responsável
    summary: Envia e-mail com link para redefinir a senha
    description: |
      Solicita o envio de um e-mail com link de recuperação de senha.

      ### Comportamento de segurança
      Por segurança, **a resposta é sempre a mesma** independente de o e-mail
      existir ou não no sistema. Isso evita a enumeração de e-mails cadastrados.

      ### Token gerado
      O link enviado contém um token válido por **2 horas**.
      Após o uso, o token é invalidado automaticamente.

      ### Em desenvolvimento
      O e-mail não é enviado. O token é exibido no **console do servidor**
      para facilitar os testes.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
              description: E-mail cadastrado do responsável
              example: larissa.batalha@email.com
    responses:
      200:
        description: Solicitação processada (independente de o e-mail existir)
        schema:
          type: object
          properties:
            mensagem:
              type: string
              example: >
                Se o e-mail estiver cadastrado, você receberá um link de
                recuperação em breve.
      400:
        description: E-mail inválido
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Dados inválidos
            detalhes:
              type: object
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição inválido"}), 400

    try:
        dados = _solicitar_recuperacao_schema.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    responsavel = Responsavel.query.filter_by(email=dados["email"].lower()).first()

    if responsavel and responsavel.ativo and responsavel.email_confirmado:
        horas = current_app.config["TOKEN_RESET_SENHA_EXPIRACAO_HORAS"]
        token = responsavel.gerar_token_reset_senha(horas=horas)
        db.session.commit()
        enviar_reset_senha_responsavel(responsavel.nome, responsavel.email, token)

    return jsonify({
        "mensagem": (
            "Se o e-mail estiver cadastrado e a conta estiver ativa, "
            "você receberá um link de recuperação em breve."
        )
    }), 200


@auth_bp.post("/responsavel/redefinir-senha")
def redefinir_senha_responsavel():
    """
    Redefinir senha do responsável
    ---
    tags:
      - Auth — Responsável
    summary: Redefine a senha usando o token recebido por e-mail
    description: |
      Redefine a senha do responsável usando o token enviado por e-mail
      no endpoint `/auth/responsavel/solicitar-recuperacao`.

      ### Observações
      - O token é válido por **2 horas** após a solicitação.
      - Após o uso, o token é invalidado (não pode ser reutilizado).
      - A nova senha deve ter no mínimo **8 caracteres**.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - token
            - senha
            - confirmar_senha
          properties:
            token:
              type: string
              description: Token recebido no e-mail de recuperação
              example: "dG9rZW5fZXhhbXBsZV9hcXVp..."
            senha:
              type: string
              format: password
              description: Nova senha (mínimo 8 caracteres)
              example: "novaSenhaForte@2025"
            confirmar_senha:
              type: string
              format: password
              description: Confirmação da nova senha
              example: "novaSenhaForte@2025"
    responses:
      200:
        description: Senha redefinida com sucesso
        schema:
          type: object
          properties:
            mensagem:
              type: string
              example: Senha redefinida com sucesso. Você já pode fazer login com a nova senha.
      400:
        description: Dados inválidos ou senhas divergentes
        schema:
          type: object
          properties:
            erro:
              type: string
              example: As senhas não coincidem
      404:
        description: Token inválido ou não encontrado
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Token inválido ou não encontrado
      410:
        description: Token expirado
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Token expirado. Solicite uma nova recuperação de senha.
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição inválido"}), 400

    try:
        dados = _redefinir_senha_schema.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    if dados["senha"] != dados["confirmar_senha"]:
        return jsonify({"erro": "As senhas não coincidem"}), 400

    responsavel = Responsavel.query.filter_by(token_reset_senha=dados["token"]).first()
    if not responsavel:
        return jsonify({"erro": "Token inválido ou não encontrado"}), 404

    if not responsavel.validar_token_reset_senha(dados["token"]):
        return jsonify({
            "erro": "Token expirado. Solicite uma nova recuperação de senha."
        }), 410

    responsavel.set_senha(dados["senha"])
    responsavel.usar_token_reset_senha()
    db.session.commit()

    return jsonify({
        "mensagem": "Senha redefinida com sucesso. Você já pode fazer login com a nova senha."
    }), 200


@auth_bp.get("/responsavel/perfil")
@jwt_required()
def perfil_responsavel():
    """
    Dados do responsável autenticado
    ---
    tags:
      - Auth — Responsável
    summary: Retorna os dados do responsável logado
    description: |
      Retorna as informações básicas do responsável correspondente ao
      JWT Bearer Token informado no header.

      ### Autenticação obrigatória
      Inclua o token no header:
      ```
      Authorization: Bearer {access_token}
      ```
    security:
      - BearerAuth: []
    responses:
      200:
        description: Dados do responsável autenticado
        schema:
          type: object
          properties:
            responsavel:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                nome:
                  type: string
                  example: Larissa Barbosa Batalha
                email:
                  type: string
                  example: larissa.batalha@email.com
                email_confirmado:
                  type: boolean
                  example: true
                ativo:
                  type: boolean
                  example: true
                criado_em:
                  type: string
                  format: date-time
                  example: "2026-01-15T10:30:00+00:00"
      401:
        description: Token ausente, inválido ou expirado
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Token ausente ou inválido
    """
    identity = get_jwt_identity()
    responsavel = Responsavel.query.get(int(identity))

    if not responsavel or not responsavel.ativo:
        return jsonify({"erro": "Responsável não encontrado ou inativo"}), 404

    return jsonify({"responsavel": responsavel.to_dict()}), 200


# ════════════════════════════════════════════════════════════════════════════════
# PORTAL DO FUNCIONÁRIO
# ════════════════════════════════════════════════════════════════════════════════

@auth_bp.post("/funcionario/login")
def login_funcionario():
    """
    Login do funcionário (professor, secretária ou diretora)
    ---
    tags:
      - Auth — Funcionário
    summary: Autentica um funcionário com usuário e senha
    description: |
      Realiza o login de um **funcionário** no Portal do Funcionário.

      ### Formato do usuário
      O nome de usuário segue o padrão `nome.sobrenome`, por exemplo:
      - `luana.marcela` — Professora
      - `luana.silveira` — Secretária
      - `rosa.paz` — Diretora

      ### Perfis disponíveis (`tipo`)
      | Valor | Descrição |
      |-------|-----------|
      | `professor` | Acesso às turmas, lançamento de notas e frequência |
      | `secretaria` | Acesso a cadastros, comunicados, agenda e financeiro |
      | `diretora` | Acesso completo (secretaria + dashboard financeiro) |

      ### Retorno em caso de sucesso
      Retorna um **JWT Bearer Token** válido por 1 hora e os dados do funcionário,
      incluindo o `tipo` (papel) para o frontend decidir o menu de navegação.

      ### Códigos de erro comuns
      | Código | Motivo |
      |--------|--------|
      | 400 | JSON inválido ou campos obrigatórios faltando |
      | 401 | Usuário ou senha incorretos |
      | 403 | Conta desativada — contate a administração |
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - usuario
            - senha
          properties:
            usuario:
              type: string
              description: Nome de usuário no formato nome.sobrenome
              example: luana.marcela
            senha:
              type: string
              format: password
              description: Senha da conta (mínimo 6 caracteres)
              example: "123456"
    responses:
      200:
        description: Login realizado com sucesso
        schema:
          type: object
          properties:
            access_token:
              type: string
              description: JWT Bearer Token para usar em endpoints protegidos
              example: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            token_type:
              type: string
              example: Bearer
            expires_in:
              type: integer
              description: Tempo de expiração em segundos
              example: 3600
            funcionario:
              type: object
              description: Dados do funcionário autenticado
              properties:
                id:
                  type: integer
                  example: 1
                nome:
                  type: string
                  example: Luana Marcela
                usuario:
                  type: string
                  example: luana.marcela
                email:
                  type: string
                  example: luana.marcela@coracaodemaria.edu.br
                cargo:
                  type: string
                  example: Professora
                tipo:
                  type: string
                  enum: [professor, secretaria, diretora]
                  example: professor
                ativo:
                  type: boolean
                  example: true
      400:
        description: Dados inválidos na requisição
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Dados inválidos
            detalhes:
              type: object
      401:
        description: Usuário ou senha incorretos
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Usuário ou senha incorretos
      403:
        description: Conta desativada
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Conta desativada. Entre em contato com a administração.
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição inválido ou Content-Type incorreto"}), 400

    try:
        dados = _login_funcionario_schema.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    funcionario = Funcionario.query.filter_by(usuario=dados["usuario"].lower()).first()

    if not funcionario or not funcionario.verificar_senha(dados["senha"]):
        return jsonify({"erro": "Usuário ou senha incorretos"}), 401

    if not funcionario.ativo:
        return jsonify({
            "erro": "Conta desativada. Entre em contato com a administração."
        }), 403

    expires = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    access_token = create_access_token(
        identity=str(funcionario.id),
        additional_claims={
            "tipo": "funcionario",
            "role": funcionario.tipo.value,
        },
    )

    return jsonify({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": int(expires.total_seconds()),
        "funcionario": funcionario.to_dict(),
    }), 200


@auth_bp.post("/funcionario/solicitar-recuperacao")
def solicitar_recuperacao_funcionario():
    """
    Solicitar recuperação de senha do funcionário
    ---
    tags:
      - Auth — Funcionário
    summary: Envia e-mail com link para redefinir a senha
    description: |
      Solicita o envio de um e-mail com link de recuperação de senha para o funcionário.

      ### Comportamento de segurança
      A resposta é **sempre a mesma** independente de o e-mail existir ou não,
      para evitar enumeração de usuários.

      ### Token gerado
      O link é válido por **2 horas**.

      ### Em desenvolvimento
      O e-mail não é enviado. O token aparece no **console do servidor**.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
          properties:
            email:
              type: string
              format: email
              description: E-mail do funcionário cadastrado pela secretaria
              example: luana.marcela@coracaodemaria.edu.br
    responses:
      200:
        description: Solicitação processada
        schema:
          type: object
          properties:
            mensagem:
              type: string
              example: >
                Se o e-mail estiver cadastrado, você receberá um link de
                recuperação em breve.
      400:
        description: E-mail inválido
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Dados inválidos
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição inválido"}), 400

    try:
        dados = _solicitar_recuperacao_schema.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    funcionario = Funcionario.query.filter_by(email=dados["email"].lower()).first()

    if funcionario and funcionario.ativo:
        horas = current_app.config["TOKEN_RESET_SENHA_EXPIRACAO_HORAS"]
        token = funcionario.gerar_token_reset_senha(horas=horas)
        db.session.commit()
        enviar_reset_senha_funcionario(funcionario.nome, funcionario.email, token)

    return jsonify({
        "mensagem": (
            "Se o e-mail estiver cadastrado e a conta estiver ativa, "
            "você receberá um link de recuperação em breve."
        )
    }), 200


@auth_bp.post("/funcionario/redefinir-senha")
def redefinir_senha_funcionario():
    """
    Redefinir senha do funcionário
    ---
    tags:
      - Auth — Funcionário
    summary: Redefine a senha usando o token recebido por e-mail
    description: |
      Redefine a senha do funcionário usando o token enviado por e-mail.

      ### Observações
      - Token válido por **2 horas**.
      - Após o uso, o token é invalidado.
      - Nova senha com mínimo de **8 caracteres**.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - token
            - senha
            - confirmar_senha
          properties:
            token:
              type: string
              description: Token recebido no e-mail de recuperação
              example: "dG9rZW5fZXhhbXBsZV9hcXVp..."
            senha:
              type: string
              format: password
              description: Nova senha (mínimo 8 caracteres)
              example: "novaSenhaForte@2025"
            confirmar_senha:
              type: string
              format: password
              description: Confirmação da nova senha
              example: "novaSenhaForte@2025"
    responses:
      200:
        description: Senha redefinida com sucesso
        schema:
          type: object
          properties:
            mensagem:
              type: string
              example: Senha redefinida com sucesso.
      400:
        description: Dados inválidos ou senhas divergentes
        schema:
          type: object
          properties:
            erro:
              type: string
              example: As senhas não coincidem
      404:
        description: Token inválido ou não encontrado
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Token inválido ou não encontrado
      410:
        description: Token expirado
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Token expirado. Solicite uma nova recuperação de senha.
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição inválido"}), 400

    try:
        dados = _redefinir_senha_schema.load(dados)
    except ValidationError as e:
        return jsonify({"erro": "Dados inválidos", "detalhes": e.messages}), 400

    if dados["senha"] != dados["confirmar_senha"]:
        return jsonify({"erro": "As senhas não coincidem"}), 400

    funcionario = Funcionario.query.filter_by(token_reset_senha=dados["token"]).first()
    if not funcionario:
        return jsonify({"erro": "Token inválido ou não encontrado"}), 404

    if not funcionario.validar_token_reset_senha(dados["token"]):
        return jsonify({
            "erro": "Token expirado. Solicite uma nova recuperação de senha."
        }), 410

    funcionario.set_senha(dados["senha"])
    funcionario.usar_token_reset_senha()
    db.session.commit()

    return jsonify({"mensagem": "Senha redefinida com sucesso."}), 200


@auth_bp.get("/funcionario/perfil")
@jwt_required()
def perfil_funcionario():
    """
    Dados do funcionário autenticado
    ---
    tags:
      - Auth — Funcionário
    summary: Retorna os dados do funcionário logado
    description: |
      Retorna as informações do funcionário correspondente ao JWT Bearer Token.

      ### Autenticação obrigatória
      ```
      Authorization: Bearer {access_token}
      ```
    security:
      - BearerAuth: []
    responses:
      200:
        description: Dados do funcionário autenticado
        schema:
          type: object
          properties:
            funcionario:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                nome:
                  type: string
                  example: Luana Marcela
                usuario:
                  type: string
                  example: luana.marcela
                email:
                  type: string
                  example: luana.marcela@coracaodemaria.edu.br
                cargo:
                  type: string
                  example: Professora
                tipo:
                  type: string
                  enum: [professor, secretaria, diretora]
                  example: professor
                ativo:
                  type: boolean
                  example: true
                criado_em:
                  type: string
                  format: date-time
                  example: "2026-01-10T08:00:00+00:00"
      401:
        description: Token ausente, inválido ou expirado
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Token ausente ou inválido
      404:
        description: Funcionário não encontrado
        schema:
          type: object
          properties:
            erro:
              type: string
              example: Funcionário não encontrado ou inativo
    """
    identity = get_jwt_identity()
    funcionario = Funcionario.query.get(int(identity))

    if not funcionario or not funcionario.ativo:
        return jsonify({"erro": "Funcionário não encontrado ou inativo"}), 404

    return jsonify({"funcionario": funcionario.to_dict()}), 200


# ════════════════════════════════════════════════════════════════════════════════
# CONFIRMAÇÃO DE TROCA DE E-MAIL (endpoint público — responsável clica no link)
# ════════════════════════════════════════════════════════════════════════════════

@auth_bp.post("/responsavel/confirmar-troca-email")
def confirmar_troca_email():
    """
    Confirmar troca de e-mail do responsável
    ---
    tags:
      - Auth — Responsável
    summary: Confirma o novo e-mail usando o token recebido
    description: |
      Endpoint público chamado quando o responsável clica no link de confirmação
      de troca de e-mail enviado pela secretaria.

      Após a confirmação, o `email` passa a ser o `email_pendente` e o login
      passa a funcionar com o novo endereço.

      ### Token
      Gerado pela secretaria via `POST /api/v1/responsaveis/{id}/alterar-email`.
      Válido por 48 horas.
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [token]
          properties:
            token:
              type: string
              description: Token recebido no e-mail de troca
              example: "dG9rZW5fZXhhbXBsZV9hcXVp..."
    responses:
      200:
        description: E-mail trocado com sucesso
        schema:
          type: object
          properties:
            mensagem: { type: string, example: "E-mail atualizado com sucesso. Faça login com o novo endereço." }
      400:
        description: Token ausente
      404:
        description: Token inválido ou não encontrado
      410:
        description: Token expirado
    """
    dados = request.get_json(silent=True) or {}
    token = str(dados.get("token", "")).strip()
    if not token:
        return jsonify({"erro": "Token obrigatório"}), 400

    resp = Responsavel.query.filter_by(token_troca_email=token).first()
    if not resp:
        return jsonify({"erro": "Token inválido ou não encontrado"}), 404

    if not resp.validar_token_troca_email(token):
        return jsonify({"erro": "Token expirado. Solicite uma nova troca de e-mail à secretaria."}), 410

    resp.confirmar_troca_email()
    db.session.commit()

    return jsonify({"mensagem": "E-mail atualizado com sucesso. Faça login com o novo endereço."}), 200
