"""Regras da expedição: leitura dos pedidos do ERP, cotação de frete e prazos de entrega."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import quote


def normalizar(texto: object) -> str:
    """Sem acento, maiúsculo e sem espaços nas pontas ("São Paulo " -> "SAO PAULO")."""
    texto = unicodedata.normalize("NFD", str(texto or "").strip())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").upper()


def so_digitos(texto: object) -> str:
    return re.sub(r"\D", "", str(texto or ""))


# ---------------------------------------------------------------- pedidos

@dataclass
class Pedido:
    numero: str
    cliente: str
    documento: str
    cep: str
    cidade: str
    uf: str
    valor: float
    peso_kg: float
    volumes: int
    embalagem: str
    retira: bool
    liberado: bool
    avisos: list[str] = field(default_factory=list)


def _numero(valor: object) -> float:
    """Converte "1.234,56", "1234.56" ou 1234.56 em float."""
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor or "").strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto) if texto else 0.0
    except ValueError:
        return 0.0


def formatar_documento(digitos: str) -> str:
    if len(digitos) == 14:
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"
    if len(digitos) == 11:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    return digitos


def formatar_cep(digitos: str) -> str:
    return f"{digitos[:5]}-{digitos[5:]}" if len(digitos) == 8 else digitos


def ler_pedido(linha: dict) -> Pedido:
    """Transforma uma linha crua do ERP num pedido organizado."""
    tipo_frete = normalizar(linha.get("tipo_frete"))
    peso_bruto = _numero(linha.get("peso_bruto"))
    peso_liquido = _numero(linha.get("peso_liquido"))

    pedido = Pedido(
        numero=str(linha.get("num_pedido", "")).strip(),
        cliente=str(linha.get("cliente", "")).strip() or "Cliente não informado",
        documento=formatar_documento(so_digitos(linha.get("cnpj_cpf"))),
        cep=formatar_cep(so_digitos(linha.get("cep"))),
        cidade=str(linha.get("cidade", "")).strip(),
        uf=normalizar(linha.get("uf")),
        valor=_numero(linha.get("valor_total")),
        peso_kg=peso_bruto or peso_liquido,
        volumes=int(_numero(linha.get("qtd_volumes"))),
        embalagem=str(linha.get("embalagem", "")).strip(),
        retira="RETIRA" in tipo_frete,
        liberado=normalizar(linha.get("liberado_faturar")) == "S",
    )
    if not peso_bruto and peso_liquido:
        pedido.avisos.append("Sem peso bruto: usando o peso líquido, o frete pode sair mais baixo.")
    if len(so_digitos(pedido.cep)) != 8:
        pedido.avisos.append("CEP de entrega ausente ou incompleto.")
    return pedido


def filtrar(pedidos: list[Pedido], busca: str = "", uf: str = "", mostrar_retira: bool = False,
            so_liberados: bool = False) -> list[Pedido]:
    termo = normalizar(busca)
    resultado = []
    for p in pedidos:
        if p.retira and not mostrar_retira:
            continue
        if so_liberados and not p.liberado:
            continue
        if uf and p.uf != uf:
            continue
        if termo and termo not in normalizar(f"{p.numero} {p.cliente} {p.cidade}"):
            continue
        resultado.append(p)
    return resultado


# ---------------------------------------------------------------- cotação

def cubagem_m3(pedido: Pedido, caixas: list[dict]) -> float | None:
    """Volume total em m³, achando a caixa pelo nome ou apelido na descrição da embalagem."""
    descricao = normalizar(pedido.embalagem)
    for caixa in caixas:
        nomes = [caixa["nome"], *caixa.get("apelidos", [])]
        if any(normalizar(n) in descricao for n in nomes):
            m3 = caixa["comprimento_cm"] * caixa["largura_cm"] * caixa["altura_cm"] / 1_000_000
            return round(m3 * max(pedido.volumes, 1), 3)
    return None


def transportadoras_para(pedido: Pedido, transportadoras: list[dict]) -> list[dict]:
    """Transportadoras ativas que atendem a cidade ou o estado do pedido."""
    cidade = normalizar(pedido.cidade)
    return [
        t for t in transportadoras
        if t.get("ativa", True)
        and (cidade in {normalizar(c) for c in t.get("cidades", [])} or pedido.uf in t.get("estados", []))
    ]


def rota_propria(pedido: Pedido, cidades: list[str]) -> bool:
    return normalizar(pedido.cidade) in {normalizar(c) for c in cidades}


def mensagem_cotacao(pedido: Pedido, modelo: str, remetente_cep: str, m3: float | None) -> str:
    """Preenche o modelo de mensagem com os dados do pedido."""
    return modelo.format(
        numero=pedido.numero,
        cep_origem=remetente_cep,
        cep_destino=pedido.cep or "—",
        cidade=f"{pedido.cidade}/{pedido.uf}",
        documento=pedido.documento or "—",
        valor=moeda(pedido.valor),
        peso=f"{pedido.peso_kg:.2f}".replace(".", ","),
        volumes=pedido.volumes,
        cubagem=f"{m3:.3f}".replace(".", ",") if m3 else "a confirmar",
    )


def link_whatsapp(telefone: str, mensagem: str) -> str:
    return f"https://wa.me/{so_digitos(telefone)}?text={quote(mensagem)}"


def moeda(valor: float) -> str:
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


# ---------------------------------------------------------------- rastreio

SITUACOES = {
    "atrasado": ("Atrasado", 0),
    "vence_breve": ("Vence em breve", 1),
    "no_prazo": ("No prazo", 2),
    "entregue_atraso": ("Entregue com atraso", 3),
    "entregue_prazo": ("Entregue no prazo", 4),
    "sem_rastreio": ("Sem rastreio", 5),
}


def situacao_entrega(previsao: date | None, entregue_em: date | None, hoje: date) -> tuple[str, str]:
    """Diz se a entrega está atrasada, vencendo, no prazo ou já entregue.

    Retorna (código, texto), por exemplo ("atrasado", "3 dias de atraso").
    """
    if previsao is None:
        return "sem_rastreio", "Transportadora ainda sem previsão"
    if entregue_em is not None:
        atraso = (entregue_em - previsao).days
        if atraso > 0:
            return "entregue_atraso", f"Entregue com {atraso} dia(s) de atraso"
        return "entregue_prazo", "Entregue no prazo"
    faltam = (previsao - hoje).days
    if faltam < 0:
        return "atrasado", f"{-faltam} dia(s) de atraso"
    if faltam <= 1:
        return "vence_breve", "Vence hoje" if faltam == 0 else "Vence amanhã"
    return "no_prazo", f"Faltam {faltam} dias"
