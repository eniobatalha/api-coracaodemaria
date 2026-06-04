"""Model do Aluno — vinculado a uma turma e a um responsável."""
from app.extensions import db


class Aluno(db.Model):
    __tablename__ = "alunos"

    id           = db.Column(db.Integer,      primary_key=True)
    nome         = db.Column(db.String(200),  nullable=False)
    genero       = db.Column(db.String(1),    nullable=False)   # "M" | "F"
    matricula    = db.Column(db.String(20),   unique=True, nullable=False, index=True)
    turma_id     = db.Column(
        db.Integer,
        db.ForeignKey("turmas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    responsavel_id = db.Column(
        db.Integer,
        db.ForeignKey("responsaveis.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    turma = db.relationship(
        "Turma",
        foreign_keys=[turma_id],
        backref=db.backref("alunos_matriculados", lazy="select"),
    )
    responsavel = db.relationship(
        "Responsavel",
        foreign_keys=[responsavel_id],
        backref=db.backref("alunos", lazy="select"),
    )

    ativo         = db.Column(db.Boolean, default=True, nullable=False)
    criado_em     = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    atualizado_em = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())

    def __repr__(self) -> str:
        return f"<Aluno {self.nome} mat={self.matricula}>"

    def to_dict(self, include_related: bool = False) -> dict:
        d: dict = {
            "id":            self.id,
            "nome":          self.nome,
            "genero":        self.genero,
            "matricula":     self.matricula,
            "turma_id":      self.turma_id,
            "responsavel_id": self.responsavel_id,
            "ativo":         self.ativo,
            "criado_em":     self.criado_em.isoformat() if self.criado_em else None,
        }
        if include_related:
            d["turma"] = self.turma.to_dict() if self.turma else None
            d["responsavel"] = (
                {"id": self.responsavel.id, "nome": self.responsavel.nome, "email": self.responsavel.email}
                if self.responsavel else None
            )
        return d
