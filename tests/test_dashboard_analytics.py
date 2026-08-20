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


def test_dashboard_analytics_returns_real_aggregates_with_seven_days(app_client):
    _login(app_client)
    analytics = models.get_dashboard_analytics()

    assert len(analytics['movimentacao_diaria']) == 7
    assert all({'dia', 'label', 'total'} <= set(item) for item in analytics['movimentacao_diaria'])
    assert analytics['movimentacao_7_dias'] >= 0
    assert analytics['total_processos'] >= analytics['total_concluidos']
    assert analytics['total_processos'] >= analytics['total_abertos']
    assert 0 <= analytics['taxa_conclusao'] <= 100
    assert 0 <= analytics['taxa_no_prazo'] <= 100
    assert analytics['pico_movimentacao']['total'] >= 0
    assert all(item['total'] >= 0 for item in analytics['status_distribuicao'])
    assert len(analytics['servicos_principais']) <= 5


def test_dashboard_exposes_analytics_cards_and_chart_canvases(app_client):
    _login(app_client)
    response = app_client.get('/dashboard')
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert 'dashboard-insights-grid' not in body
    assert body.find('class="kpi-grid"') < body.find('Processos Recentes') < body.find('Movimentação diária')
    assert body.find('Processos Recentes') < body.find('Prazos Críticos')
    for marker in (
        'dashboardMovementChart',
        'dashboardStatusChart',
        'dashboardServicesChart',
        'Movimentação diária',
        'Distribuição por status',
        'Serviços mais movimentados',
        'Leitura operacional',
    ):
        assert marker in body

    dashboard_template = (ROOT / 'templates/dashboard.html').read_text(encoding='utf-8')
    assert 'dashboard_info.analytics | tojson' in dashboard_template
    assert "type: 'bar'" in dashboard_template
    assert "type: 'doughnut'" in dashboard_template
