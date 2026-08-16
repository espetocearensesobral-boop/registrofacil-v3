# registrofacil/utils/file_uploads.py

import os
import secrets
import hashlib
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import url_for

from config import Config
from utils.logger import logger

# Diretório único de imagem utilizado pela aplicação: logo do estabelecimento.
EMPRESA_UPLOAD_FOLDER = Config.EMPRESA_UPLOAD_FOLDER

# Garante que o diretório de logo exista.
os.makedirs(EMPRESA_UPLOAD_FOLDER, exist_ok=True)

# --- Validação de MIME real para imagens (mesmo princípio de routes/processos.py) ---
# Evita que um arquivo malicioso disfarçado com extensão de imagem (ex: .php
# renomeado para .png) seja aceito apenas por checagem de extensão.
IMAGE_MIME_ALIASES = {
    'jpg':  {'image/jpeg'},
    'jpeg': {'image/jpeg'},
    'png':  {'image/png'},
}


def _get_mime_type_from_file(filepath):
    """
    Determina o tipo MIME real de um arquivo usando python-magic.
    Por segurança, se a biblioteca não estiver disponível, o upload é bloqueado
    em vez de cair num fallback inseguro baseado só na extensão.
    """
    try:
        import magic
        mime = magic.Magic(mime=True)
        return mime.from_file(filepath)
    except ImportError:
        logger.critical(
            "ERRO CRÍTICO DE SEGURANÇA: Biblioteca 'python-magic' não encontrada. "
            "Upload de imagem bloqueado por segurança."
        )
        raise ValueError("Sistema de validação de arquivos indisponível. Contate o suporte.")
    except Exception as e:
        logger.error(f"Erro na detecção de MIME type com python-magic: {e}", exc_info=True)
        raise ValueError("Não foi possível validar o arquivo enviado.")


def _mime_valido_para_extensao_imagem(extensao, mime_type):
    """Verifica se o MIME type real detectado é compatível com a extensão informada."""
    mime_normalizado = mime_type.split(';')[0].strip().lower()
    mimes_aceitos = IMAGE_MIME_ALIASES.get(extensao, set())
    return mime_normalizado in mimes_aceitos


def _sanitizar_svg(filepath):
    """
    Remove conteúdo potencialmente perigoso de um arquivo SVG antes de aceitá-lo.

    SVG é um formato XML e pode conter <script>, manipuladores de evento
    (onload, onclick, ...), tags <foreignObject>/<iframe>/<embed>/<object> ou
    URIs 'javascript:' — qualquer um deles pode executar código no navegador
    de quem visualiza o arquivo (XSS armazenado). Esta função reescreve o
    arquivo removendo esses elementos/atributos, ou levanta ValueError se o
    conteúdo não puder ser processado com segurança.

    Observação: nenhum fluxo atual do sistema permite upload de .svg
    (removido de ALLOWED_LOGO_EXTENSIONS em routes/empresa.py). Esta função é
    mantida como camada extra de defesa, caso SVG volte a ser habilitado no
    futuro em algum ponto do sistema.
    """
    import re
    import xml.etree.ElementTree as ET

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, OSError):
        raise ValueError('Arquivo SVG inválido ou com codificação não suportada.')

    # Bloqueia DOCTYPE/ENTITY: previne XXE e ataques de expansão de entidades
    # ("billion laughs"). Um SVG legítimo de logo não precisa disso.
    if re.search(r'<!DOCTYPE', content, re.IGNORECASE) or re.search(r'<!ENTITY', content, re.IGNORECASE):
        raise ValueError('Arquivo SVG contendo DOCTYPE/ENTITY não é permitido por segurança.')

    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        raise ValueError('Arquivo SVG malformado.')

    tags_perigosas = {'script', 'foreignobject', 'iframe', 'embed', 'object'}
    prefixo_atributo_evento = 'on'  # onload, onclick, onmouseover, etc.
    padrao_uri_perigosa = re.compile(r'^\s*javascript:', re.IGNORECASE)

    def nome_local(tag):
        return tag.split('}', 1)[1].lower() if '}' in tag else tag.lower()

    def limpar(elemento):
        for filho in list(elemento):
            if nome_local(filho.tag) in tags_perigosas:
                elemento.remove(filho)
                continue
            limpar(filho)

        for atributo in list(elemento.attrib.keys()):
            attr_local = atributo.split('}', 1)[1].lower() if '}' in atributo else atributo.lower()
            valor = elemento.attrib[atributo]
            if attr_local.startswith(prefixo_atributo_evento):
                del elemento.attrib[atributo]
            elif attr_local in ('href',) and padrao_uri_perigosa.match(valor or ''):
                del elemento.attrib[atributo]

    limpar(root)

    conteudo_sanitizado = ET.tostring(root, encoding='unicode')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(conteudo_sanitizado)



