import pytest

from app import criar_app


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setenv("DATA_REFERENCIA", "2026-11-19")
    app = criar_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_fila_mostra_pedidos_e_esconde_retira(cliente):
    html = cliente.get("/").get_data(as_text=True)
    assert "Pedido 50101" in html
    assert "Pedido 50107" not in html  # cliente retira
    assert "wa.me/" in html


def test_cidade_da_rota_propria_nao_pede_cotacao(cliente):
    html = cliente.get("/?busca=joinville").get_data(as_text=True)
    assert "rota própria" in html


def test_filtro_por_estado(cliente):
    html = cliente.get("/?uf=SP").get_data(as_text=True)
    assert "Pedido 50104" in html and "Pedido 50101" not in html


def test_rastreio_ordena_atrasados_primeiro(cliente):
    html = cliente.get("/rastreio").get_data(as_text=True)
    assert html.index("9001") < html.index("9004")  # atrasado antes de entregue


def test_api_de_pedidos(cliente):
    dados = cliente.get("/api/pedidos").get_json()
    assert len(dados) == 8
