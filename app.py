"""Despacho Rápido: fila de expedição com cotação de frete e acompanhamento de entregas.

Rodar:  python app.py   e abrir http://localhost:5000
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from despacho.core import (
    SITUACOES,
    cubagem_m3,
    filtrar,
    ler_pedido,
    link_whatsapp,
    mensagem_cotacao,
    moeda,
    rota_propria,
    situacao_entrega,
    transportadoras_para,
)

PASTA = Path(__file__).parent / "data"


def criar_app(pasta_dados: Path = PASTA) -> Flask:
    app = Flask(__name__)
    app.jinja_env.filters["moeda"] = moeda

    def ler(nome: str):
        return json.loads((pasta_dados / nome).read_text(encoding="utf-8"))

    def buscar_pedidos():
        """Na empresa isso seria uma chamada à API do ERP; aqui lemos um arquivo de exemplo."""
        return [ler_pedido(linha) for linha in ler("pedidos_exemplo.json")]

    def hoje() -> date:
        # Os dados de exemplo são de nov/2026; a data de referência fixa mantém a demonstração coerente.
        # Apague "data_referencia" do config.json para usar a data de hoje.
        data_demo = os.environ.get("DATA_REFERENCIA") or ler("config.json").get("data_referencia")
        return date.fromisoformat(data_demo) if data_demo else date.today()

    @app.get("/")
    def fila():
        config = ler("config.json")
        todos = buscar_pedidos()
        filtros = {
            "busca": request.args.get("busca", ""),
            "uf": request.args.get("uf", ""),
            "mostrar_retira": request.args.get("retira") == "1",
            "so_liberados": request.args.get("liberados") == "1",
        }
        pedidos = filtrar(todos, **filtros)

        cards = []
        for p in pedidos:
            m3 = cubagem_m3(p, config["caixas"])
            mensagem = mensagem_cotacao(p, config["modelo_mensagem"], config["remetente_cep"], m3)
            transportadoras = []
            for t in transportadoras_para(p, config["transportadoras"]):
                link = link_whatsapp(t["telefone"], mensagem) if t["canal"] == "whatsapp" else None
                transportadoras.append({**t, "link": link})
            avisos = list(p.avisos)
            if m3 is None:
                avisos.append("Embalagem não cadastrada: informe a cubagem antes de cotar.")
            cards.append({
                "pedido": p,
                "m3": m3,
                "mensagem": mensagem,
                "transportadoras": transportadoras,
                "rota_propria": rota_propria(p, config["cidades_rota_propria"]),
                "avisos": avisos,
            })

        return render_template(
            "fila.html",
            cards=cards,
            filtros=filtros,
            ufs=sorted({p.uf for p in todos if p.uf}),
            total=len(todos),
            atualizar=config["atualizar_segundos"],
            empresa=config["empresa"],
        )

    @app.get("/rastreio")
    def rastreio():
        notas = []
        for n in ler("rastreios_exemplo.json"):
            previsao = date.fromisoformat(n["previsao"]) if n["previsao"] else None
            entregue = date.fromisoformat(n["entregue_em"]) if n["entregue_em"] else None
            codigo, texto = situacao_entrega(previsao, entregue, hoje())
            notas.append({**n, "situacao": codigo, "rotulo": SITUACOES[codigo][0], "texto": texto})
        notas.sort(key=lambda n: SITUACOES[n["situacao"]][1])
        resumo = {c: sum(1 for n in notas if n["situacao"] == c) for c in SITUACOES}
        return render_template("rastreio.html", notas=notas, resumo=resumo, situacoes=SITUACOES, hoje=hoje())

    @app.get("/api/pedidos")
    def api_pedidos():
        return jsonify([p.__dict__ for p in buscar_pedidos()])

    return app


app = criar_app()

if __name__ == "__main__":
    app.run(debug=True)