def handle_image_upload(uploaded_file, current_filename, target_folder, allowed_extensions, max_size_mb, prefix=""):
    """
    Processa o upload de uma imagem, salva no servidor e retorna o novo nome do arquivo.
    (Esta função permanece inalterada)
    """
    if uploaded_file and uploaded_file.filename != '':
        max_size_bytes = max_size_mb * 1024 * 1024
        original_filename = uploaded_file.filename
        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''

        if file_ext not in allowed_extensions:
            raise ValueError(f'Formato de imagem inválido. Apenas {", ".join(allowed_extensions).upper()} são permitidos.')

        uploaded_file.seek(0, os.SEEK_END)
        file_size = uploaded_file.tell()
        uploaded_file.seek(0) 

        if file_size > max_size_bytes:
            raise ValueError(f'A imagem deve ter no máximo {max_size_mb}MB.')

        timestamp = int(datetime.now().timestamp())
        random_hex = secrets.token_hex(4)
        filename_base = f'{prefix}_{timestamp}_{random_hex}' if prefix else f'{timestamp}_{random_hex}'

        filename = secure_filename(f'{filename_base}.{file_ext}')
        destination = os.path.join(target_folder, filename)

        # Salva primeiro em arquivo temporário para inspecionar o conteúdo real
        # antes de expor o arquivo com o nome final (mesmo padrão de routes/processos.py).
        temp_destination = os.path.join(target_folder, secure_filename(f'{filename_base}.{file_ext}.tmp'))
        uploaded_file.save(temp_destination)

        try:
            mime_type = _get_mime_type_from_file(temp_destination)
            if not _mime_valido_para_extensao_imagem(file_ext, mime_type):
                logger.warning(
                    f"Upload de imagem rejeitado: extensão '.{file_ext}' não corresponde "
                    f"ao conteúdo real detectado ({mime_type})."
                )
                raise ValueError(
                    'O conteúdo do arquivo não corresponde a uma imagem válida para a extensão informada.'
                )

            # SVG é XML e pode carregar <script>/on*/javascript:. Sanitiza antes de aceitar,
            # mesmo que hoje nenhum chamador permita essa extensão (defesa em profundidade).
            if file_ext == 'svg':
                _sanitizar_svg(temp_destination)

            # Só remove a imagem antiga depois que a nova passou na validação de conteúdo.
            if current_filename and not (current_filename.startswith('http') or current_filename == Config.DEFAULT_LOGO_URL):
                old_file_path = os.path.join(target_folder, secure_filename(current_filename))
                if os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                    except Exception as e:
                        logger.error(f"Falha ao remover arquivo antigo '{old_file_path}': {e}", exc_info=True)

            os.replace(temp_destination, destination)
            return filename
        except Exception:
            if os.path.exists(temp_destination):
                try:
                    os.remove(temp_destination)
                except Exception as rm_e:
                    logger.error(f"Falha ao remover arquivo temporário '{temp_destination}': {rm_e}")
            raise
    return None

def remove_image_file(filename, target_folder):
    """
    Remove um arquivo de imagem físico do servidor.
    (Esta função permanece inalterada)
    """
    if filename and not (filename.startswith('http') or filename == Config.DEFAULT_LOGO_URL):
        file_path = os.path.join(target_folder, secure_filename(filename))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except Exception as e:
                logger.error(f"Falha ao remover arquivo '{file_path}': {e}", exc_info=True)
    return False

def get_image_url_for_display(filename, is_company_logo=True, for_pdf=False):
    """
    Retorna a URL apropriada para uma imagem.
    - Se for_pdf=True, retorna um caminho de arquivo local absoluto para o WeasyPrint.
    - Se for_pdf=False, retorna uma URL web para o navegador.
    """
    # Preserva URLs externas configuradas para a logo, quando existirem.
    if filename and (filename.startswith('http://') or filename.startswith('https://')):
        return filename

    # A aplicação usa somente a logo do estabelecimento.
    target_folder = EMPRESA_UPLOAD_FOLDER
    default_image_path = 'img/registrofacil.png'
    
    # Constrói o caminho completo para o arquivo de imagem, se um nome foi fornecido
    local_file_path_full = os.path.join(target_folder, secure_filename(filename)) if filename else ''

    # 2. Lógica para gerar o caminho para o PDF
    if for_pdf:
        # Se um arquivo local existir, retorna seu caminho absoluto no formato 'file:///'
        if filename and os.path.exists(local_file_path_full):
            return f'file:///{os.path.abspath(local_file_path_full)}'

        # Se não houver arquivo, retorna o caminho absoluto do padrão em static/
        # Usa current_app.static_folder para ser correto em modo .py e .exe (PyInstaller)
        from flask import current_app
        static_dir = current_app.static_folder
        default_path = os.path.join(static_dir, default_image_path)
        if os.path.exists(default_path):
            return f'file:///{os.path.abspath(default_path)}'

        return ''  # Retorna vazio se nem o padrão for encontrado

    # 3. Lógica para exibição na web — usa a rota /uploads/ que funciona
    #    tanto no modo .py (static/uploads/) quanto no modo .exe (ProgramData/uploads/)
    else:
        # Se um arquivo local existir, gera a URL para ele
        if filename and os.path.exists(local_file_path_full):
            version_param = int(os.path.getmtime(local_file_path_full))
            return url_for('serve_upload', filepath=f'empresa/{secure_filename(filename)}') + f'?v={version_param}'

        return url_for('static', filename=default_image_path)
