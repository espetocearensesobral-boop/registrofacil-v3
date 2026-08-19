# registrofacil/routes/utils_routes.py
import os
import platform
from flask import Blueprint, jsonify, request, session
from routes.auth import login_status_required, admin_required, verificar_csrf_token

utils_bp = Blueprint('utils', __name__, url_prefix='/utils')

@utils_bp.route('/list_dirs', methods=['POST'])
@login_status_required
@admin_required
def list_dirs():
    """Lista diretórios para o seletor de pastas."""
    data = request.get_json(silent=True) or {}
    csrf_token = (
        request.headers.get('X-CSRFToken')
        or request.headers.get('X-CSRF-Token')
        or data.get('csrf_token')
    )
    if not verificar_csrf_token(csrf_token):
        return jsonify(success=False, message="Token de segurança inválido.", type='danger'), 403
    current_path = data.get('path', '')

    # Se o caminho estiver vazio, tenta obter a raiz do sistema ou o diretório do usuário
    if not current_path:
        if platform.system() == 'Windows':
            # No Windows, lista as unidades se o caminho estiver vazio
            import string
            drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
            return jsonify(success=True, current_path="", dirs=drives, is_root=True)
        else:
            current_path = "/"

    try:
        current_path = os.path.abspath(current_path)
        if not os.path.exists(current_path):
            return jsonify(success=False, message="Caminho não encontrado."), 404

        dirs = []
        # Adicionar opção para subir um nível
        parent_path = os.path.dirname(current_path)
        
        # Listar apenas diretórios
        for item in os.listdir(current_path):
            full_path = os.path.join(current_path, item)
            try:
                if os.path.isdir(full_path):
                    dirs.append(item)
            except (PermissionError, OSError):
                continue

        dirs.sort(key=str.lower)
        
        return jsonify(
            success=True, 
            current_path=current_path, 
            parent_path=parent_path,
            dirs=dirs,
            is_root=(current_path == parent_path)
        )
    except Exception as e:
        return jsonify(success=False, message=str(e)), 500
