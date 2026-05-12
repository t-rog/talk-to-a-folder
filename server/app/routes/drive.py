import os
from flask import Blueprint, request, jsonify

bp = Blueprint('drive', __name__, url_prefix='/api/drive')

@bp.route('/test')
def test():
    return {'status': 'ok'}