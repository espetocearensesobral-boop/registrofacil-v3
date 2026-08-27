from pathlib import Path

import models
from config import Config


ROOT = Path(__file__).resolve().parents[1]


def _login(client):
    models.executar_query("UPDATE usuarios SET must_change_password = 0 WHERE usuario = ?", ['admin'])
    client.get('/login')
    with client.session_transaction() as session:
        csrf = session['csrf_token']
    response = client.post('/login', data={
        'usuario': 'admin',
        'senha': Config.INITIAL_ADMIN_PASSWORD or 'admin123',
        'csrf_token': csrf,
    })
    assert response.status_code == 302


def test_dashboard_prioritizes_quick_status_and_deadline_actions(app_client):
    _login(app_client)
    response = app_client.get('/dashboard')
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    for marker in (
        'dashboard-page-greeting',
        'class="kpi-grid"',
        'dashboard-focus-panel',
        'dashboard-focus-action is-overdue',
        'dashboard-focus-action is-upcoming',
        "prazo_alerta=vencidos",
        "prazo_alerta=proximos",
    ):
        assert marker in body

    assert 'dashboard-focus-count' not in body


def test_dashboard_does_not_duplicate_metrics_analysis(app_client):
    _login(app_client)
    response = app_client.get('/dashboard')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    template = (ROOT / 'templates/dashboard.html').read_text(encoding='utf-8')

    for marker in (
        'Leitura gerencial',
        'Acompanhe o ritmo da operação',
        'dashboard-analytics-section',
        'dashboardMovementChart',
        'dashboardStatusChart',
        'dashboardServicesChart',
        'dashboard_info.analytics',
        'chart.umd.min.js',
    ):
        assert marker not in body
        assert marker not in template
