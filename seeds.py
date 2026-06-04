"""
Comandos CLI para popular o banco com dados de desenvolvimento.

Uso:
    flask seed dev      — cria todos os dados de teste (espelha os mocks do frontend)
    flask seed limpar   — remove todos os dados das tabelas principais
"""
import click
from flask import current_app
from flask.cli import with_appcontext

from app.extensions import db
from app.models.responsavel import Responsavel
from app.models.funcionario import Funcionario, TipoFuncionario
from app.models.turma import Turma
from app.models.aluno import Aluno


@click.group()
def seed():
    """Comandos para popular o banco de dados."""
    pass


@seed.command("dev")
@with_appcontext
def seed_dev():
    """
    Cria dados de desenvolvimento espelhando os mocks do frontend.

    Cria na ordem correta: funcionários → responsáveis → turmas → alunos.
    """
    # ── 1. Funcionários ───────────────────────────────────────────────────────
    _funcionarios = [
        dict(nome="Rosa Paz",       usuario="rosa.paz",       email="rosa.paz@coracaodemaria.edu.br",       cargo="Diretora",   tipo=TipoFuncionario.diretora,   senha="123456"),
        dict(nome="Luana Silveira", usuario="luana.silveira", email="luana.silveira@coracaodemaria.edu.br", cargo="Secretária", tipo=TipoFuncionario.secretaria, senha="123456"),
        dict(nome="Luana Marcela",  usuario="luana.marcela",  email="luana.marcela@coracaodemaria.edu.br",  cargo="Professora", tipo=TipoFuncionario.professor,  senha="123456"),
        dict(nome="Paula Virgínia", usuario="paula.virginia", email="paula.virginia@coracaodemaria.edu.br", cargo="Professora", tipo=TipoFuncionario.professor,  senha="123456"),
    ]
    criados_f = 0
    for f in _funcionarios:
        if not Funcionario.query.filter_by(usuario=f["usuario"]).first():
            func_ = Funcionario(nome=f["nome"], usuario=f["usuario"], email=f["email"], cargo=f["cargo"], tipo=f["tipo"])
            func_.set_senha(f["senha"])
            db.session.add(func_)
            criados_f += 1
    db.session.flush()  # garante IDs disponíveis antes das turmas

    # ── 2. Responsáveis ───────────────────────────────────────────────────────
    _responsaveis = [
        dict(nome="Larissa Barbosa Batalha",  email="larissa.batalha@email.com", senha="123456"),
        dict(nome="Fernanda Souza Lima",       email="fernanda.lima@email.com",   senha="123456"),
        dict(nome="Carlos Ferreira Costa",     email="carlos.costa@email.com",    senha="123456"),
        dict(nome="Patrícia Menezes Ramos",    email="patricia.ramos@email.com",  senha="123456"),
        dict(nome="Roberto Cavalcanti Braga",  email="roberto.braga@email.com",   senha="123456"),
        dict(nome="Juliana Almeida Santos",    email="juliana.santos@email.com",  senha="123456"),
    ]
    criados_r = 0
    for r in _responsaveis:
        if not Responsavel.query.filter_by(email=r["email"]).first():
            resp = Responsavel(nome=r["nome"], email=r["email"])
            resp.set_senha(r["senha"])
            resp.email_confirmado = True
            db.session.add(resp)
            criados_r += 1
    db.session.flush()

    # ── 3. Turmas ─────────────────────────────────────────────────────────────
    luana   = Funcionario.query.filter_by(usuario="luana.marcela").first()
    paula   = Funcionario.query.filter_by(usuario="paula.virginia").first()

    _turmas = [
        dict(serie="1º Ano", turma="A", turno="Manhã", unidade="Gaibu", label="1º Ano A — Manhã", professor=luana),
        dict(serie="1º Ano", turma="B", turno="Tarde", unidade="Gaibu", label="1º Ano B — Tarde", professor=luana),
        dict(serie="4º Ano", turma="A", turno="Manhã", unidade="Cabo",  label="4º Ano A — Manhã", professor=paula),
    ]
    criados_t = 0
    for t in _turmas:
        if not Turma.query.filter_by(label=t["label"]).first():
            turma = Turma(
                serie=t["serie"], turma=t["turma"], turno=t["turno"],
                unidade=t["unidade"], label=t["label"],
                professor_id=t["professor"].id if t["professor"] else None,
            )
            db.session.add(turma)
            criados_t += 1
    db.session.flush()

    # ── 4. Alunos ─────────────────────────────────────────────────────────────
    t1a = Turma.query.filter_by(label="1º Ano A — Manhã").first()
    t1b = Turma.query.filter_by(label="1º Ano B — Tarde").first()
    t4a = Turma.query.filter_by(label="4º Ano A — Manhã").first()

    larissa   = Responsavel.query.filter_by(email="larissa.batalha@email.com").first()
    fernanda  = Responsavel.query.filter_by(email="fernanda.lima@email.com").first()
    carlos    = Responsavel.query.filter_by(email="carlos.costa@email.com").first()
    patricia  = Responsavel.query.filter_by(email="patricia.ramos@email.com").first()
    roberto   = Responsavel.query.filter_by(email="roberto.braga@email.com").first()
    juliana   = Responsavel.query.filter_by(email="juliana.santos@email.com").first()

    _alunos = [
        dict(nome="Dionísio Barbosa Batalha",  genero="M", matricula="363", turma=t4a, responsavel=larissa),
        dict(nome="Hera Barbosa Batalha",       genero="F", matricula="262", turma=t1b, responsavel=larissa),
        dict(nome="Valentina Souza Lima",        genero="F", matricula="271", turma=t1a, responsavel=fernanda),
        dict(nome="Miguel Ferreira Costa",       genero="M", matricula="274", turma=t1a, responsavel=carlos),
        dict(nome="Isabella Menezes Ramos",      genero="F", matricula="278", turma=t1a, responsavel=patricia),
        dict(nome="Théo Cavalcanti Braga",       genero="M", matricula="265", turma=t1b, responsavel=roberto),
        dict(nome="Sofia Almeida Santos",        genero="F", matricula="268", turma=t1b, responsavel=juliana),
    ]
    criados_a = 0
    for a in _alunos:
        if not Aluno.query.filter_by(matricula=a["matricula"]).first():
            aluno = Aluno(
                nome=a["nome"], genero=a["genero"], matricula=a["matricula"],
                turma_id=a["turma"].id if a["turma"] else None,
                responsavel_id=a["responsavel"].id if a["responsavel"] else None,
            )
            db.session.add(aluno)
            criados_a += 1

    db.session.commit()

    click.secho("\n✅  Seeds aplicados com sucesso!", fg="green", bold=True)
    click.echo(f"   Funcionários : {criados_f}")
    click.echo(f"   Responsáveis : {criados_r}")
    click.echo(f"   Turmas       : {criados_t}")
    click.echo(f"   Alunos       : {criados_a}")
    click.echo("\n📋  Credenciais de teste:")
    click.echo("   Funcionários  → rosa.paz / luana.silveira / luana.marcela / paula.virginia  |  senha: 123456")
    click.echo("   Responsáveis  → larissa.batalha@email.com (e demais)                        |  senha: 123456\n")


@seed.command("limpar")
@with_appcontext
def seed_limpar():
    """Remove todos os dados principais (somente dev!)."""
    if not current_app.debug:
        click.secho("❌  Este comando só pode ser executado em modo DEBUG.", fg="red")
        return

    confirmacao = click.prompt("Digite 'CONFIRMAR' para apagar todos os dados", type=str)
    if confirmacao != "CONFIRMAR":
        click.echo("Operação cancelada.")
        return

    Aluno.query.delete()
    Turma.query.delete()
    Responsavel.query.delete()
    Funcionario.query.delete()
    db.session.commit()
    click.secho("✅  Todos os dados removidos.", fg="yellow")


def register_commands(app):
    app.cli.add_command(seed)
