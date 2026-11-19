from datetime import date

from despacho.core import (
    cubagem_m3,
    filtrar,
    ler_pedido,
    link_whatsapp,
    mensagem_cotacao,
    moeda,
    situacao_entrega,
    transportadoras_para,
)

LINHA = {
    "num_pedido": "123", "cliente": "Loja Teste", "cnpj_cpf": "00123456000101", "cep": "88010000",
    "cidade": "Florianópolis", "uf": "sc", "valor_total": "1.234,56", "peso_bruto": "10,5",
    "peso_liquido": "10", "qtd_volumes": 2, "embalagem": "CX M", "tipo_frete": "TRANSPORTADORA",
    "liberado_faturar": "S",
}
CAIXAS = [{"nome": "Caixa M", "apelidos": ["CX M"], "comprimento_cm": 40, "largura_cm": 30, "altura_cm": 30}]


def test_le_e_formata_o_pedido_do_erp():
    p = ler_pedido(LINHA)
    assert p.documento == "00.123.456/0001-01"
    assert p.cep == "88010-000"
    assert p.uf == "SC"
    assert p.valor == 1234.56 and p.peso_kg == 10.5
    assert p.liberado and not p.retira and p.avisos == []


def test_sem_peso_bruto_usa_liquido_e_avisa():
    p = ler_pedido({**LINHA, "peso_bruto": ""})
    assert p.peso_kg == 10
    assert any("peso líquido" in a for a in p.avisos)


def test_cliente_retira_fica_fora_da_fila_por_padrao():
    pedidos = [ler_pedido(LINHA), ler_pedido({**LINHA, "num_pedido": "124", "tipo_frete": "CLIENTE RETIRA"})]
    assert [p.numero for p in filtrar(pedidos)] == ["123"]
    assert len(filtrar(pedidos, mostrar_retira=True)) == 2


def test_busca_ignora_acentos():
    pedidos = [ler_pedido(LINHA)]
    assert filtrar(pedidos, busca="florianopolis")


def test_cubagem_pela_embalagem():
    p = ler_pedido(LINHA)
    assert cubagem_m3(p, CAIXAS) == 0.072  # 0,036 m³ por caixa x 2 volumes
    assert cubagem_m3(ler_pedido({**LINHA, "embalagem": "saco"}), CAIXAS) is None


def test_escolhe_transportadoras_por_estado_ou_cidade():
    transportadoras = [
        {"nome": "A", "estados": ["SC"], "cidades": []},
        {"nome": "B", "estados": ["PR"], "cidades": ["Florianópolis"]},
        {"nome": "C", "estados": ["SC"], "cidades": [], "ativa": False},
        {"nome": "D", "estados": ["SP"], "cidades": []},
    ]
    nomes = [t["nome"] for t in transportadoras_para(ler_pedido(LINHA), transportadoras)]
    assert nomes == ["A", "B"]


def test_mensagem_e_link_do_whatsapp():
    p = ler_pedido(LINHA)
    texto = mensagem_cotacao(p, "Pedido {numero} para {cidade}, {valor}, {cubagem} m3", "89000-000", 0.072)
    assert texto == "Pedido 123 para Florianópolis/SC, R$ 1.234,56, 0,072 m3"
    assert link_whatsapp("+55 (00) 0000-0001", "oi tudo") == "https://wa.me/550000000001?text=oi%20tudo"


def test_situacao_da_entrega():
    hoje = date(2026, 11, 19)
    assert situacao_entrega(date(2026, 11, 16), None, hoje) == ("atrasado", "3 dia(s) de atraso")
    assert situacao_entrega(date(2026, 11, 19), None, hoje)[0] == "vence_breve"
    assert situacao_entrega(date(2026, 11, 25), None, hoje) == ("no_prazo", "Faltam 6 dias")
    assert situacao_entrega(date(2026, 11, 10), date(2026, 11, 12), hoje)[0] == "entregue_atraso"
    assert situacao_entrega(date(2026, 11, 10), date(2026, 11, 9), hoje)[0] == "entregue_prazo"
    assert situacao_entrega(None, None, hoje)[0] == "sem_rastreio"


def test_moeda():
    assert moeda(1234567.8) == "R$ 1.234.567,80"
