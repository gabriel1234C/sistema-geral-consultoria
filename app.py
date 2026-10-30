"""Sistema Geral de Consultoria — mesa no Streamlit."""

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from motor import (
    AREA_PADRAO,
    OUTRA_CIDADE,
    TIPO_LABEL,
    UFS,
    Intake,
    brl,
    cidades_da_uf,
    avaliar,
    manuais_no_prazo,
    montar_fluxo,
    pct,
    pdf_bytes,
    preco_m2,
    simular,
    texto_proposta,
    whatsapp_url,
)

st.set_page_config(
    page_title="Sistema Geral de Consultoria",
    page_icon="⌂",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.4rem; max-width: 1180px; }
      div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e7e1d6;
        border-radius: 12px;
        padding: 0.6rem 0.8rem;
      }
      .aviso {
        background: #f4f7f2;
        border-left: 4px solid #1f6b4a;
        padding: 0.7rem 0.9rem;
        border-radius: 8px;
        color: #1c1917;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Sistema Geral de Consultoria")
st.caption("Simulação de financiamento e fluxo da construtora. Não é carta de crédito da Caixa.")


def _num(label, value, step, key, help_text=None):
    return st.number_input(label, min_value=0.0, value=float(value), step=float(step), key=key, help=help_text)


c1, c2, c3 = st.columns(3)
with c1:
    cliente = st.text_input("Cliente", key="cliente")
with c2:
    consultor = st.text_input("Consultor", key="consultor")
with c3:
    gerente = st.text_input("E-mail do gerente", key="gerente")

st.subheader("Imóvel")
i1, i2, i3, i4 = st.columns(4)
uf_labels = {code: f"{code} — {nome}" for code, nome in UFS}
with i1:
    uf = st.selectbox("Estado", [c[0] for c in UFS], index=24, format_func=lambda c: uf_labels[c], key="uf")
cidades = cidades_da_uf(uf)
if st.session_state.get("_uf_vista") != uf:
    st.session_state["_uf_vista"] = uf
    st.session_state["cidade"] = "Hortolândia" if uf == "SP" and "Hortolândia" in cidades else cidades[0]
with i2:
    cidade = st.selectbox("Cidade", cidades, key="cidade")
with i3:
    tipo = st.selectbox(
        "Tipo",
        list(TIPO_LABEL),
        format_func=lambda t: TIPO_LABEL[t],
        key="tipo",
    )
with i4:
    objetivo = st.selectbox("Imóvel", ["novo", "usado"], format_func=lambda o: "Novo" if o == "novo" else "Usado")

area_sugerida = AREA_PADRAO[tipo]
a1, a2, a3 = st.columns(3)
with a1:
    area = st.number_input("Área (m²)", min_value=0.0, value=float(area_sugerida), step=1.0, key=f"area_{tipo}")
unit = preco_m2(uf, cidade, tipo)
if unit is None:
    st.session_state["seguir_tabela"] = False
elif "seguir_tabela" not in st.session_state:
    st.session_state["seguir_tabela"] = True
with a2:
    seguir = st.checkbox(
        "Usar o preço do m² da cidade",
        disabled=unit is None,
        key="seguir_tabela",
        help="Hortolândia, Monte Mor, Sumaré, Piracicaba, Sorocaba, Paulínia, Salto, São José do Rio Preto e Indaiatuba têm tabela.",
    )
sugerido = round(unit * area) if unit and area > 0 else None
if "valor_imovel" not in st.session_state:
    st.session_state["valor_imovel"] = float(sugerido or 350000)
if seguir and sugerido:
    st.session_state["valor_imovel"] = float(sugerido)
with a3:
    valor = st.number_input(
        "Valor do imóvel (R$)",
        min_value=0.0,
        step=1000.0,
        key="valor_imovel",
        disabled=bool(seguir and sugerido),
    )
if unit:
    st.markdown(
        f"<div class='aviso'>Referência de anúncio em <b>{cidade}</b>: {brl(unit)}/m² · "
        f"esta unidade fica em <b>{brl(sugerido or 0)}</b>. Não é o laudo da Caixa.</div>",
        unsafe_allow_html=True,
    )
elif cidade != OUTRA_CIDADE:
    st.caption("Esta cidade ainda não tem tabela de m². Digite o valor do imóvel.")

st.subheader("Comprador e crédito")
b1, b2, b3, b4 = st.columns(4)
with b1:
    renda = _num("Renda do titular (R$)", 7500, 100, "renda")
with b2:
    renda2 = _num("Renda de quem compõe (R$)", 0, 100, "renda2")
with b3:
    nasc = st.date_input("Nascimento", value=date(1988, 5, 12), min_value=date(1930, 1, 1), max_value=date.today())
with b4:
    deps = st.number_input("Dependentes", min_value=0, max_value=10, value=0, step=1)

c4, c5, c6, c7 = st.columns(4)
with c4:
    entrada = _num("Entrada própria (R$)", 75000, 1000, "entrada")
with c5:
    fgts = _num("Saldo FGTS (R$)", 30000, 1000, "fgts")
with c6:
    prazo = st.number_input("Prazo (anos)", min_value=1, max_value=35, value=30, step=1)
with c7:
    linha = st.selectbox(
        "Linha",
        ["melhor", "mcmv", "procotista", "sbpe"],
        format_func=lambda x: {
            "melhor": "Melhor enquadramento",
            "mcmv": "Minha Casa Minha Vida",
            "procotista": "Pró-Cotista",
            "sbpe": "SBPE",
        }[x],
    )
indexador = st.radio(
    "Correção do contrato",
    ["TR", "fixa"],
    horizontal=True,
    format_func=lambda x: "TR (SAC até 35 anos, PRICE até 30)" if x == "TR" else "Taxa fixa (SAC até 30, PRICE até 20)",
)
ja_benef = st.checkbox("Já usou o subsídio do Minha Casa, Minha Vida", value=False)

with st.expander("Regras do cliente e FGTS"):
    g1, g2, g3 = st.columns(3)
    with g1:
        nome_limpo = st.checkbox("Nome limpo", value=True)
        tres_anos = st.checkbox("3 anos de FGTS", value=True)
        clt = st.checkbox("CLT ativa", value=True)
        usar_fgts = st.checkbox("Usar FGTS na entrada", value=True)
    with g2:
        saque = st.checkbox("Saque-aniversário bloqueando o saldo", value=False)
        imovel_regiao = st.checkbox("Já tem imóvel na região", value=False)
        sfh_ativo = st.checkbox("Financiamento SFH ativo", value=False)
        relacao = st.checkbox("Tem relacionamento com a Caixa", value=True)
    with g3:
        ppp = st.checkbox("PPP — FGTS cobre até 12 parcelas", value=False)
        futuro = st.checkbox("FGTS Futuro (renda até R$ 2.640)", value=False)
        modo24 = st.selectbox(
            "FGTS a cada 24 meses",
            ["nenhum", "prestacao", "prazo"],
            format_func=lambda m: {"nenhum": "Não usar", "prestacao": "Baixar a parcela", "prazo": "Encurtar o prazo"}[m],
        )
        aporte = _num("Depósito mensal de FGTS (R$)", round(renda * 0.08) if modo24 != "nenhum" else 0, 50, "aporte")
        valoriza = st.number_input("Valorização do imóvel (% ao ano)", min_value=0.0, max_value=30.0, value=4.0, step=0.5)

intake = Intake(
    client_name=cliente,
    consultor_name=consultor,
    email_gerente=gerente,
    tipo_imovel=tipo,
    uf=uf,
    cidade=cidade,
    area_m2=area,
    valor_imovel=float(valor),
    objetivo=objetivo,
    renda=float(renda),
    renda_composta=float(renda2),
    nascimento=nasc.isoformat(),
    dependentes=int(deps),
    nome_limpo=nome_limpo,
    tempo_fgts_3_anos=tres_anos,
    clt_ativa=clt,
    saque_aniversario=saque,
    imovel_na_regiao=imovel_regiao,
    financiamento_sfh_ativo=sfh_ativo,
    relacionamento_caixa=relacao,
    usar_fgts=usar_fgts,
    saldo_fgts=float(fgts),
    entrada=float(entrada),
    usar_ppp=ppp,
    usar_fgts_futuro=futuro,
    modo_fgts_24=modo24,
    aporte_mensal_fgts=float(aporte or 0),
    valorizacao_anual=float(valoriza),
    linha_preferida=linha,
    prazo_anos=int(prazo),
    indexador=indexador,
    ja_beneficiado=ja_benef,
)

enq = avaliar(intake)
sim = simular(intake, enq)

st.subheader("Resultado")
if not enq.pode_simular:
    st.error("Esta combinação não fecha uma simulação. Veja os avisos abaixo e ajuste entrada, idade ou restrição.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Linha", enq.linha or "—")
m2.metric("Taxa", pct(enq.taxa_anual) + " a.a.")
m3.metric("Prazo", f"{enq.prazo_efetivo_anos} anos")
m4.metric("Sistema", enq.sistema_habitacional)
st.caption(enq.linha_motivo + " " + enq.taxa_detalhe)
st.caption("Cada parcela já inclui R$ 25 de taxa de administração. MIP e DFI não entram — a alíquota sai no contrato da Caixa.")

s1, s2 = st.columns(2)
with s1:
    st.markdown("**SAC — parcela cai**")
    st.metric("1ª parcela", brl(sim["sac"]["primeira"]))
    st.write(f"Última parcela: {brl(sim['sac']['ultima'])}")
    st.write(f"Financiado: {brl(sim['sac']['valor_financiado'])}")
    st.write(f"No bolso (1ª): {brl(sim['sac']['primeira_cliente'])}")
    st.write(f"Juros totais: {brl(sim['sac']['juros'])}")
    st.write(f"Renda mínima (30%): {brl(sim['sac']['renda_minima'])}")
with s2:
    st.markdown("**PRICE — parcela fixa**")
    if enq.price_disponivel and sim["price"]["ok"]:
        st.metric("Parcela", brl(sim["price"]["primeira"]))
        st.write(f"Financiado: {brl(sim['price']['valor_financiado'])}")
        st.write(f"No bolso (1ª): {brl(sim['price']['primeira_cliente'])}")
        st.write(f"Juros totais: {brl(sim['price']['juros'])}")
        st.write(f"Juros a mais que o SAC: {brl(sim['economia_juros'])}")
    else:
        st.info("PRICE indisponível nesta operação.")

st.write(
    f"Entrada usada {brl(enq.sac.entrada_usada)} · FGTS {brl(enq.sac.fgts_usado)} · "
    f"subsídio {brl(enq.subsidio)} · imóvel ao fim do prazo {brl(sim['sac']['imovel_fim'])} · "
    f"patrimônio estimado {brl(sim['sac']['patrimonio_fim'])}."
)

for msg in enq.mensagens:
    if msg.nivel == "bloqueio":
        st.error(f"**{msg.titulo}.** {msg.detalhe}")
    elif msg.nivel == "alerta":
        st.warning(f"**{msg.titulo}.** {msg.detalhe}")
    elif msg.codigo in ("subsidio", "fgts-ok", "iof", "fgts-futuro"):
        st.info(f"**{msg.titulo}.** {msg.detalhe}")

chart_rows = []
for nome, bloco, cor in (("SAC", sim["sac"], "#1f6b4a"), ("PRICE", sim["price"], "#c46b2c")):
    for row in bloco["cronograma"]:
        if row["mes"] == 1 or row["mes"] % 6 == 0 or row["mes"] == bloco["prazo_meses"]:
            chart_rows.append({
                "Mês": row["mes"],
                "Parcela": round(row["prestacao"], 2),
                "Saldo": round(row["saldo"], 2),
                "Imóvel": round(row["imovel"], 2),
                "Sistema": nome,
            })
if chart_rows:
    df = pd.DataFrame(chart_rows)
    st.subheader("Gráficos")
    g1, g2 = st.columns(2)
    base = alt.Chart(df).encode(x=alt.X("Mês:Q", title="Mês"), color=alt.Color("Sistema:N", scale=alt.Scale(range=["#1f6b4a", "#c46b2c"])))
    with g1:
        st.altair_chart(base.mark_line().encode(y=alt.Y("Parcela:Q", title="Parcela (R$)")).properties(height=260), use_container_width=True)
    with g2:
        st.altair_chart(base.mark_line().encode(y=alt.Y("Saldo:Q", title="Saldo devedor (R$)")).properties(height=260), use_container_width=True)

st.subheader("Fluxo da construtora")
st.caption("Unidade − financiamento − FGTS − subsídio = fluxo de entrada. A Caixa só começa depois das chaves.")
f1, f2, f3, f4 = st.columns(4)
with f1:
    sistema_fluxo = st.selectbox("Tabela do fluxo", ["SAC", "PRICE"], key="fluxo_sis")
with f2:
    meses_obra = st.number_input("Meses de obra", min_value=0, max_value=120, value=17, step=1)
with f3:
    total_parc = st.number_input("Total de parcelas da entrada", min_value=0, max_value=120, value=59, step=1)
with f4:
    ato = _num("Ato (R$)", 0, 500, "ato")

usar_nums = st.checkbox("Usar financiamento, FGTS, subsídio e parcela Caixa da simulação", value=True)
fin_in = fgts_in = sub_in = caixa_in = None
if not usar_nums:
    n1, n2, n3, n4 = st.columns(4)
    with n1:
        fin_in = _num("Financiamento (R$)", sim["sac"]["valor_financiado"], 1000, "fin_fluxo")
    with n2:
        fgts_in = _num("FGTS no fluxo (R$)", enq.sac.fgts_usado, 1000, "fgts_fluxo")
    with n3:
        sub_in = _num("Subsídio no fluxo (R$)", enq.subsidio, 500, "sub_fluxo")
    with n4:
        caixa_in = _num("Parcela Caixa (R$)", sim["sac"]["primeira"], 50, "caixa_fluxo")

intake.fluxo_sistema = sistema_fluxo
intake.fluxo_meses_obra = int(meses_obra)
intake.fluxo_total_mensais = int(total_parc)
intake.fluxo_ato = float(ato)
intake.fluxo_financiamento = None if usar_nums else float(fin_in)
intake.fluxo_fgts = None if usar_nums else float(fgts_in)
intake.fluxo_subsidio = None if usar_nums else float(sub_in)
intake.fluxo_parcela_caixa = None if usar_nums else float(caixa_in)
intake.fluxo_valor_unidade = float(valor)

inicio = date.today().replace(day=1)
slots = manuais_no_prazo(inicio, int(meses_obra))
manuais = {}
if slots:
    st.markdown("**Manuais de dezembro, durante a obra**")
    cols = st.columns(min(4, len(slots)))
    for i, slot in enumerate(slots):
        with cols[i % len(cols)]:
            manuais[str(slot["ano"])] = st.number_input(
                f"Manual dez/{slot['ano']}",
                min_value=0.0,
                value=0.0,
                step=500.0,
                key=f"manual_{slot['ano']}_{int(meses_obra)}",
            )
intake.fluxo_manuais = manuais

fluxo = montar_fluxo(sim, inicio)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Fluxo de entrada", brl(fluxo["fluxo_entrada"]))
k2.metric("Parcela da obra", brl(fluxo["parcela_mensal"]))
k3.metric("Pós-chaves", f"{fluxo['meses_pos']} meses")
k4.metric("Parcela morando", brl(fluxo["parcela_morando"]))
st.write(
    f"Unidade {brl(fluxo['valor_unidade'])} − financiamento {brl(fluxo['financiamento'])} − "
    f"FGTS {brl(fluxo['fgts'])} − subsídio {brl(fluxo['subsidio'])}. "
    f"Ato {brl(fluxo['ato'])}. Manuais {brl(fluxo['soma_manuais'])}. "
    f"A parcela da Caixa ({brl(fluxo['parcela_caixa'])}) só entra depois das chaves."
)
if fluxo.get("juros_obra", 0) > 0:
    st.info(
        f"Juros de obra estimados, só enquanto a planta não entrega: {brl(fluxo['juros_obra'])} no total "
        f"(média {brl(fluxo['juros_obra_medio'])} por mês). "
        f"MCMV e Pró-Cotista usam 0,28% ao mês; SBPE usa 0,43%, sobre o saldo que a Caixa vai liberando. "
        f"Isso não entra na parcela da construtora."
    )
if fluxo["alerta"]:
    st.warning(fluxo["alerta"])
if fluxo["anos"]:
    tabela = pd.DataFrame(fluxo["anos"])
    tabela = tabela.rename(columns={
        "ano": "Ano",
        "ato": "Ato",
        "mensais_obra": "Mensais da obra",
        "qtd_obra": "Qtd obra",
        "manual": "Manual",
        "pos_chaves": "Pós-chaves",
        "qtd_pos": "Qtd pós",
        "caixa": "Caixa",
        "qtd_caixa": "Qtd Caixa",
        "total": "Total no ano",
    })
    money_cols = ["Ato", "Mensais da obra", "Manual", "Pós-chaves", "Caixa", "Total no ano"]
    st.dataframe(
        tabela.style.format({c: lambda v: brl(v) for c in money_cols}),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Proposta")
texto = texto_proposta(sim, fluxo)
st.text_area("Texto para o WhatsApp", texto, height=280)
p1, p2 = st.columns(2)
with p1:
    st.link_button("Abrir no WhatsApp", whatsapp_url(texto), type="primary")
with p2:
    nome_arq = (cliente or "proposta").strip().replace(" ", "-").lower()
    st.download_button(
        "Baixar PDF",
        data=pdf_bytes(texto),
        file_name=f"proposta-{nome_arq}.pdf",
        mime="application/pdf",
    )
st.caption("O WhatsApp abre com o texto. O PDF baixa neste aparelho: anexe o arquivo na conversa.")
