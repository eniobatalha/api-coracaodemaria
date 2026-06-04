"""Decoradores de autorização por papel (role)."""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def requer_secretaria(f):
    """Exige JWT de funcionário com role secretaria ou diretora."""
    @wraps(f)
    def decorated(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("tipo") != "funcionario":
            return jsonify({"erro": "Acesso restrito a funcionários"}), 403
        if claims.get("role") not in ("secretaria", "diretora"):
            return jsonify({"erro": "Acesso restrito à secretaria e diretoria"}), 403
        return f(*args, **kwargs)
    return decorated
