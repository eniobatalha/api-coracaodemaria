"""Importa todos os models para que o Alembic os detecte automaticamente."""
from .responsavel import Responsavel
from .funcionario import Funcionario, TipoFuncionario
from .turma import Turma
from .aluno import Aluno
from .evento_escolar import EventoEscolar
from .comunicado import Comunicado

__all__ = ["Responsavel", "Funcionario", "TipoFuncionario", "Turma", "Aluno",
           "EventoEscolar", "Comunicado"]
