# registrofacil/utils/helpers.py

from datetime import datetime
import math
import re

def get_contrast_color(hex_color):
    """
    Determina se uma cor hexadecimal deve usar texto branco ou preto para contraste.
    Adaptação da equação YIQ.
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    # YIQ equation from http://en.wikipedia.org/wiki/YIQ_color_space#Limitations
    yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000
    return '#ffffff' if yiq < 150 else '#000000'

def formatar_data(data_str):
    """
    Formata uma string de data/timestamp para o formato DD/MM/YYYY ou DD/MM/YYYY HH:MM:SS.
    """
    if not data_str:
        return '-'
    try:
        # Tenta parsear com milissegundos
        if '.' in str(data_str):
            dt_obj = datetime.strptime(str(data_str), '%Y-%m-%d %H:%M:%S.%f')
            return dt_obj.strftime('%d/%m/%Y %H:%M:%S')
        # Tenta parsear com segundos
        elif ' ' in str(data_str):
            dt_obj = datetime.strptime(str(data_str), '%Y-%m-%d %H:%M:%S')
            return dt_obj.strftime('%d/%m/%Y %H:%M:%S')
        # Tenta parsear apenas data
        else:
            dt_obj = datetime.strptime(str(data_str), '%Y-%m-%d')
            return dt_obj.strftime('%d/%m/%Y')
    except ValueError:
        # Se falhar, retorna a string original ou um fallback
        return data_str

def formatar_tamanho_arquivo(bytes_count, decimals = 2):
    """
    Formata um número de bytes para uma string legível (Bytes, KB, MB, GB).
    """
    if bytes_count is None: return '-'
    if bytes_count == 0: return '0 Bytes'
    k = 1024
    dm = decimals if decimals >= 0 else 0
    sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    i = math.floor(math.log(bytes_count) / math.log(k))
    return f"{bytes_count / (k ** i):.{dm}f} {sizes[i]}"

def obter_icone_anexo(mime_type):
    """
    Retorna a classe do ícone Bootstrap Icons com base no tipo MIME do anexo.
    """
    icon_map = {
        'application/pdf': 'bi-file-earmark-pdf-fill',
        'application/msword': 'bi-file-earmark-word-fill',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'bi-file-earmark-word-fill',
        'image/jpeg': 'bi-file-earmark-image-fill',
        'image/png': 'bi-file-earmark-image-fill',
        'image/gif': 'bi-file-earmark-image-fill',
        'text/plain': 'bi-file-earmark-text-fill',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'bi-file-earmark-excel-fill',
        'application/vnd.ms-excel': 'bi-file-earmark-excel-fill',
        'text/csv': 'bi-file-earmark-spreadsheet-fill'
    }
    return icon_map.get(mime_type, 'bi-file-earmark')

def validarCPF(cpf: str) -> bool:
    """Valida um número de CPF."""
    cpf = re.sub(r'[^0-9]', '', cpf)
    if len(cpf) != 11 or re.match(r'(\d)\1{10}', cpf):
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[j]) * ((i + 1) - j) for j in range(i))
        digito = 11 - (soma % 11)
        if digito > 9:
            digito = 0
        if int(cpf[i]) != digito:
            return False
    return True

def validarCNPJ(cnpj: str) -> bool:
    """Valida um número de CNPJ."""
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    if len(cnpj) != 14 or re.match(r'(\d)\1{13}', cnpj):
        return False
    
    def calculate_digit(numbers, factors):
        soma = sum(int(numbers[i]) * factors[i] for i in range(len(numbers)))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    factors1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    factors2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    digito1 = calculate_digit(cnpj[0:12], factors1)
    if int(cnpj[12]) != digito1:
        return False

    digito2 = calculate_digit(cnpj[0:13], factors2)
    if int(cnpj[13]) != digito2:
        return False
    
    return True

def validar_telefone(telefone):
    """Valida um número de telefone com formatos específicos."""
    if not telefone: return True
    padrao = r"^\(?[0-9]{2}\)?[ .-]?[0-9]{4,5}[ .-][0-9]{4}$"
    if not re.fullmatch(padrao, telefone):
        raise ValueError("Telefone inválido. Formato esperado: (XX) 9XXXX-XXXX ou (XX) XXXX-XXXX.")
    return True

def validar_email(email):
    """Valida um endereço de e-mail."""
    if not email: return True
    if not re.fullmatch(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError("E-mail inválido.")
    return True