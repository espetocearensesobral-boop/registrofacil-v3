from werkzeug.security import check_password_hash

import models
from config import Config


PALETAS_DA_INTERFACE = [
    'dourado', 'azul-marinho', 'vinho', 'verde-esmeralda', 'azul-petroleo',
    'roxo-real', 'azul-royal', 'verde-oliva', 'terracota', 'azul-cobalto',
    'magenta', 'cinza-grafite', 'teal', 'indigo', 'ambar', 'verde-floresta',
    'azul-aco', 'coral', 'lavanda', 'preto-classico', 'vermelho-rubi',
    'rosa-antigo', 'laranja-queimado', 'verde-jade', 'azul-meia-noite',
    'violeta-ametista', 'marrom-cafe', 'cinza-carvao', 'verde-salvia',
    'azul-oceano',
]


def _admin_password():
    return Config.INITIAL_ADMIN_PASSWORD or 'admin123'


def _login(client):
    client.get('/login')
    with client.session_transaction() as session:
        csrf = session['csrf_token']
    response = client.post('/login', data={
        'usuario': 'admin',
        'senha': _admin_password(),
        'csrf_token': csrf,
    })
    assert response.status_code == 302
    with client.session_transaction() as session:
        return session['csrf_token']


def test_admin_can_change_own_password_with_contextual_response(app_client):
    csrf = _login(app_client)
    admin = models.executar_query(
        'SELECT nome, email FROM usuarios WHERE usuario = ?', ['admin'], fetch_one=True
    )
    new_password = 'SenhaNovaSegura123!'

    response = app_client.post('/perfil/', data={
        'csrf_token': csrf,
        'nome': admin['nome'],
        'email': admin['email'],
        'senha_atual': _admin_password(),
        'nova_senha': new_password,
        'confirmar_senha': new_password,
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['type'] == 'success'
    assert payload['title'] == 'Sucesso'
    stored = models.executar_query(
        'SELECT senha FROM usuarios WHERE usuario = ?', ['admin'], fetch_one=True
    )
    assert check_password_hash(stored['senha'], new_password)


def test_all_palette_ids_exposed_by_ui_are_accepted(app_client):
    csrf = _login(app_client)

    for palette_id in PALETAS_DA_INTERFACE:
        response = app_client.post(
            '/perfil/salvar-tema',
            json={'tema': palette_id},
            headers={'X-CSRFToken': csrf},
        )
        assert response.status_code == 200, (palette_id, response.get_json())
        payload = response.get_json()
        assert payload['success'] is True
        assert payload['type'] == 'success'
        assert payload['message']

    current = app_client.get('/perfil/tema')
    assert current.status_code == 200
    assert current.get_json()['tema_cor'] == PALETAS_DA_INTERFACE[-1]
