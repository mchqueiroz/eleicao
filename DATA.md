# DATA.md: dicionário de dados

Todas as bases ficam em `data/processed/` (fora do git) e são recriadas pelo `Makefile`.
Os brutos ficam em `data/raw/`, com os hashes em `raw.sha256`. Chaves: `cd_municipio_ibge` (7 dígitos)
e `cd_municipio_tse` (5 dígitos); o de-para vem do diretório da Base dos Dados e confere 100% com a
configuração do TSE de 2026 (`tests/test_painel.py`).

Convenções: **A/B** = 1º e 2º colocados nacionais no 1º turno de cada eleição (posicional, sem nomes).
Percentuais em 0–100, exceto quando o nome diz "parcela" ou "taxa" (0–1). "Risco" lista o que pode
distorcer o uso da variável.

## Eleições

### `painel_presidente.parquet`: município × eleição × turno (2014, 2018, 2022)
Fonte: TSE, `detalhe_votacao_munzona` e `votacao_candidato_munzona` (arquivos `_BR`), sem o exterior (ZZ).

| Variável | Definição | Tratamento | Risco |
|---|---|---|---|
| `aptos` | eleitores aptos | soma de zonas | cadastro inclui falecidos e eleitores que moram em outra cidade |
| `comparecimento`, `abstencoes` | | identidade: comparecimento + abstenções + `aptos_secoes_nao_instaladas` = aptos | 2014: 2 municípios de SE com diferença de 2 eleitores na fonte (exceção nomeada no teste) |
| `validos`, `brancos`, `nulos` | | identidade: válidos + brancos + nulos + `anulados_apuracao_separada` = comparecimento | |
| `votos_A`, `votos_B` | votos nominais dos 1º e 2º colocados nacionais no 1º turno | inclui voto em trânsito, contado onde foi dado | A e B são candidatos diferentes a cada ano |
| `nec` | 1 ÷ Σ(parcela²) dos votos nominais | | no 2º turno vale ≤ 2 por construção |

### `locais_presidente.parquet`: local de votação × eleição × turno
Fonte: TSE, `votacao_secao_<ano>_BR`. Unidade intramunicipal dos eixos 2 e 3: as seções de um mesmo local
são subdivisões quase arbitrárias, e o local aproxima o bairro. Os códigos 95, 96 e 97 (branco, nulo e
anulado em separado) ficam fora de `validos`. A soma dos locais reproduz o painel municipal (teste).
Risco: os locais mudam entre eleições, por isso não há chave longitudinal no nível do local.

### `painel_2026_t1_provisorio.parquet`: 1º turno de 2026, **provisório**
Fonte: sistema de divulgação do TSE (`resultados.tse.jus.br`, eleição 6257), um JSON por município,
com snapshot e SHA256 em `data/raw/tse/2026/divulga/`. `aptos_apurados` = eleitorado das seções já
totalizadas (`c + a = est`); a abstenção usa esse denominador. `pct_totalizado` < 100 indica apuração
parcial. A/B pela posição nacional no snapshot (gravada em `candidatos_2026.parquet`; o 2º turno reusa
esse ranking). Uso: só a previsão. O artigo usa os arquivos finais.

### `candidatos_presidente.parquet`, `candidatos_2026.parquet`
Número, partido e posição no 1º turno, só para auditoria do rótulo A/B. Não entram em saídas públicas.

### `prefeitos.parquet`: continuidade local, 2016–2024 (exploratório, H1)
Fonte: TSE, `votacao_candidato_munzona_<ano>_BRASIL`, cargo prefeito, eleição ordinária, turno decisivo.

| Variável | Definição | Risco |
|---|---|---|
| `linhagem_<ano>` | partido do eleito, harmonizado pelas renomeações e fusões até 2024 (`municipal.SUCESSORA`) | fusões tornam "o mesmo partido" mais amplo do que o partido original |
| `mesmo_partido_<a>_<b>` | mesma linhagem nas duas eleições | |
| `mesma_pessoa_<a>_<b>` | mesmo nome normalizado (o nome não é gravado) | homônimos (raro dentro do município) |
| `margem_<ano>` | (1º − 2º) ÷ válidos no turno decisivo; 1 = candidato único | NaN quando os válidos foram zerados (sub judice) |
| `continuidade_partidaria` | 0, 1 ou 2 continuidades | |

## Censo e território

### `censo2010_municipio.parquet`, `censo2022_municipio.parquet`
Fonte: API SIDRA v3 do IBGE (consultas declaradas em `ibge.CONSULTAS_2010/2022`; respostas em cache em
`data/raw/ibge/sidra/`). Na API, "-" = zero.

