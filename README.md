# 🚚 Despacho Rápido

Painel web para a **expedição de uma distribuidora**: mostra os pedidos na fila de faturamento, monta na hora a mensagem de **cotação de frete** para cada transportadora e acompanha os **prazos de entrega** das notas já despachadas.

> Projeto de portfólio inspirado num sistema real que desenvolvi para a empresa onde trabalho. O código foi escrito do zero, e todos os nomes, transportadoras e dados são fictícios.

## O problema

Todo dia a expedição precisava abrir cada pedido no ERP, copiar CEP, peso, volumes e valor da nota, calcular a cubagem e mandar a mesma mensagem para várias transportadoras. Era um trabalho manual, lento e cheio de erro de digitação. Depois de despachado, ninguém sabia com facilidade quais entregas estavam atrasadas.

## O que o sistema faz

**Fila de faturamento**
- Lê os pedidos do ERP (aqui, de um JSON de exemplo) e organiza CNPJ, CEP, peso, volumes e valor.
- Esconde por padrão os pedidos "cliente retira" e filtra por estado, liberação e busca, ignorando acentos.
- Calcula a **cubagem** a partir da embalagem cadastrada (Caixa P, M, G, Fardo...).
- Sugere as **transportadoras que atendem** a cidade ou o estado do destino.
- Gera a **mensagem de cotação pronta**, com botão de copiar e link direto para o WhatsApp de cada transportadora.
- Avisa quando falta peso bruto, CEP ou embalagem, porque esses casos fazem o frete sair errado.
- Identifica cidades da **rota própria**, que não precisam de cotação.
- Atualiza sozinho a cada 2 minutos, com contagem regressiva na tela.

**Rastreio**
- Classifica cada nota em: atrasada, vence em breve, no prazo, entregue no prazo, entregue com atraso ou sem rastreio.
- Mostra um resumo por situação e lista as atrasadas primeiro.

## Tecnologias

Python 3 · Flask · Jinja2 · JavaScript · CSS · pytest

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate      # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abra http://localhost:5000.

As transportadoras, as caixas, as cidades da rota própria e o modelo da mensagem ficam em `data/config.json`. Como os dados de exemplo são de novembro de 2026, o rastreio usa a data fixa `data_referencia` do config. Apague essa linha para usar a data de hoje.

## Testes

```bash
pytest
```

## Estrutura

```
app.py                 rotas da aplicação Flask
despacho/core.py       regras: leitura do pedido, cubagem, transportadoras, mensagem e prazos
templates/             páginas HTML
static/                estilo, atualização automática e botão de copiar
data/                  configuração e dados de exemplo (fictícios)
tests/                 testes automatizados
```

## Próximos passos

- Conectar à API real do ERP, com a chave lida de variável de ambiente.
- Consultar o rastreio direto na API das transportadoras.
- Salvar o histórico de cotações em banco de dados.

## Autor

Feito por **Gui Rocha**: [LinkedIn](https://www.linkedin.com/in/guilherme-rochaaa) · [GitHub](https://github.com/GuiRocha07)
