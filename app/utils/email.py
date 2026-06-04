"""Utilitários de envio de e-mail.

Em desenvolvimento (MAIL_SUPPRESS_SEND=True), os e-mails são apenas logados
no console em vez de enviados. Em produção, configure o SMTP no .env.
"""
import logging
from flask import current_app
from flask_mail import Message
from app.extensions import mail

logger = logging.getLogger(__name__)


def _log_email_dev(assunto: str, destinatario: str, corpo: str) -> None:
    """Loga o conteúdo do e-mail no console durante o desenvolvimento."""
    separador = "─" * 60
    logger.info(
        "\n%s\n📧 E-MAIL (modo dev — não enviado)\nPara: %s\nAssunto: %s\n%s\n%s\n%s",
        separador, destinatario, assunto, separador, corpo, separador,
    )
    print(
        f"\n{separador}\n"
        f"📧  E-MAIL (modo dev — não enviado)\n"
        f"Para:    {destinatario}\n"
        f"Assunto: {assunto}\n"
        f"{separador}\n"
        f"{corpo}\n"
        f"{separador}\n"
    )


def enviar_confirmacao_responsavel(nome: str, email: str, token: str) -> None:
    """Envia o e-mail de confirmação de conta para o responsável."""
    frontend_url = current_app.config["FRONTEND_URL"]
    horas = current_app.config["TOKEN_CONFIRMACAO_EXPIRACAO_HORAS"]
    link = f"{frontend_url}/confirmar-conta?token={token}"

    assunto = "Bem-vindo ao Portal Coração de Maria — Confirme sua conta"
    corpo = f"""Olá, {nome}!

Sua conta no Portal do Responsável do Colégio Coração de Maria foi criada.

Para definir sua senha e acessar o portal, clique no link abaixo:

  {link}

Este link é válido por {horas} horas.

Caso não tenha solicitado este cadastro, ignore este e-mail.

Atenciosamente,
Secretaria — Colégio e Curso Coração de Maria
"""

    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        _log_email_dev(assunto, email, corpo)
        return

    mail.send(Message(assunto, recipients=[email], body=corpo))


def enviar_reset_senha_responsavel(nome: str, email: str, token: str) -> None:
    """Envia o e-mail de recuperação de senha para o responsável."""
    frontend_url = current_app.config["FRONTEND_URL"]
    horas = current_app.config["TOKEN_RESET_SENHA_EXPIRACAO_HORAS"]
    link = f"{frontend_url}/redefinir-senha?token={token}"

    assunto = "Redefinição de senha — Portal Coração de Maria"
    corpo = f"""Olá, {nome}!

Recebemos uma solicitação de redefinição de senha para a sua conta no Portal do Responsável.

Para criar uma nova senha, clique no link abaixo:

  {link}

Este link é válido por {horas} horas.

Se você não solicitou a redefinição de senha, ignore este e-mail. Sua senha atual permanece inalterada.

Atenciosamente,
Secretaria — Colégio e Curso Coração de Maria
"""

    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        _log_email_dev(assunto, email, corpo)
        return

    mail.send(Message(assunto, recipients=[email], body=corpo))


def enviar_reset_senha_funcionario(nome: str, email: str, token: str) -> None:
    """Envia o e-mail de recuperação de senha para um funcionário."""
    frontend_url = current_app.config["FRONTEND_URL"]
    horas = current_app.config["TOKEN_RESET_SENHA_EXPIRACAO_HORAS"]
    link = f"{frontend_url}/portal-funcionario/redefinir-senha?token={token}"

    assunto = "Redefinição de senha — Portal do Funcionário Coração de Maria"
    corpo = f"""Olá, {nome}!

Recebemos uma solicitação de redefinição de senha para a sua conta no Portal do Funcionário.

Para criar uma nova senha, clique no link abaixo:

  {link}

Este link é válido por {horas} horas.

Se você não solicitou a redefinição de senha, ignore este e-mail.

Atenciosamente,
TI — Colégio e Curso Coração de Maria
"""

    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        _log_email_dev(assunto, email, corpo)
        return

    mail.send(Message(assunto, recipients=[email], body=corpo))


def enviar_troca_email_responsavel(nome: str, email_novo: str, token: str) -> None:
    """Envia confirmação de troca de e-mail para o novo endereço do responsável."""
    frontend_url = current_app.config["FRONTEND_URL"]
    horas = current_app.config["TOKEN_CONFIRMACAO_EXPIRACAO_HORAS"]
    link = f"{frontend_url}/portal/confirmar-troca-email?token={token}"

    assunto = "Confirme a troca de e-mail — Portal Coração de Maria"
    corpo = f"""Olá, {nome}!

A secretaria do Colégio Coração de Maria registrou uma alteração de e-mail na sua conta.
Este endereço ({email_novo}) foi indicado como o novo e-mail de acesso ao Portal do Responsável.

Para confirmar a troca, clique no link abaixo:

  {link}

Este link é válido por {horas} horas.

Se você não reconhece esta solicitação, entre em contato com a secretaria da escola.

Atenciosamente,
Secretaria — Colégio e Curso Coração de Maria
"""

    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        _log_email_dev(assunto, email_novo, corpo)
        return

    mail.send(Message(assunto, recipients=[email_novo], body=corpo))