| Variável | Definição | 2010 | 2022 | Risco |
|---|---|---|---|---|
| `pct_ate_meio_sm` | % de moradores com renda domiciliar per capita ≤ ½ salário mínimo (inclui sem rendimento) | t3462 | t10296 | salário mínimo de cada ano |
| `pct_superior_25mais` | % com superior completo, 25 anos ou mais | t3547 | t10061 | 2022 é resultado preliminar da amostra |
| `pct_evangelicos`, `pct_catolicos`, `pct_sem_religiao` | % da população (2010) / de 10 anos ou mais (2022) | t137 | t9537 | universo ligeiramente diferente entre os anos |
| `pct_urbana` | % residente em situação urbana | t608 | t10089 | critério urbano/rural mudou em 2022 |
| `pct_pretos_pardos`, `pct_indigenas` | % da população | t9605 | t9605 | |
| `renda_pc_media/mediana`, `pct_renda_outras_fontes`, `anos_estudo_11mais`, `pct_alfabetizados_15mais`, `idade_mediana`, `pct_domicilios_internet` | só 2022: robustez e eixo 4 estendido | – | t10295, t10297, t10062, t10091, t10097, t9936 | sem par em 2010 |
| `imputado_origem` | município instalado em 2013 que herda os valores de 2010 do município de origem | | | aproximação para 5 municípios |

**Indisponível:** Gini municipal de 2022 (as tabelas t10301/t10315 só vão até UF na API) e IDHM municipal 2022.

### `pop_18mais.parquet`
População de 18 anos ou mais = total − Σ idades 0–17 (idade simples: t1552 em 2010, t9514 em 2022).

### `economia_anual.parquet`
PIB municipal a preços correntes (t5938, 2010–2023) e população estimada (t6579). As estimativas faltam
em 2010 e 2022 (anos de censo) e em 2023 (não publicada).

### `acesso_regic.parquet`
`nivel_regic` = hierarquia da REGIC 2018 (1 metrópole … 5 centro local); `dist_km_centro_regional` =
distância geodésica do centroide ao município de nível ≤ 2 mais próximo (0 para metrópoles e capitais
regionais, inclusive integrantes de arranjos). Boa Esperança do Norte herda o nível de Sorriso.
Risco: é distância em linha reta, não por estrada nem até o local de votação.

### `vizinhanca.parquet`, `centroides.parquet`
Grafo queen ∪ 1 vizinho mais próximo (simétrico e conexo; as ilhas ficam ligadas), a partir da malha
municipal 2025 do IBGE, sem as lagoas Mirim e dos Patos. Centroides calculados em SIRGAS 2000 /
Policônica e guardados em lon/lat. AMC: Boa Esperança do Norte + Sorriso + Nova Ubiratã (`espacial.AMC`).

## Economia (exploratório, H1/H3)

### `rais_municipio.parquet`: RAIS de estabelecimentos, 2011–2024
`vinculos_ativos` (estoque em 31/12), `vinculos_publicos` (natureza jurídica 1xxx), `vinculos_agro`
(subclasse CNAE 2.0, divisões 01–03). Há dois layouts de arquivo (até 2023 e 2024), detectados pelo
cabeçalho. Os totais conferem com a RAIS oficial (teste). Risco: só emprego formal; vínculos
contados no município do estabelecimento, não no de residência.

### `bolsa_familia.parquet`
Famílias beneficiárias em outubro de cada ano par e em set/2025 (MI Social/MDS). **Quebra de série:**
`familias_bf_antigo` vai até 2020 e reaparece em 2024; `familias_bf_novo` cobre 2022 (Auxílio Brasil) e
2024, e em 2024 os dois divergem (20,7 contra 17,0 milhões). Variações usam o mesmo campo nas duas pontas.

## Saídas

| Caminho | Conteúdo |
|---|---|
| `data/processed/backtest.csv` | validação da previsão deixando uma eleição de fora |
| `reports/previsao_2T_2026/` | pacote da previsão (CSV, LEIAME, SHA256SUMS; o final entra no git) |
| `data/output/eixos/` | resultados e veredito dos eixos 1–4 (bloqueados até `prereg-v1`) |
| `data/output/exploratorio/` | H1, H3, H7 (exploratório) |
| `data/output/poder/` | poder do desenho com desfechos simulados |
| `reports/mapa/` | mapa público (só métricas que não dependem de lado) |
