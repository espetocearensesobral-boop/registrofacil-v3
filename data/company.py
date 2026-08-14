"""Serviços de informações da empresa."""

from data.database import executar_query
from utils.helpers import validar_email, validar_telefone

def get_empresa_info():
    return executar_query("""
        SELECT id, cartorio, oficial, substituta, endereco,
               telefone, email, logo,
               criado_em, atualizado_em
        FROM empresa LIMIT 1""", fetch_one=True)

def save_empresa_info(data, is_new_record=False, connection=None):
    if data.get('email') and not validar_email(data['email']):
        raise ValueError("E-mail da empresa inválido.")

    if data.get('telefone') and not validar_telefone(data['telefone']):
        raise ValueError("Telefone da empresa inválido.")

    field_mapping = {
        'cartorio': 'cartorio',
        'oficial': 'oficial',
        'substituta': 'substituta',
        'endereco': 'endereco',
        'telefone': 'telefone',
        'email': 'email',
        'logo': 'logo'
    }
    
    filtered_data = {}
    for k, v in data.items():
        if k in field_mapping:
            filtered_data[field_mapping[k]] = v

    if is_new_record:
        if 'logo' in filtered_data and not filtered_data['logo']:
            del filtered_data['logo']
        
        columns = ', '.join(filtered_data.keys())
        placeholders = ', '.join(['?'] * len(filtered_data))
        query = f"INSERT INTO empresa ({columns}, criado_em, atualizado_em) VALUES ({placeholders}, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))"
        return executar_query(query, list(filtered_data.values()), connection=connection)
    else:
        update_fields = []
        update_params = []
        for k_lower, v in filtered_data.items():
            if k_lower == 'logo':
                if v is None or v == '':
                    update_fields.append(f"{k_lower} = NULL")
                else:
                    update_fields.append(f"{k_lower} = ?")
                    update_params.append(v)
            else:
                update_fields.append(f"{k_lower} = ?")
                update_params.append(v)
        
        query = f"UPDATE empresa SET {', '.join(update_fields)}, atualizado_em = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = ?"
        update_params.append(data['id'])
        
        return executar_query(query, update_params, connection=connection)

