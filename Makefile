# Pipeline: make all  (download → painel → test)
ANOS := 2014 2018 2022
CDN  := https://cdn.tse.jus.br/estatistica/sead/odsele
BD   := https://storage.googleapis.com/basedosdados-public/one-click-download/br_bd_diretorios_brasil/municipio/municipio.csv.gz
TSE_ZIPS := $(foreach a,$(ANOS),data/raw/tse/$(a)/detalhe_votacao_munzona_$(a).zip data/raw/tse/$(a)/votacao_candidato_munzona_$(a).zip)

.PHONY: all download painel test checksums verificar
all: painel test

MALHA := data/raw/ibge/malha/BR_Municipios_2025.zip

download: $(TSE_ZIPS) data/raw/bd/municipio.csv.gz $(MALHA)

$(MALHA):
	@mkdir -p $(dir $@)
	curl -sSfL -o $@ "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/Brasil/BR_Municipios_2025.zip"

data/raw/tse/%.zip:
	@mkdir -p $(dir $@)
	curl -sSfL -o $@ "$(CDN)/$(patsubst %_$(notdir $(patsubst %/,%,$(dir $@))).zip,%,$(notdir $@))/$(notdir $@)"

data/raw/bd/municipio.csv.gz:
	@mkdir -p $(dir $@)
	curl -sSfL -o $@ "$(BD)"

# grava os hashes dos brutos baixados (rodar uma vez; versionar raw.sha256)
checksums: download
	sha256sum $(TSE_ZIPS) data/raw/bd/municipio.csv.gz $(MALHA) > raw.sha256

verificar:
	sha256sum -c raw.sha256

data/processed/painel_presidente.parquet: download src/geovoto/tse.py config.toml
	uv run python -m geovoto.tse

painel: data/processed/painel_presidente.parquet

test: painel
	uv run pytest -q

# 2026: snapshot provisório do 1º turno (repetir até 100% totalizado) e previsão do 2º turno
.PHONY: provisorio2026 previsao
provisorio2026:
	uv run python -m geovoto.divulga 1

previsao: painel
	uv run python -m geovoto.previsao

.PHONY: censo
censo:
	uv run python -m geovoto.ibge

.PHONY: vizinhanca
vizinhanca:
	uv run python -m geovoto.espacial

.PHONY: secoes
secoes: painel
	uv run python -m geovoto.secao
