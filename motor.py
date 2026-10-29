"""Motor do Sistema Geral de Consultoria.

Regras de enquadramento, SAC/PRICE, FGTS e fluxo da construtora.
Simulação de mesa — não é carta de crédito da Caixa.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

COMPROMETIMENTO = 0.3
IDADE_LIMITE_ANOS = 80.5
PRAZO_MAX_ANOS = 35
PRAZO_SFI_ANOS = 20
LTV_SAC = 0.8
LTV_PRICE = 0.7
LTV_COMERCIAL = 0.7
TETO_SFH = 1_500_000
TETO_PROCOTISTA = 500_000
RENDA_MCMV_MAX = 13000
RENDA_FGTS_FUTURO = 2640
TAXA_PROCOTISTA = 8.66
IOF_FATOR = 0.0038 + 0.000082 * 365

TipoImovel = Literal["apartamento", "casa_condominio", "casa_rua", "comercial", "terreno"]
Sistema = Literal["SAC", "PRICE"]
Linha = Literal["MCMV", "PROCOTISTA", "SBPE"]
Faixa = Literal[1, 2, 3, 4]
Grupo = Literal["A", "B", "C"]

TIPO_LABEL = {
    "apartamento": "Apartamento",
    "casa_condominio": "Casa em condomínio",
    "casa_rua": "Casa de rua",
    "comercial": "Comercial",
    "terreno": "Terreno",
}

AREA_PADRAO = {
    "apartamento": 58,
    "casa_condominio": 90,
    "casa_rua": 80,
    "comercial": 45,
    "terreno": 250,
}

REGIAO = {
    "AC": "N", "AP": "N", "AM": "N", "PA": "N", "RO": "N", "RR": "N", "TO": "N",
    "AL": "NE", "BA": "NE", "CE": "NE", "MA": "NE", "PB": "NE", "PE": "NE",
    "PI": "NE", "RN": "NE", "SE": "NE",
    "DF": "CO", "GO": "CO", "MT": "CO", "MS": "CO",
    "ES": "SE", "MG": "SE", "RJ": "SE", "SP": "SE",
    "PR": "S", "RS": "S", "SC": "S",
}

UFS = [
    ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"), ("AM", "Amazonas"),
    ("BA", "Bahia"), ("CE", "Ceará"), ("DF", "Distrito Federal"), ("ES", "Espírito Santo"),
    ("GO", "Goiás"), ("MA", "Maranhão"), ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"),
    ("MG", "Minas Gerais"), ("PA", "Pará"), ("PB", "Paraíba"), ("PR", "Paraná"),
    ("PE", "Pernambuco"), ("PI", "Piauí"), ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"),
    ("RS", "Rio Grande do Sul"), ("RO", "Rondônia"), ("RR", "Roraima"), ("SC", "Santa Catarina"),
    ("SP", "São Paulo"), ("SE", "Sergipe"), ("TO", "Tocantins"),
]


def _tabela(apartamento: float, terreno: float) -> dict:
    return {
        "apartamento": apartamento,
        "casa_condominio": round(apartamento * 0.86),
        "casa_rua": round(apartamento * 0.74),
        "comercial": round(apartamento * 0.78),
        "terreno": terreno,
    }


# R$/m² de referência de anúncio (não é laudo). Praças pedidas pelo consultor.
CIDADES = [
    {"nome": "São Paulo", "uf": "SP", "grupo": "A"},
    {"nome": "Guarulhos", "uf": "SP", "grupo": "A"},
    {"nome": "Campinas", "uf": "SP", "grupo": "A"},
    {"nome": "São Bernardo do Campo", "uf": "SP", "grupo": "A"},
    {"nome": "Santo André", "uf": "SP", "grupo": "A"},
    {"nome": "Osasco", "uf": "SP", "grupo": "A"},
    {"nome": "Santos", "uf": "SP", "grupo": "A"},
    {"nome": "Ribeirão Preto", "uf": "SP", "grupo": "B"},
    {"nome": "Sorocaba", "uf": "SP", "grupo": "B", "m2": _tabela(6800, 1100)},
    {"nome": "São José dos Campos", "uf": "SP", "grupo": "B"},
    {"nome": "São José do Rio Preto", "uf": "SP", "grupo": "B", "m2": _tabela(6075, 980)},
    {"nome": "Indaiatuba", "uf": "SP", "grupo": "B", "m2": _tabela(7600, 1450)},
    {"nome": "Piracicaba", "uf": "SP", "grupo": "B", "m2": _tabela(5500, 780)},
    {"nome": "Hortolândia", "uf": "SP", "grupo": "B", "m2": _tabela(5600, 900)},
    {"nome": "Sumaré", "uf": "SP", "grupo": "B", "m2": _tabela(5200, 850)},
    {"nome": "Paulínia", "uf": "SP", "grupo": "B", "m2": _tabela(5400, 860)},
    {"nome": "Salto", "uf": "SP", "grupo": "C", "m2": _tabela(4900, 750)},
    {"nome": "Monte Mor", "uf": "SP", "grupo": "C", "m2": _tabela(4300, 620)},
    {"nome": "Rio de Janeiro", "uf": "RJ", "grupo": "A"},
    {"nome": "Niterói", "uf": "RJ", "grupo": "A"},
    {"nome": "São Gonçalo", "uf": "RJ", "grupo": "B"},
    {"nome": "Duque de Caxias", "uf": "RJ", "grupo": "B"},
    {"nome": "Nova Iguaçu", "uf": "RJ", "grupo": "B"},
    {"nome": "Brasília", "uf": "DF", "grupo": "A"},
    {"nome": "Belo Horizonte", "uf": "MG", "grupo": "A"},
    {"nome": "Uberlândia", "uf": "MG", "grupo": "B"},
    {"nome": "Contagem", "uf": "MG", "grupo": "B"},
    {"nome": "Juiz de Fora", "uf": "MG", "grupo": "B"},
    {"nome": "Vitória", "uf": "ES", "grupo": "B"},
    {"nome": "Vila Velha", "uf": "ES", "grupo": "B"},
    {"nome": "Curitiba", "uf": "PR", "grupo": "B"},
    {"nome": "Londrina", "uf": "PR", "grupo": "B"},
    {"nome": "Maringá", "uf": "PR", "grupo": "B"},
    {"nome": "Porto Alegre", "uf": "RS", "grupo": "B"},
    {"nome": "Caxias do Sul", "uf": "RS", "grupo": "B"},
    {"nome": "Florianópolis", "uf": "SC", "grupo": "B"},
    {"nome": "Joinville", "uf": "SC", "grupo": "B"},
    {"nome": "Blumenau", "uf": "SC", "grupo": "B"},
    {"nome": "Salvador", "uf": "BA", "grupo": "B"},
    {"nome": "Feira de Santana", "uf": "BA", "grupo": "C"},
    {"nome": "Recife", "uf": "PE", "grupo": "B"},
    {"nome": "Jaboatão dos Guararapes", "uf": "PE", "grupo": "B"},
    {"nome": "Fortaleza", "uf": "CE", "grupo": "B"},
    {"nome": "Natal", "uf": "RN", "grupo": "B"},
    {"nome": "João Pessoa", "uf": "PB", "grupo": "B"},
    {"nome": "Maceió", "uf": "AL", "grupo": "B"},
    {"nome": "Aracaju", "uf": "SE", "grupo": "B"},
    {"nome": "Teresina", "uf": "PI", "grupo": "B"},
    {"nome": "São Luís", "uf": "MA", "grupo": "B"},
    {"nome": "Belém", "uf": "PA", "grupo": "B"},
    {"nome": "Ananindeua", "uf": "PA", "grupo": "B"},
    {"nome": "Manaus", "uf": "AM", "grupo": "B"},
    {"nome": "Macapá", "uf": "AP", "grupo": "C"},
    {"nome": "Boa Vista", "uf": "RR", "grupo": "C"},
    {"nome": "Porto Velho", "uf": "RO", "grupo": "C"},
    {"nome": "Rio Branco", "uf": "AC", "grupo": "C"},
    {"nome": "Palmas", "uf": "TO", "grupo": "C"},
    {"nome": "Goiânia", "uf": "GO", "grupo": "B"},
    {"nome": "Aparecida de Goiânia", "uf": "GO", "grupo": "B"},
    {"nome": "Cuiabá", "uf": "MT", "grupo": "B"},
    {"nome": "Campo Grande", "uf": "MS", "grupo": "B"},
]

OUTRA_CIDADE = "Outra cidade"


def round2(value: float) -> float:
    return round((value + 1e-9) * 100) / 100


def brl(value: float) -> str:
    neg = value < 0
    n = f"{abs(value):,.2f}"
    n = n.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {n}" if neg else f"R$ {n}"


def pct(value: float, digits: int = 2) -> str:
    n = f"{value:,.{digits}f}"
    n = n.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{n}%"


def cidades_da_uf(uf: str) -> list[str]:
    nomes = sorted((c["nome"] for c in CIDADES if c["uf"] == uf), key=lambda s: s)
    return nomes + [OUTRA_CIDADE]


def preco_m2(uf: str, cidade: str, tipo: str) -> float | None:
    for c in CIDADES:
        if c["uf"] == uf and c["nome"] == cidade and "m2" in c:
            return float(c["m2"][tipo])
    return None


def resolver_grupo(uf: str, cidade: str) -> Grupo:
    if not cidade or cidade == OUTRA_CIDADE:
        return "C"
    for c in CIDADES:
        if c["uf"] == uf and c["nome"] == cidade:
            return c["grupo"]  # type: ignore[return-value]
    return "C"


def is_norte_nordeste(uf: str) -> bool:
    return REGIAO.get(uf) in ("N", "NE")


def is_residencial(tipo: str) -> bool:
    return tipo in ("apartamento", "casa_condominio", "casa_rua")


@dataclass
class Intake:
    client_name: str = ""
    consultor_name: str = ""
    email_gerente: str = ""
    tipo_imovel: str = "apartamento"
    uf: str = "SP"
    cidade: str = "Hortolândia"
    area_m2: float = 58
    valor_imovel: float = 324800
    valor_avaliacao: float = 0
    objetivo: str = "novo"
    renda: float = 7500
    renda_composta: float = 0
    nascimento: str = "1988-05-12"
    dependentes: int = 0
    nacionalidade: str = "brasileiro"
    nome_limpo: bool = True
    tempo_fgts_3_anos: bool = True
    clt_ativa: bool = True
    saque_aniversario: bool = False
    imovel_na_regiao: bool = False
    financiamento_sfh_ativo: bool = False
    relacionamento_caixa: bool = True
    usar_fgts: bool = True
    saldo_fgts: float = 30000
    entrada: float = 75000
    usar_ppp: bool = False
    usar_fgts_futuro: bool = False
    modo_fgts_24: str = "nenhum"
    aporte_mensal_fgts: float = 0
    modo_amort_propria: str = "nenhum"
    amort_propria_mensal: float = 0
    financiar_taxas: bool = False
    aliquota_itbi: float = 2
    valorizacao_anual: float = 4
    linha_preferida: str = "melhor"
    sistema_preferido: str = "ambos"
    prazo_anos: int = 30
    taxa_manual: float | None = None
    fluxo_sistema: str = "SAC"
    fluxo_valor_unidade: float | None = None
    fluxo_financiamento: float | None = None
    fluxo_fgts: float | None = None
    fluxo_subsidio: float | None = None
    fluxo_parcela_caixa: float | None = None
    fluxo_ato: float = 0
    fluxo_meses_obra: int = 17
    fluxo_total_mensais: int = 59
    fluxo_manuais: dict = field(default_factory=dict)


@dataclass
class Condicao:
    ltv_max: float
    max_financiado: float
    entrada_minima: float
    fgts_usado: float
    entrada_usada: float
    valor_financiado: float
    cobertura_ok: bool


@dataclass
class Mensagem:
    nivel: str
    codigo: str
    titulo: str
    detalhe: str


@dataclass
class Enquadramento:
    idade_anos: float
    prazo_maximo_anos: int
    prazo_efetivo_anos: int
    valor_base: float
    residencial: bool
    mcmv_possivel: bool
    mcmv_motivo: str | None
    faixa_mcmv: int | None
    teto_mcmv: float | None
    linha: str | None
    linha_motivo: str
    sistema_habitacional: str
    price_disponivel: bool
    procotista_possivel: bool
    fgts_futuro_elegivel: bool
    fgts_futuro_mensal: float
    custos_cartorio: float
    taxas_financiadas_sac: float
    iof_sac: float
    laudo_minimo_sac: float
    renda_familiar: float
    taxa_anual: float
    taxa_fonte: str
    taxa_detalhe: str
    subsidio: float
    fgts_elegivel: bool
    fgts_motivo: str | None
    cotista_fgts: bool
    sac: Condicao
    price: Condicao
    mensagens: list
    pode_simular: bool


def idade_anos(iso: str, hoje: date | None = None) -> float:
    hoje = hoje or date.today()
    parts = iso.split("-")
    if len(parts) != 3:
        return 0
    try:
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        birth = date(y, m, d)
    except ValueError:
        return 0
    if hoje < birth:
        return 0
    return (hoje - birth).days / 365.25


def prazo_maximo_por_idade(idade: float) -> int:
    if idade < 16:
        return 0
    meses = int((IDADE_LIMITE_ANOS - idade) * 12)
    if meses < 12:
        return 0
    return min(PRAZO_MAX_ANOS, meses // 12)


def faixa_mcmv(renda: float) -> int | None:
    if renda <= 0:
        return None
    if renda <= 3200:
        return 1
    if renda <= 5000:
        return 2
    if renda <= 9600:
        return 3
    if renda <= RENDA_MCMV_MAX:
        return 4
    return None


def teto_imovel_mcmv(faixa: int, grupo: str) -> float:
    if faixa == 3:
        return 400000
    if faixa == 4:
        return 600000
    if grupo == "A":
        return 275000
    if grupo == "B":
        return 250000
    return 210000


def _clamp(n: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, n))


def subsidio_mcmv(renda: float, faixa: int | None, dependentes: int) -> float:
    if faixa not in (1, 2):
        return 0
    if faixa == 1:
        t = _clamp((renda - 2000) / 1200, 0, 1)
        base = 55000 - t * 23000
    else:
        t = _clamp((renda - 3200) / 1800, 0, 1)
        base = 32000 * (1 - t)
    extra = min(max(0, dependentes), 3) * 1500
    teto = 55000 if faixa == 1 else 32000
    return round2(min(teto, max(0, base + extra)))


def taxa_mcmv(faixa: int, renda: float, uf: str, cotista: bool) -> float:
    nn = is_norte_nordeste(uf)
    if faixa == 1:
        if nn:
            return 4.0 if cotista else 4.5
        return 4.25 if cotista else 5.0
    if faixa == 2:
        t = _clamp((renda - 3200) / 1800, 0, 1)
        base = 4.75 + t * 2.25
        regional = -0.25 if nn else 0
        extra = 0 if cotista else 0.5
        return round2(base + regional + extra)
    if faixa == 3:
        return 7.66 if cotista else 8.16
    return 10.0 if cotista else 10.5


def taxa_sbpe(tipo: str, objetivo: str, relacionamento: bool, acima_sfh: bool) -> float:
    base = 10.9
    if tipo == "comercial":
        base = 12.49
    elif tipo == "terreno":
        base = 9.49
    elif acima_sfh:
        base = 11.7
    elif objetivo == "usado":
        base = 11.4
    if relacionamento:
        base -= 0.5
    return round2(base)


def _montar_sistema(valor_base, ltv, entrada, fgts, subsidio) -> Condicao:
    max_fin = round2(valor_base * ltv)
    falta = round2(max(0, valor_base - max_fin))
    apos = max(0, valor_base - subsidio)
    fgts_usado = min(fgts, apos)
    restante = apos - fgts_usado
    entrada_usada = min(entrada, restante)
    restante -= entrada_usada
    valor_fin = round2(min(max_fin, restante))
    coberto = round2(subsidio + fgts_usado + entrada_usada + valor_fin)
    if coberto + 0.05 < valor_base:
        return Condicao(ltv, max_fin, falta, fgts_usado, entrada_usada, 0, False)
    if valor_fin < 0.01:
        valor_fin = 0
    return Condicao(ltv, max_fin, falta, fgts_usado, entrada_usada, valor_fin, True)


def _aplicar_custos(cond: Condicao, custos: float, financiar: bool, sfi: bool):
    if not cond.cobertura_ok or cond.valor_financiado <= 0:
        return cond, 0.0, 0.0
    valor = cond.valor_financiado
    taxas = 0.0
    if financiar and custos > 0:
        room = max(0, cond.max_financiado - valor)
        cap = valor * 0.05
        taxas = round2(min(custos, cap, room))
        valor = round2(valor + taxas)
    iof = 0.0
    if sfi and valor > 0:
        iof = round2(valor * IOF_FATOR)
        valor = round2(valor + iof)
    novo = deepcopy(cond)
    novo.valor_financiado = valor
    return novo, taxas, iof


def avaliar(intake: Intake, hoje: date | None = None) -> Enquadramento:
    hoje = hoje or date.today()
    msgs: list[Mensagem] = []

    def push(nivel, codigo, titulo, detalhe):
        msgs.append(Mensagem(nivel, codigo, titulo, detalhe))

    residencial = is_residencial(intake.tipo_imovel)
    comercial = intake.tipo_imovel == "comercial"
    terreno = intake.tipo_imovel == "terreno"
    idade = idade_anos(intake.nascimento, hoje)
    prazo_idade = prazo_maximo_por_idade(idade)
    prazo_tipo = PRAZO_SFI_ANOS if (comercial or terreno) else PRAZO_MAX_ANOS
    prazo_max = min(prazo_idade, prazo_tipo)
    prazo_efetivo = min(max(1, int(round(intake.prazo_anos or 1))), max(0, prazo_max))
    avaliacao = intake.valor_avaliacao if intake.valor_avaliacao > 0 else intake.valor_imovel
    valor_base = round2(min(max(0, intake.valor_imovel), max(0, avaliacao)))
    renda_fam = round2(max(0, intake.renda) + max(0, intake.renda_composta))
    acima = residencial and valor_base > TETO_SFH
    sfi = (not residencial) or acima
    faixa = faixa_mcmv(renda_fam)
    grupo = resolver_grupo(intake.uf, intake.cidade)
    teto = teto_imovel_mcmv(faixa, grupo) if faixa else None
    cotista = intake.tempo_fgts_3_anos

    if 0 < idade < 18:
        push("alerta", "idade-menor", "Proponente com menos de 18 anos",
             "A Caixa aceita a partir de 16 anos somente se emancipado.")
    if prazo_max <= 0:
        push("bloqueio", "idade-prazo", "Idade fora do limite da Caixa",
             "A soma da idade com o prazo não pode passar de 80 anos e 6 meses.")
    elif intake.prazo_anos > prazo_max:
        push("alerta", "prazo-ajustado", f"Prazo ajustado para {prazo_max} anos",
             f"Com {idade:.1f} anos, o prazo máximo nesta operação é {prazo_max} anos.")

    if intake.nacionalidade == "estrangeiro_temporario":
        push("bloqueio", "visto", "Visto temporário não enquadra",
             "A Caixa exige brasileiro ou estrangeiro com visto permanente.")
    if not intake.nome_limpo:
        push("bloqueio", "restricao", "Restrição cadastral",
             "Nome com apontamento em SPC/Serasa costuma impedir a aprovação.")

    fgts_ok = True
    fgts_motivo = None
    if not residencial:
        fgts_ok = False
        fgts_motivo = "Comercial ou terreno não usa FGTS na compra."
    elif acima:
        fgts_ok = False
        fgts_motivo = "Acima de R$ 1,5 milhão o FGTS não entra."
    elif not intake.tempo_fgts_3_anos:
        fgts_ok = False
        fgts_motivo = "Uso do FGTS exige ao menos 36 meses de contribuição."
    elif intake.financiamento_sfh_ativo:
        fgts_ok = False
        fgts_motivo = "Financiamento ativo no SFH impede o uso do FGTS."
    elif intake.imovel_na_regiao:
        fgts_ok = False
        fgts_motivo = "Imóvel residencial na mesma região impede o FGTS."
    elif intake.saque_aniversario:
        fgts_ok = False
        fgts_motivo = "Saldo bloqueado pelo saque-aniversário."
    if intake.usar_fgts and not fgts_ok and fgts_motivo:
        push("alerta", "fgts-bloqueado", "FGTS não pode entrar nesta operação", fgts_motivo)
    elif intake.usar_fgts and fgts_ok:
        push("info", "fgts-ok", "FGTS elegível para a entrada",
             "As regras declaradas permitem usar o saldo na entrada.")

    mcmv_reasons = []
    if not residencial:
        mcmv_reasons.append("MCMV é só para habitação residencial.")
    if intake.financiamento_sfh_ativo:
        mcmv_reasons.append("Financiamento SFH ativo impede o MCMV.")
    if intake.imovel_na_regiao:
        mcmv_reasons.append("Imóvel residencial na mesma região impede o MCMV.")
    if not faixa:
        mcmv_reasons.append("Renda familiar acima de R$ 13.000 fica fora do MCMV.")
    if faixa and teto and valor_base > teto:
        mcmv_reasons.append(f"Valor do imóvel ({brl(valor_base)}) supera o teto da faixa ({brl(teto)}).")
    mcmv_possivel = len(mcmv_reasons) == 0 and faixa is not None
    mcmv_motivo = None if mcmv_possivel else (mcmv_reasons[0] if mcmv_reasons else None)

    proco = []
    if not residencial:
        proco.append("Pró-Cotista é só para imóvel residencial.")
    if intake.objetivo != "novo":
        proco.append("Pró-Cotista aceita apenas imóvel novo.")
    if valor_base > TETO_PROCOTISTA:
        proco.append(f"O teto do Pró-Cotista é {brl(TETO_PROCOTISTA)}.")
    if not intake.tempo_fgts_3_anos:
        proco.append("É obrigatório ter 3 anos de FGTS.")
    saldo_dez = intake.saldo_fgts + 0.5 >= valor_base * 0.1
    if not intake.clt_ativa and not saldo_dez:
        proco.append("Sem carteira assinada, o FGTS precisa cobrir 10% do imóvel.")
    if intake.imovel_na_regiao:
        proco.append("Não pode ter outro imóvel residencial na mesma região.")
    if intake.financiamento_sfh_ativo:
        proco.append("Financiamento ativo no SFH impede o Pró-Cotista.")
    if not intake.nome_limpo:
        proco.append("Restrição cadastral impede o Pró-Cotista.")
    procotista_ok = len(proco) == 0 and valor_base > 0

    linha = None
    linha_motivo = ""
    pref = intake.linha_preferida
    if pref == "mcmv":
        if mcmv_possivel:
            linha, linha_motivo = "MCMV", "Enquadramento no Minha Casa, Minha Vida."
        else:
            linha = "SBPE"
            linha_motivo = f"MCMV indisponível: {mcmv_motivo or 'regras não atendidas'}."
            push("alerta", "mcmv-recusado", "MCMV não enquadrou", linha_motivo)
    elif pref == "procotista":
        if procotista_ok:
            linha, linha_motivo = "PROCOTISTA", "Pró-Cotista: imóvel novo até R$ 500 mil."
        else:
            linha = "MCMV" if mcmv_possivel else "SBPE"
            linha_motivo = f"Pró-Cotista indisponível: {proco[0] if proco else 'regras não atendidas'}."
            push("alerta", "procotista-recusado", "Pró-Cotista não enquadrou", linha_motivo)
    elif pref == "sbpe":
        linha = "SBPE"
        linha_motivo = "Linha SBPE escolhida pelo corretor."
    elif mcmv_possivel and faixa and faixa <= 3:
        linha, linha_motivo = "MCMV", "Melhor enquadramento: Minha Casa, Minha Vida."
    elif procotista_ok:
        linha, linha_motivo = "PROCOTISTA", "Melhor enquadramento: Pró-Cotista a 8,66% a.a."
    elif mcmv_possivel:
        linha, linha_motivo = "MCMV", "Melhor enquadramento automático: Minha Casa, Minha Vida."
    else:
        linha = "SBPE"
        linha_motivo = f"SBPE — {mcmv_motivo}" if mcmv_motivo else "SBPE — linha de mercado da Caixa."

    subsidio = subsidio_mcmv(renda_fam, faixa, intake.dependentes) if linha == "MCMV" and faixa in (1, 2) else 0
    if subsidio > 0:
        push("info", "subsidio", "Subsídio estimado na entrada",
             f"Faixa {faixa}: cerca de {brl(subsidio)}. O valor final sai na análise da Caixa.")

    if intake.taxa_manual is not None:
        taxa = round2(max(0, intake.taxa_manual))
        taxa_fonte = "manual"
        taxa_detalhe = "Taxa informada pelo corretor."
    elif linha == "PROCOTISTA":
        taxa = TAXA_PROCOTISTA
        taxa_fonte = "tabela"
        taxa_detalhe = "Pró-Cotista · 8,66% a.a."
    elif linha == "MCMV" and faixa:
        taxa = taxa_mcmv(faixa, renda_fam, intake.uf, cotista)
        taxa_fonte = "tabela"
        taxa_detalhe = f"Tabela MCMV · faixa {faixa}."
    else:
        taxa = taxa_sbpe(intake.tipo_imovel, intake.objetivo, intake.relacionamento_caixa, acima)
        taxa_fonte = "tabela"
        taxa_detalhe = "Tabela SBPE."

    fgts_disp = max(0, intake.saldo_fgts) if intake.usar_fgts and fgts_ok else 0
    ltv_sac = LTV_COMERCIAL if comercial else LTV_SAC
    price_ok = not comercial
    sac = _montar_sistema(valor_base, ltv_sac, max(0, intake.entrada), fgts_disp, subsidio)
    price = (
        _montar_sistema(valor_base, LTV_PRICE, max(0, intake.entrada), fgts_disp, subsidio)
        if price_ok
        else Condicao(0, 0, round2(valor_base), 0, 0, 0, False)
    )
    custos = round2(valor_base * (max(0, intake.aliquota_itbi) / 100) + valor_base * 0.008)
    sac, taxas_sac, iof_sac = _aplicar_custos(sac, custos, intake.financiar_taxas, sfi)
    price, _, _ = _aplicar_custos(price, custos, intake.financiar_taxas, sfi)

    futuro_ok = (
        residencial and not acima and 0 < renda_fam <= RENDA_FGTS_FUTURO
        and intake.tempo_fgts_3_anos and intake.nome_limpo
        and not intake.financiamento_sfh_ativo and not intake.imovel_na_regiao
    )
    futuro_mensal = round2(max(0, intake.renda) * 0.08) if intake.usar_fgts_futuro and futuro_ok else 0
    if intake.usar_fgts_futuro and not futuro_ok:
        push("alerta", "fgts-futuro", "FGTS Futuro não enquadra",
             "Serve para renda familiar de até R$ 2.640, com 3 anos de FGTS.")
    if sfi and iof_sac > 0:
        push("info", "iof", "IOF do SFI no saldo", f"IOF estimado de {brl(iof_sac)} entra no saldo.")
    if not sac.cobertura_ok:
        push("alerta", "entrada-sac", "Entrada insuficiente no SAC",
             f"O SAC financia até {round(ltv_sac * 100)}% ({brl(sac.max_financiado)}).")
    if price_ok and not price.cobertura_ok:
        push("alerta", "entrada-price", "Entrada insuficiente no PRICE",
             f"O PRICE financia até 70% ({brl(price.max_financiado)}).")

    bloqueios = [m for m in msgs if m.nivel == "bloqueio"]
    pode = len(bloqueios) == 0 and valor_base > 0 and prazo_efetivo >= 1 and (sac.cobertura_ok or price.cobertura_ok)
    return Enquadramento(
        idade, prazo_max, prazo_efetivo, valor_base, residencial, mcmv_possivel, mcmv_motivo,
        faixa, teto, linha, linha_motivo, "SFI" if sfi else "SFH", price_ok, procotista_ok,
        futuro_ok, futuro_mensal, custos, taxas_sac, iof_sac,
        (max(0, valor_base - subsidio - fgts_disp - max(0, intake.entrada)) / ltv_sac) if ltv_sac else 0,
        renda_fam, taxa, taxa_fonte, taxa_detalhe, subsidio, fgts_ok, fgts_motivo, cotista,
        sac, price, msgs, pode,
    )


def price_pmt(valor: float, taxa: float, prazo: int) -> float:
    if valor <= 0 or prazo < 1:
        return 0
    if taxa == 0:
        return valor / prazo
    return valor * ((taxa * (1 + taxa) ** prazo) / ((1 + taxa) ** prazo - 1))


def price_nper(saldo: float, taxa: float, prestacao: float) -> int:
    if saldo <= 0.5:
        return 0
    if prestacao <= 0 or taxa <= 0:
        return 420 if prestacao <= 0 else max(1, int(-(-saldo // prestacao)))
    if prestacao <= saldo * taxa + 0.01:
        return 420
    import math
    n = math.log(prestacao / (prestacao - saldo * taxa)) / math.log(1 + taxa)
    return max(1, math.ceil(n - 1e-6))


def _recompor(base: Condicao, valor_base, subsidio, fgts_entrada, entrada) -> Condicao:
    apos = max(0, valor_base - max(0, subsidio))
    fgts_usado = min(max(0, fgts_entrada), apos)
    restante = apos - fgts_usado
    entrada_usada = min(max(0, entrada), restante)
    restante -= entrada_usada
    valor_fin = round2(min(base.max_financiado, max(0, restante)))
    coberto = round2(subsidio + fgts_usado + entrada_usada + valor_fin)
    if coberto + 0.05 < valor_base:
        return Condicao(base.ltv_max, base.max_financiado, base.entrada_minima, round2(fgts_usado), round2(entrada_usada), 0, False)
    if valor_fin < 0.01:
        valor_fin = 0
    return Condicao(base.ltv_max, base.max_financiado, base.entrada_minima, round2(fgts_usado), round2(entrada_usada), valor_fin, True)


def _primeira(sistema, valor, taxa, prazo) -> float:
    if valor <= 0 or prazo < 1:
        return 0
    if sistema == "SAC":
        return valor / prazo + valor * taxa
    return price_pmt(valor, taxa, prazo)


def _reservar_ppp(sistema, enq: Enquadramento, intake: Intake, taxa, prazo):
    base = enq.sac if sistema == "SAC" else enq.price
    pode = enq.fgts_elegivel and intake.saldo_fgts > 0 and (intake.usar_fgts or intake.usar_ppp)
    if not pode or not intake.usar_ppp:
        return base, 0.0
    fgts_total = intake.saldo_fgts
    fgts_entrada = fgts_total if intake.usar_fgts else 0
    reserva = 0.0
    for _ in range(12):
        cond = _recompor(base, enq.valor_base, enq.subsidio, fgts_entrada, intake.entrada)
        p = _primeira(sistema, cond.valor_financiado, taxa, prazo)
        nova = round2(min(fgts_total, p * min(12, prazo)))
        novo_fgts = round2(fgts_total - nova) if intake.usar_fgts else 0
        reserva = nova
        if abs(novo_fgts - fgts_entrada) < 1:
            fgts_entrada = novo_fgts
            break
        fgts_entrada = novo_fgts
    return _recompor(base, enq.valor_base, enq.subsidio, fgts_entrada, intake.entrada), reserva


def simular_cronograma(sistema, valor, taxa, prazo, reserva_ppp, aporte, modo24, futuro, propria, modo_propria, valorizacao, valor_imovel):
    if valor <= 0 or prazo < 1:
        return []
    saldo = valor
    fim = prazo
    amort_fixa = valor / prazo
    prestacao_fixa = price_pmt(valor, taxa, prazo) if sistema == "PRICE" else 0
    reserva = reserva_ppp
    pot = 0.0
    taxa_val = valorizacao / 100
    rows = []
    mes = 1
    while mes <= fim and saldo > 0.5:
        pot += max(0, aporte)
        juros = saldo * taxa
        if sistema == "SAC":
            amort = min(saldo, amort_fixa)
            prest = amort + juros
        else:
            falta = saldo + juros
            if falta <= prestacao_fixa + 0.01:
                amort = saldo
                prest = falta
            else:
                amort = max(0, prestacao_fixa - juros)
                prest = amort + juros
        fgts_ppp = min(reserva, prest)
        reserva -= fgts_ppp
        saldo = max(0, saldo - amort)
        extra = 0.0
        abate = min(max(0, futuro), max(0, prest - fgts_ppp)) if mes <= 120 else 0

        def reajustar(rest):
            nonlocal amort_fixa, prestacao_fixa
            if rest <= 0 or saldo <= 0.5:
                return
            if sistema == "SAC":
                amort_fixa = saldo / rest
            else:
                prestacao_fixa = price_pmt(saldo, taxa, rest)

        def encurtar(quota):
            nonlocal fim
            if fim - mes <= 0 or saldo <= 0.5:
                return
            if sistema == "SAC":
                need = max(1, int(-(-saldo // max(quota, 0.01))))
                fim = mes + need
            else:
                fim = mes + price_nper(saldo, taxa, prestacao_fixa)

        if propria > 1 and modo_propria != "nenhum" and saldo > 0.5:
            cut = min(propria, saldo)
            saldo = max(0, saldo - cut)
            extra += cut
            if modo_propria == "prestacao":
                reajustar(fim - mes)
            else:
                encurtar(amort_fixa)
        if mes % 24 == 0 and modo24 != "nenhum" and pot > 1 and saldo > 0.5:
            cut = min(pot, saldo)
            saldo = max(0, saldo - cut)
            pot -= cut
            extra += cut
            if modo24 == "prestacao":
                reajustar(fim - mes)
            else:
                encurtar(amort_fixa if sistema == "SAC" else prestacao_fixa)
        rows.append({
            "mes": mes,
            "prestacao": prest,
            "amortizacao": amort,
            "juros": juros,
            "saldo": saldo,
            "fgts_ppp": fgts_ppp,
            "cliente": max(0, prest - fgts_ppp - abate),
            "extra": extra,
            "imovel": valor_imovel * (1 + taxa_val) ** (mes / 12),
        })
        mes += 1
    return rows


def _resumir(rows, valor_fin, ltv, ok):
    primeira = rows[0]["prestacao"] if rows else 0
    ultima = rows[-1]["prestacao"] if rows else 0
    juros = sum(r["juros"] for r in rows)
    return {
        "primeira": primeira,
        "ultima": ultima,
        "juros": juros,
        "total": sum(r["prestacao"] for r in rows),
        "renda_minima": primeira / COMPROMETIMENTO if primeira else 0,
        "cronograma": rows,
        "valor_financiado": valor_fin,
        "ltv": ltv,
        "ok": ok and len(rows) > 0,
        "primeira_cliente": rows[0]["cliente"] if rows else primeira,
        "prazo_meses": len(rows),
        "imovel_fim": rows[-1]["imovel"] if rows else 0,
        "patrimonio_fim": max(0, (rows[-1]["imovel"] if rows else 0) - (rows[-1]["saldo"] if rows else 0)),
    }


def simular(intake: Intake, enq: Enquadramento) -> dict:
    prazo = max(1, int(round(enq.prazo_efetivo_anos * 12)))
    taxa_m = enq.taxa_anual / 100 / 12
    ppp_sac = _reservar_ppp("SAC", enq, intake, taxa_m, prazo)
    ppp_price = _reservar_ppp("PRICE", enq, intake, taxa_m, prazo)
    enq.sac, enq.price = ppp_sac[0], ppp_price[0]
    modo24 = intake.modo_fgts_24 if enq.fgts_elegivel else "nenhum"
    aporte = intake.aporte_mensal_fgts if enq.fgts_elegivel and modo24 != "nenhum" else 0
    propria = intake.amort_propria_mensal if intake.modo_amort_propria != "nenhum" else 0
    valor_imovel = enq.valor_base

    def rows(sistema, cond, reserva):
        if not (cond.cobertura_ok and cond.valor_financiado > 0):
            return []
        return simular_cronograma(
            sistema, cond.valor_financiado, taxa_m, prazo, reserva, aporte, modo24,
            enq.fgts_futuro_mensal, propria, intake.modo_amort_propria,
            intake.valorizacao_anual, valor_imovel,
        )

    sac = _resumir(rows("SAC", enq.sac, ppp_sac[1]), enq.sac.valor_financiado, enq.sac.ltv_max, enq.sac.cobertura_ok)
    price = _resumir(rows("PRICE", enq.price, ppp_price[1]), enq.price.valor_financiado, enq.price.ltv_max, enq.price.cobertura_ok)
    bloqueios = [m for m in enq.mensagens if m.nivel == "bloqueio"]
    enq.pode_simular = len(bloqueios) == 0 and enq.valor_base > 0 and enq.prazo_efetivo_anos >= 1 and (enq.sac.cobertura_ok or enq.price.cobertura_ok)
    return {
        "intake": intake,
        "enq": enq,
        "prazo_meses": prazo,
        "taxa_mensal": taxa_m,
        "sac": sac,
        "price": price,
        "economia_juros": price["juros"] - sac["juros"],
    }


def _month_start(inicio: date, add: int) -> date:
    y = inicio.year + (inicio.month - 1 + add) // 12
    m = (inicio.month - 1 + add) % 12 + 1
    return date(y, m, 1)


def manuais_no_prazo(inicio: date, meses_obra: int) -> list[dict]:
    obra = max(0, int(round(meses_obra)))
    slots = []
    for mes in range(1, obra + 1):
        data = _month_start(inicio, mes)
        if data.month == 12:
            slots.append({"ano": data.year, "mes": mes})
    return slots


def calcular_fluxo(opts: dict) -> dict:
    valor = round2(max(0, opts["valor_unidade"]))
    fin = round2(max(0, opts["financiamento"]))
    fgts = round2(max(0, opts["fgts"]))
    sub = round2(max(0, opts["subsidio"]))
    ato = round2(max(0, opts["ato"]))
    obra = max(0, int(round(opts["meses_obra"])))
    total = max(0, int(round(opts["total_mensais"])))
    caixa = round2(max(0, opts["parcela_caixa"]))
    manuais = [
        {"ano": m["ano"], "mes": m["mes"], "valor": round2(max(0, m["valor"]))}
        for m in opts["manuais"]
    ]
    soma_manuais = round2(sum(m["valor"] for m in manuais))
    fluxo = round2(max(0, valor - fin - fgts - sub))
    pos = total - obra
    alerta = None
    if pos < 0:
        alerta = "O total de parcelas mensais é menor que os meses de obra."
    divisor = total if pos >= 0 else 0
    restante_bruto = round2(fluxo - ato - soma_manuais)
    if restante_bruto < -0.009 and not alerta:
        alerta = "Ato e manuais passam do fluxo de entrada."
    restante = round2(max(0, restante_bruto))
    parcela = round2(restante / divisor) if divisor else 0
    ultima = round2(restante - parcela * (divisor - 1)) if divisor else 0
    npos = max(0, pos)
    por_ano: dict[int, dict] = {}

    def ano(year):
        if year not in por_ano:
            por_ano[year] = {
                "ano": year, "ato": 0, "mensais_obra": 0, "qtd_obra": 0, "manual": 0,
                "pos_chaves": 0, "qtd_pos": 0, "caixa": 0, "qtd_caixa": 0, "total": 0,
            }
        return por_ano[year]

    inicio = opts["inicio"]
    if ato > 0:
        ano(_month_start(inicio, 0).year)["ato"] = ato
    manual_mes = {m["mes"]: m["valor"] for m in manuais}
    for mes in range(1, obra + 1):
        data = _month_start(inicio, mes)
        linha = ano(data.year)
        valor_mes = ultima if mes == divisor else parcela
        linha["qtd_obra"] += 1
        linha["mensais_obra"] = round2(linha["mensais_obra"] + (valor_mes if divisor else 0))
        reforco = manual_mes.get(mes, 0)
        if reforco > 0:
            linha["manual"] = round2(linha["manual"] + reforco)
    for i in range(npos):
        mes = obra + 1 + i
        data = _month_start(inicio, mes)
        linha = ano(data.year)
        indice = obra + i + 1
        valor_mes = ultima if indice == divisor else parcela
        linha["qtd_pos"] += 1
        linha["pos_chaves"] = round2(linha["pos_chaves"] + (valor_mes if divisor else 0))
        if caixa > 0:
            linha["qtd_caixa"] += 1
            linha["caixa"] = round2(linha["caixa"] + caixa)
    anos = []
    for linha in sorted(por_ano.values(), key=lambda r: r["ano"]):
        linha["total"] = round2(linha["ato"] + linha["mensais_obra"] + linha["manual"] + linha["pos_chaves"] + linha["caixa"])
        anos.append(linha)
    return {
        "sistema": opts["sistema"],
        "valor_unidade": valor,
        "financiamento": fin,
        "fgts": fgts,
        "subsidio": sub,
        "fluxo_entrada": fluxo,
        "ato": ato,
        "soma_manuais": soma_manuais,
        "meses_obra": obra,
        "total_mensais": total,
        "meses_pos": pos,
        "restante": restante,
        "parcela_mensal": parcela,
        "parcela_ultima": ultima,
        "parcela_caixa": caixa,
        "parcela_morando": round2(parcela + caixa),
        "manuais": manuais,
        "anos": anos,
        "alerta": alerta,
    }


def montar_fluxo(sim: dict, inicio: date | None = None) -> dict:
    inicio = inicio or date.today()
    intake: Intake = sim["intake"]
    enq: Enquadramento = sim["enq"]
    sistema = intake.fluxo_sistema if intake.fluxo_sistema in ("SAC", "PRICE") else "SAC"
    if sistema == "PRICE" and not enq.price_disponivel:
        sistema = "SAC"
    cond = enq.sac if sistema == "SAC" else enq.price
    resumo = sim["sac"] if sistema == "SAC" else sim["price"]
    slots = manuais_no_prazo(inicio, intake.fluxo_meses_obra)
    manuais = []
    for slot in slots:
        manuais.append({**slot, "valor": float(intake.fluxo_manuais.get(str(slot["ano"]), intake.fluxo_manuais.get(slot["ano"], 0) or 0))})
    return calcular_fluxo({
        "sistema": sistema,
        "valor_unidade": intake.fluxo_valor_unidade if intake.fluxo_valor_unidade is not None else intake.valor_imovel,
        "financiamento": intake.fluxo_financiamento if intake.fluxo_financiamento is not None else cond.valor_financiado,
        "fgts": intake.fluxo_fgts if intake.fluxo_fgts is not None else cond.fgts_usado,
        "subsidio": intake.fluxo_subsidio if intake.fluxo_subsidio is not None else enq.subsidio,
        "ato": intake.fluxo_ato,
        "meses_obra": intake.fluxo_meses_obra,
        "total_mensais": intake.fluxo_total_mensais,
        "manuais": manuais,
        "parcela_caixa": intake.fluxo_parcela_caixa if intake.fluxo_parcela_caixa is not None else resumo["primeira"],
        "inicio": inicio,
    })


def texto_proposta(sim: dict, fluxo: dict) -> str:
    intake: Intake = sim["intake"]
    enq: Enquadramento = sim["enq"]
    nome = intake.client_name.strip() or "cliente"
    linhas = [
        f"Olá, {nome}.",
        "",
        "Segue a simulação do Sistema Geral de Consultoria.",
        "",
        f"{TIPO_LABEL.get(intake.tipo_imovel, intake.tipo_imovel)} {intake.objetivo} em {intake.cidade}/{intake.uf}.",
        f"Valor de venda: {brl(enq.valor_base or intake.valor_imovel)}.",
    ]
    unit = preco_m2(intake.uf, intake.cidade, intake.tipo_imovel)
    if intake.area_m2 > 0 and unit:
        linhas.append(f"Área: {intake.area_m2:g} m² · referência {brl(unit)}/m².")
    linhas += [
        f"Linha: {enq.linha or 'a confirmar'}{f' · faixa {enq.faixa_mcmv}' if enq.faixa_mcmv else ''}.",
        f"Taxa: {pct(enq.taxa_anual)} a.a. · prazo {enq.prazo_efetivo_anos} anos.",
        f"Entrada: {brl(enq.sac.entrada_usada)} · FGTS: {brl(enq.sac.fgts_usado)} · subsídio: {brl(enq.subsidio)}.",
        "",
        "SAC",
        f"Financiado {brl(sim['sac']['valor_financiado'])}.",
        f"1ª parcela {brl(sim['sac']['primeira'])} · última {brl(sim['sac']['ultima'])}.",
        f"Juros totais {brl(sim['sac']['juros'])}.",
    ]
    if enq.price_disponivel and sim["price"]["ok"]:
        linhas += [
            "",
            "PRICE",
            f"Financiado {brl(sim['price']['valor_financiado'])}.",
            f"Parcela {brl(sim['price']['primeira'])}.",
            f"Juros totais {brl(sim['price']['juros'])}.",
        ]
    linhas += [
        "",
        "Fluxo da construtora",
        f"Entrada a diluir: {brl(fluxo['fluxo_entrada'])}.",
        f"Ato {brl(fluxo['ato'])}. Obra: {fluxo['meses_obra']} meses de {brl(fluxo['parcela_mensal'])}.",
        f"Pós-chaves: {fluxo['meses_pos']} meses. Morando: {brl(fluxo['parcela_morando'])} (entrada + Caixa {brl(fluxo['parcela_caixa'])}).",
        "",
        "Simulação prévia, sujeita à análise de crédito e à avaliação da Caixa. Não é carta de crédito.",
        "O PDF foi baixado neste aparelho. Anexe o arquivo nesta conversa.",
    ]
    if intake.consultor_name.strip():
        linhas += ["", intake.consultor_name.strip()]
    if intake.email_gerente.strip():
        linhas += [f"Gerente: {intake.email_gerente.strip()}"]
    linhas.append("Sistema Geral de Consultoria")
    return "\n".join(linhas)


def whatsapp_url(text: str) -> str:
    from urllib.parse import quote
    return "https://wa.me/?text=" + quote(text)


def pdf_bytes(texto: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "Sistema Geral de Consultoria", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", size=11)
    for bloco in texto.split("\n"):
        pdf.multi_cell(0, 6, bloco if bloco else " ", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
