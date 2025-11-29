from flask import Blueprint, jsonify, request, session, g
from db import get_db

# Створюємо Blueprint версії 1
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Допоміжна функція: перетворення рядків БД у словник (JSON)
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@api_bp.route('/status', methods=['GET'])
def get_status():
    """
    Перевірка статусу API
    ---
    tags:
      - System
    responses:
      200:
        description: API працює
        schema:
          type: object
          properties:
            status:
              type: string
    """
    return jsonify({"status": "ok", "version": "1.0"})