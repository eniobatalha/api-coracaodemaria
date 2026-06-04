"""Model do Evento Escolar — agenda de eventos, reuniões, provas e feriados."""
from app.extensions import db

CATEGORIAS_VALIDAS = ["Evento", "Reunião", "Prova", "Entrega", "Feriado"]


class EventoEscolar(db.Model):
    __tablename__ = "eventos_escolares"

    id        = db.Column(db.Integer, primary_key=True)
    titulo    = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    data      = db.Column(db.Date, nullable=False)
    categoria = db.Column(db.String(20), nullable=False)
    ativo     = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    def __repr__(self) -> str:
        return f"<EventoEscolar {self.data} — {self.titulo}>"

    def to_dict(self) -> dict:
        return {
            "id":        self.id,
            "titulo":    self.titulo,
            "descricao": self.descricao or "",
            "data":      self.data.isoformat() if self.data else None,
            "categoria": self.categoria,
            "ativo":     self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }
