"""Importa todos os models para que o Alembic os detecte automaticamente."""
from .responsavel import Responsavel
from .funcionario import Funcionario, TipoFuncionario
from .turma import Turma
from .aluno import Aluno

__all__ = ["Responsavel", "Funcionario", "TipoFuncionario", "Turma", "Aluno"]
