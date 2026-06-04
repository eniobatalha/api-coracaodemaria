"""Model de Comunicado — avisos enviados pela secretaria para responsáveis."""
from app.extensions import db


class Comunicado(db.Model):
    __tablename__ = "comunicados"

    id                 = db.Column(db.Integer, primary_key=True)
    titulo             = db.Column(db.String(200), nullable=False)
    conteudo           = db.Column(db.Text, nullable=False)
    urgente            = db.Column(db.Boolean, default=False, nullable=False)
    destinatario       = db.Column(db.String(50), nullable=False, default="all")
    destinatario_label = db.Column(db.String(100), nullable=False, default="Todos os alunos")
    ativo              = db.Column(db.Boolean, default=True, nullable=False)
    criado_em          = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    def __repr__(self) -> str:
        return f"<Comunicado {self.titulo!r}>"

    def to_dict(self) -> dict:
        return {
            "id":                 self.id,
            "titulo":             self.titulo,
            "conteudo":           self.conteudo,
            "urgente":            self.urgente,
            "destinatario":       self.destinatario,
            "destinatario_label": self.destinatario_label,
            "ativo":              self.ativo,
            "criado_em":          self.criado_em.isoformat() if self.criado_em else None,
        }
