# Pipeline: make all  (download → painel, seções, censo, vizinhança → testes)
ANOS := 2014 2018 2022
CDN  := https://cdn.tse.jus.br/estatistica/sead/odsele
BD   := https://storage.googleapis.com/basedosdados-public/one-click-download/br_bd_diretorios_brasil/municipio/municipio.csv.gz
GEO  := https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais
P    := data/processed

MUNZONA := $(foreach a,$(ANOS),data/raw/tse/$(a)/detalhe_votacao_munzona_$(a).zip data/raw/tse/$(a)/votacao_candidato_munzona_$(a).zip)
SECAO   := $(foreach a,$(ANOS),data/raw/tse/$(a)/votacao_secao_$(a)_BR.zip)
DIRETORIO := data/raw/bd/municipio.csv.gz
MALHA   := data/raw/ibge/malha/BR_Municipios_2025.zip
BRUTOS  := $(MUNZONA) $(SECAO) $(DIRETORIO) $(MALHA)

# exploratórias: eleições municipais, RAIS (estabelecimentos) e REGIC
MUNICIPAIS := $(foreach a,2016 2020 2024,data/raw/tse/$(a)/votacao_candidato_munzona_$(a).zip)
RAIS_ANOS  := 2011 2012 2013 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024
RAIS       := $(foreach a,$(RAIS_ANOS),data/raw/rais/$(a)/estab.7z)
REGIC      := data/raw/ibge/regic/REGIC2018_Municipios_Hierarquia_e_regiao.xlsx
EXPLORA    := $(MUNICIPAIS) $(RAIS) $(REGIC)

# apaga o alvo se a receita falhar (evita zip truncado tratado como pronto)
.DELETE_ON_ERROR:
.PHONY: all download checksums verificar test painel secoes censo vizinhanca \
        provisorio2026 previsao eixos bym2 veredito economia prefeitos exploratorio mapa

all: painel secoes censo vizinhanca test

# ---------- brutos (baixa para .part e só renomeia se completar) ----------
download: $(BRUTOS)

$(MUNZONA) $(MUNICIPAIS):
	@mkdir -p $(dir $@)
	curl -sSfL -o $@.part "$(CDN)/$(patsubst %_$(notdir $(patsubst %/,%,$(dir $@))).zip,%,$(notdir $@))/$(notdir $@)" && mv $@.part $@

$(SECAO):
	@mkdir -p $(dir $@)
	curl -sSfL -o $@.part "$(CDN)/votacao_secao/$(notdir $@)" && mv $@.part $@

$(DIRETORIO):
	@mkdir -p $(dir $@)
	curl -sSfL -o $@.part "$(BD)" && mv $@.part $@

$(MALHA):
	@mkdir -p $(dir $@)
	curl -sSfL -o $@.part "$(GEO)/municipio_2025/Brasil/BR_Municipios_2025.zip" && mv $@.part $@

# RAIS: o nome do arquivo de estabelecimentos muda entre anos (Estb2012.7z, ESTB2014.7z, RAIS_ESTAB_PUB.7z)
$(RAIS):
	@mkdir -p $(dir $@)
	f=$$(curl -sS --list-only "ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/$(notdir $(patsubst %/,%,$(dir $@)))/" \
	     | grep -iE '^(estb|rais_estab)' | head -1 | tr -d '\r'); \
	curl -sSf -o $@.part "ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/$(notdir $(patsubst %/,%,$(dir $@)))/$$f" && mv $@.part $@

$(REGIC):
	@mkdir -p $(dir $@)
	curl -sSfL -o $@.part "https://geoftp.ibge.gov.br/organizacao_do_territorio/divisao_regional/regioes_de_influencia_das_cidades/Regioes_de_influencia_das_cidades_2018_Resultados_definitivos/base_tabular/$(notdir $@)" && mv $@.part $@

checksums: $(BRUTOS) $(EXPLORA)
	sha256sum $(BRUTOS) $(EXPLORA) > raw.sha256

verificar:
	sha256sum -c raw.sha256

# ---------- processados (alvos reais: só refazem quando a entrada muda) ----------
$(P)/painel_presidente.parquet: $(MUNZONA) $(DIRETORIO) src/geovoto/tse.py config.toml
	uv run python -m geovoto.tse

$(P)/locais_presidente.parquet: $(SECAO) $(P)/painel_presidente.parquet src/geovoto/secao.py
	uv run python -m geovoto.secao

$(P)/censo2022_municipio.parquet: src/geovoto/ibge.py
	uv run python -m geovoto.ibge

$(P)/vizinhanca.parquet: $(MALHA) src/geovoto/espacial.py
	uv run python -m geovoto.espacial

painel: $(P)/painel_presidente.parquet
secoes: $(P)/locais_presidente.parquet
censo: $(P)/censo2022_municipio.parquet
vizinhanca: $(P)/vizinhanca.parquet

test:
	uv run pytest -q

# ---------- 2026: snapshot provisório (repetir até 100% totalizado) e previsão ----------
provisorio2026:
	uv run python -m geovoto.divulga 1

previsao: painel
	uv run python -m geovoto.previsao

# ---------- análise: o código recusa rodar sem a tag prereg-v1 (ver geovoto.eixos) ----------
eixos: painel secoes censo vizinhanca
	uv run python -m geovoto.eixos

veredito:
	uv run python -m geovoto.veredito

bym2: painel censo vizinhanca
	uv run python -m geovoto.bym2

# ---------- exploratórias (H1, H3, H7) e mapa público ----------
$(P)/rais_municipio.parquet: $(RAIS) $(DIRETORIO) src/geovoto/economia.py
	uv run python -m geovoto.economia

$(P)/prefeitos.parquet: $(MUNICIPAIS) src/geovoto/municipal.py
	uv run python -m geovoto.municipal

economia: $(P)/rais_municipio.parquet
prefeitos: $(P)/prefeitos.parquet

exploratorio: painel censo vizinhanca economia prefeitos $(REGIC)
	uv run python -m geovoto.exploratorio

mapa: painel vizinhanca
	uv run python -m geovoto.mapa
