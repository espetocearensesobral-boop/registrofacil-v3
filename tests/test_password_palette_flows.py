from pathlib import Path

from werkzeug.security import check_password_hash

import models
from config import Config


PALETAS_DA_INTERFACE = [f'paleta-{numero:02d}' for numero in range(1, 21)]


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


def test_all_institutional_palette_ids_are_accepted(app_client):
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


def test_profile_exposes_twenty_institutional_themes_without_sidebar_palette(app_client):
    _login(app_client)
    response = app_client.get('/perfil/')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'Tema 01' in body
    assert 'Tema 02' in body
    for numero in range(1, 21):
        assert f'Tema {numero:02d}' in body
    assert '30 paletas profissionais' not in body
    assert '30 temas disponíveis' in body
    assert 'sidebar-color-grid' not in body
    assert 'Cor de seleção da sidebar' not in body


def test_sidebar_palette_endpoint_is_removed(app_client):
    csrf = _login(app_client)
    response = app_client.post(
        '/perfil/salvar-sidebar-cor',
        json={'sidebar_selection_color': '#7A1F2B'},
        headers={'X-CSRFToken': csrf},
    )
    assert response.status_code == 404



def test_profile_uses_compact_two_column_layout_without_profile_photo_controls(app_client):
    _login(app_client)
    response = app_client.get('/perfil/')
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert 'profile-page-layout' in body
    assert 'profile-main-column' in body
    assert 'profile-side-column' in body
    assert 'profile-theme-current' in body
    assert 'profile-password-grid' in body
    assert 'Dicas de segurança' not in body
    assert 'profile-security-card' not in body
    assert 'perfil-paleta-atual-nome' in body
    assert 'profile-photo' not in body
    palette_js = (Path(__file__).resolve().parents[1] / 'static/js/paleta.js').read_text(encoding='utf-8')
    assert "document.querySelectorAll('#paleta-atual-nome, #perfil-paleta-atual-nome')" in palette_js
    template = (Path(__file__).resolve().parents[1] / 'templates/perfil.html').read_text(encoding='utf-8')
    css = (Path(__file__).resolve().parents[1] / 'static/css/layout-standard.css').read_text(encoding='utf-8')
    assert template.count('profile-password-toggle') == 3
    assert 'aria-label="Mostrar ou ocultar senha atual"' in template
    assert 'padding-right: 2.65rem !important' in css
    assert 'profile-side-card' in css
    assert 'profile-theme-current' in css
    assert 'border: 1px solid var(--rf-border)' in css
    assert 'profile-page-layout' in css
    assert 'align-items: stretch;' in css
    assert 'profile-main-column' in css
    assert 'profile-side-column' in css
    assert 'height: 100%;' in css
    assert 'grid-template-rows: auto minmax(0, 1fr);' in css
