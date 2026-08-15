import models
from config import Config


def _default_admin_password():
    return Config.INITIAL_ADMIN_PASSWORD or "admin123"


def _csrf_token(client):
    client.get("/login")
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_dashboard_requires_login(app_client):
    response = app_client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_rejects_invalid_csrf(app_client):
    response = app_client.post(
        "/login",
        data={"usuario": "admin", "senha": _default_admin_password(), "csrf_token": "invalid"},
    )
    assert response.status_code == 200
    with app_client.session_transaction() as session:
        assert session.get("logado") is not True


def test_login_requires_password_change_on_default_account(app_client):
    models.executar_query(
        "UPDATE usuarios SET must_change_password = 1 WHERE usuario = ?",
        ["admin"],
    )
    response = app_client.post(
        "/login",
        data={
            "usuario": "admin",
            "senha": _default_admin_password(),
            "csrf_token": _csrf_token(app_client),
        },
    )
    assert response.status_code == 302
    with app_client.session_transaction() as session:
        assert session.get("logado") is True
        assert session.get("force_password_change") is True

    protected = app_client.get("/dashboard")
    assert protected.status_code == 302
    assert "/perfil" in protected.headers["Location"]


def test_admin_form_csrf_remains_valid_after_opening_another_page(app_client):
    models.executar_query("UPDATE usuarios SET must_change_password = 0 WHERE usuario = ?", ["admin"])
    client = app_client
    client.get('/login')
    with client.session_transaction() as session:
        login_csrf = session['csrf_token']
    login = client.post('/login', data={
        'usuario': 'admin',
        'senha': _default_admin_password(),
        'csrf_token': login_csrf,
    })
    assert login.status_code == 302

    edit_page = client.get('/admin/editar_usuario/1')
    assert edit_page.status_code == 200
    with client.session_transaction() as session:
        form_csrf = session['csrf_token']

    # Outra renderização não pode invalidar o formulário já aberto.
    client.get('/perfil/')
    admin = models.executar_query(
        'SELECT nome, email, role, ativo FROM usuarios WHERE id = 1',
        fetch_one=True,
    )
    response = client.post('/admin/editar_usuario/1', data={
        'csrf_token': form_csrf,
        'nome': admin['nome'],
        'email': admin['email'],
        'role': admin['role'],
        'ativo': 'on' if admin['ativo'] else '',
        'nova_senha': '',
        'confirmar_senha': '',
    }, headers={'X-Requested-With': 'XMLHttpRequest'})

    assert response.status_code != 403
    assert response.get_json()['message'] != 'Sessão expirada ou token de segurança inválido. Por favor, recarregue a página e tente novamente.'
