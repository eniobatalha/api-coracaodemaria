"""Model da Turma — associa série, turno, unidade e professor."""
from app.extensions import db


class Turma(db.Model):
    __tablename__ = "turmas"

    id          = db.Column(db.Integer, primary_key=True)
    serie       = db.Column(db.String(50),  nullable=False)   # "1º Ano", "2º Ano"…
    turma       = db.Column(db.String(5),   nullable=False)   # "A", "B", "C"
    turno       = db.Column(db.String(10),  nullable=False)   # "Manhã" | "Tarde"
    unidade     = db.Column(db.String(20),  nullable=False)   # "Cabo" | "Gaibu"
    label       = db.Column(db.String(100), nullable=False)   # "1º Ano A — Manhã"
    professor_id = db.Column(
        db.Integer,
        db.ForeignKey("funcionarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    professor = db.relationship(
        "Funcionario",
        foreign_keys=[professor_id],
        backref=db.backref("turmas_lecionadas", lazy="select"),
    )

    ativo      = db.Column(db.Boolean, default=True, nullable=False)
    criado_em  = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    atualizado_em = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())

    def __repr__(self) -> str:
        return f"<Turma {self.label}>"

    def to_dict(self, include_professor: bool = False) -> dict:
        d: dict = {
            "id":           self.id,
            "serie":        self.serie,
            "turma":        self.turma,
            "turno":        self.turno,
            "unidade":      self.unidade,
            "label":        self.label,
            "professor_id": self.professor_id,
            "ativo":        self.ativo,
            "criado_em":    self.criado_em.isoformat() if self.criado_em else None,
        }
        if include_professor:
            d["professor"] = (
                {"id": self.professor.id, "nome": self.professor.nome}
                if self.professor else None
            )
        return d
