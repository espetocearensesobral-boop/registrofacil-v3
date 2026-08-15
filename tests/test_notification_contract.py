from utils.notification_contract import error, info, notification_payload, success, warning


def test_notification_payload_normalizes_unknown_type_and_empty_message():
    payload = notification_payload("", "unknown")

    assert payload == {
        "type": "info",
        "title": "Informação",
        "message": "Informação",
    }


def test_notification_helpers_return_contextual_contract():
    assert success("Registro salvo.") == {
        "type": "success",
        "title": "Sucesso",
        "message": "Registro salvo.",
    }
    assert error("Falha ao salvar.")["title"] == "Erro"
    assert warning("Confira o formulário.")["title"] == "Atenção"
    assert info("Sincronização concluída.")["title"] == "Informação"
