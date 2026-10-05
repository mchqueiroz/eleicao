# Longe do centro, fora da urna? Distância, renda e cadastro na alienação eleitoral municipal (2014–2022)

**Rascunho v0.1, 2026-10-05.** Resultados **exploratórios** (H7 em `HIPOTESES.md` §7), sem critério
confirmatório. Números gerados por `make exploratorio` (`data/output/exploratorio/`).

## Pergunta

Em que municípios uma parcela maior do eleitorado não escolhe nenhum candidato a presidente (abstenção,
voto branco ou nulo)? A pergunta é sobre lugares e sobre o funcionamento do cadastro, não sobre a motivação
de eleitores individuais.

## Dados

- **Desfecho:** alienação no 1º turno = (abstenções + brancos + nulos) ÷ aptos, por município (TSE, 2014, 2018 e 2022).
- **Acesso:** distância geodésica do centroide do município ao município mais próximo classificado como
  metrópole ou capital regional na REGIC 2018 (IBGE), e o nível hierárquico do próprio município (1 a 5).
- **Cadastro:** razão entre eleitores aptos e adultos residentes. Adultos = população estimada do ano ×
  fração de 18 anos ou mais no censo mais próximo (Censo 2022 direto para 2022).
- **Estrutura:** % de moradores com renda per capita de até ½ salário mínimo, % com ensino superior (25+),
  religião, urbanização, cor/raça e tamanho do eleitorado (Censos 2010 e 2022).

## Método

Mínimos quadrados ponderados pelo número de aptos, com o logit da alienação como desfecho, efeito fixo de UF
e erro-padrão agrupado por UF. Os regressores são padronizados: cada coeficiente é a mudança no logit associada
a um desvio-padrão do regressor. Os intervalos são de 90%.

## Resultados

| Regressor (1 desvio-padrão) | 2014 | 2018 | 2022 |
|---|---|---|---|
| log(distância ao centro regional) | +0,054 [+0,034; +0,075] | +0,050 [+0,034; +0,066] | +0,052 [+0,038; +0,066] |
| Nível REGIC (5 = centro local) | +0,013 [−0,008; +0,034] | +0,018 [+0,001; +0,036] | +0,019 [+0,007; +0,032] |
| Razão aptos/adultos | +0,061 [+0,032; +0,090] | +0,057 [+0,032; +0,081] | +0,029 [+0,012; +0,046] |
| % com ensino superior | −0,015 [−0,037; +0,007] | −0,011 [−0,026; +0,004] | +0,000 [−0,016; +0,017] |
| % com renda pc ≤ ½ SM | +0,150 [+0,087; +0,214] | +0,099 [+0,022; +0,175] | +0,104 [+0,036; +0,172] |

| | 2014 | 2018 | 2022 |
|---|---|---|---|
| Alienação nacional | 27,1% | 27,2% | 24,3% |
| Municípios com mais aptos do que adultos | 4.417 | 4.349 | 4.376 |
| Razão aptos/adultos (mediana municipal) | 1,10 | 1,11 | 1,10 |

Três padrões se repetem nas três eleições:

1. **Distância.** Quanto mais longe de uma metrópole ou capital regional, maior a alienação, com magnitude
   praticamente igual nos três anos e controlando renda, escolaridade e UF.
2. **Renda.** A proporção de moradores de baixa renda tem a associação mais forte entre os regressores.
   Depois de controlar renda e os demais fatores, a escolaridade deixa de ter associação distinguível de zero.
3. **Cadastro.** Em cerca de 4.400 dos 5.570 municípios há mais eleitores aptos do que adultos residentes.
   Onde essa razão é maior, a alienação também é maior. O efeito caiu à metade em 2022, ano seguinte ao
   Censo e com o denominador mais preciso.

## Leitura cautelosa

A razão aptos/adultos acima de 1 não prova, sozinha, cadastro desatualizado. Ela soma pelo menos três coisas:
eleitores de 16 e 17 anos (voto facultativo), pessoas que vivem em outra cidade e mantêm o título na cidade
de origem, e registros de falecidos ainda não cancelados. As duas últimas inflam a abstenção medida sem que
haja um eleitor residente deixando de votar. Uma parte da "alienação" municipal pode, portanto, ser artefato
do cadastro, sobretudo em municípios pequenos e com emigração.

A distância à capital regional pode refletir custo de deslocamento até o local de votação, menor oferta de
informação local ou composição populacional não capturada pelos controles. Este desenho não separa essas
explicações.

## Limitações

- Análise ecológica: descreve municípios, não eleitores.
- Denominador de adultos aproximado fora dos anos de censo.
- A distância é medida de centroide a centroide, não por rede viária nem até o local de votação.
- Resultados exploratórios, obtidos antes do congelamento do pré-registro do projeto principal.

## Próximos passos

1. Pré-registrar uma versão confirmatória para 2026 (direção esperada: distância +, renda baixa +, razão
   aptos/adultos +), avaliada com os arquivos finais do TSE.
2. Decompor a razão aptos/adultos: separar 16–17 anos (perfil do eleitorado do TSE por idade) e
   transferências de domicílio eleitoral.
3. Verificar sensibilidade à distância por rede viária numa amostra de UFs.
