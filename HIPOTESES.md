# HIPOTESES.md: pré-registro

**Projeto:** *Entre lugares e dentro deles: renda, escolaridade, território e a geografia da divisão eleitoral no Brasil (2014–2026)*
**Versão:** 0.1, **RASCUNHO, AINDA NÃO CONGELADO**
**Rascunho criado em:** 2026-10-04, 22h (horário de Brasília)

> Congelamento: commit + tag `prereg-v1` + carimbo de tempo externo (release no GitHub + DOI no Zenodo, ou OSF).
> Depois do congelamento, qualquer mudança vira uma nova versão com seção "Desvios" justificando.

---

## 0. Declaração de transparência (preencher antes de congelar)

- Este documento foi redigido **depois** do início da divulgação dos resultados provisórios do 1º turno de 2026 (04/10/2026, a partir das 17h).
- O autor viu: [PREENCHER: nada / resultado nacional / resultados por UF / mapas por município / pesquisas de opinião].
- Nenhuma análise com dados municipais de 2026 foi feita antes deste documento.
- Os dados de 2014, 2018 e 2022 já foram baixados e agregados por município (contagens apenas, sem nenhum modelo dos eixos abaixo).
- Antes do congelamento, rodaram sobre 2014–2022 apenas as análises **exploratórias** de §7 (H1, H3, H7; ver `data/output/exploratorio/relatorio.md`) e um mapa público de métricas descritivas (|margem|, abstenção, NEC). Os eixos 1 a 4 só foram executados em dados com desfechos embaralhados, para testar o código.
- Consequência: para o **1º turno de 2026**, os testes têm caráter confirmatório **atenuado**. Para o **2º turno de 2026** e para a previsão (§6), o pré-registro é integral.

## 1. Definições comuns

- **Unidade:** município. 5.570 em 2014–2022 e 5.571 em 2026. Para comparações no tempo, Boa Esperança do Norte (MT) é agregado com Sorriso e Nova Ubiratã numa área mínima comparável (AMC). O exterior (UF = ZZ) fica fora.
- **Blocos A/B:** A = 1º colocado nacional no 1º turno; B = 2º colocado. A definição é posicional, sem nomes nem partidos. Toda estimativa com sinal é reportada para A e para B.
- **Desfechos:** (i) participação de A e de B nos votos válidos do 1º turno; (ii) comparecimento / aptos; (iii) |margem| = |s_A − s_B|; (iv) alienação = (abstenção + brancos + nulos) / aptos. O 2º turno é usado como robustez.
- **Estrutura** (5 dimensões com definição idêntica nos Censos 2010 e 2022): econômica (% moradores com renda pc ≤ ½ SM), educacional (% superior completo, 25+), religiosa (% evangélicos, católicos, sem religião), demográfica (% urbana, log aptos), cor/raça (% pretos+pardos, % indígenas). Censo 2010 para 2014 e 2018; Censo 2022 para 2022 e 2026. Os 5 municípios instalados em 2013 herdam os valores de 2010 do município de origem (marcados). Variáveis só de 2022 (renda média, internet, idade mediana etc.) entram apenas como robustez.
- **Vizinhança:** na decomposição, filtro espacial de autovetores (MESF) do grafo queen ∪ kNN(1): autovetores com I de Moran ≥ 0,75·λmax (217 vetores). Sensibilidade com 0,5 (640) e 0,25 (1.258). O limiar foi fixado antes de qualquer resultado, porque 0,25 daria 23% de n em regressores. BYM2 é usado como robustez e para inferir coeficientes.
- **Território:** efeito de UF.
- **Decomposição (principal):** Shapley do R² ajustado de MQO ponderado por aptos sobre logit(s) (2³ submodelos), com média, amplitude entre as 3! ordens, efeitos únicos e parcela compartilhada. Os ICs vêm de bootstrap de municípios estratificado por UF (200 réplicas, seed fixa).
- **Modelo bayesiano (robustez):** BYM2 Binomial com ligação logit sobre contagens. Prioris fracamente informativas. Convergência exigida: R̂ < 1,01, ESS > 400, sem divergências.
- **Inferência:** decisões por intervalo de credibilidade de 90% e ROPE (|β padronizado| < 0,05), não por valor-p. Famílias de testes múltiplos (LISA, inclinações regionais) com Benjamini-Hochberg a 10%.

## 2. Eixo 1: O que explica o mapa

- **T1, Estruturação:** a parcela de Shapley da estrutura aumenta entre 2014 e 2026, e a do território diminui.
  - *Suportada se* a tendência linear da parcela estrutural (4 pontos) ≥ +5 p.p. no período, com IC90% > 0.
  - *Refutada se* o IC90% da tendência incluir 0 ou for negativo.
- **T2, Território persistente:** entre pares de municípios contíguos separados por divisa estadual, a diferença em s_A, condicionada à estrutura, é ≥ 3 p.p. em 2026 e não cai significativamente desde 2014.
  - *Modelo:* efeito fixo do par, o salto da UF como parâmetro e balanceamento de covariáveis reportado.
  - *Medida:* salto médio |γ_a − γ_b| nas divisas reais **menos** o mesmo salto em fronteiras-placebo (cada UF partida na mediana da longitude dos centroides). O placebo remove o viés de |·| e o efeito de qualquer linha arbitrária.
  - *Refutada se* (real − placebo) tiver IC90% dentro de [−3, 3] p.p.
- T1 e T2 não são mutuamente exclusivas. Os quatro resultados possíveis são reportados.

## 3. Eixo 2: Onde está a divisão

- Decomposição multinível de logit(A/(A+B)) em UF → município → **local de votação** (agregado de `votacao_secao`; o local aproxima o bairro, e as seções de um mesmo local são subdivisões arbitrárias), por eleição. Estimador de momentos ponderado, com correção para poucos locais por município e para o ruído binomial (validado em simulação: `tests/test_metricas.py`).
- **Entre-lugares:** a parcela UF + município cresce ≥ 5 p.p. entre 2014 e 2026 (IC90% > 0).
- **Dentro-dos-lugares:** a parcela da seção cresce ≥ 5 p.p. (IC90% > 0).
- Caso contrário, "estável".

## 4. Eixo 3: Quem convive com quem

- Isolamento_X = Σᵢ (xᵢ/X)·(xᵢ/tᵢ) e exposição_X→Y = Σᵢ (xᵢ/X)·(yᵢ/tᵢ), para X, Y ∈ {A, B}, nas escalas município e local de votação.
- **Separação:** o isolamento sobe ≥ 0,05 entre 2014 e 2026 **para os dois blocos**.
- **Estabilidade:** a variação fica em [−0,05, 0,05] para os dois.
- Mudanças assimétricas são reportadas numericamente, sem qualificação.

## 5. Eixo 4: Qual diferença divide

- Shapley dentro do bloco estrutural entre as 5 dimensões de §1, nas 4 eleições. Os efeitos únicos e a parcela compartilhada são reportados separadamente.
- **T4-renda:** a dimensão econômica tem a maior parcela única nas 4 eleições.
- **T4-deslocamento:** a parcela única de outra dimensão (educacional ou religiosa) cresce ≥ 5 p.p. e supera a econômica em 2022 ou 2026.
- **Heterogeneidade regional** (ex-H4): inclinações aleatórias por região. "Paradoxo de Simpson" exige inversão de sinal com probabilidade posterior > 0,9 em pelo menos uma região.

## 6. Previsão do 2º turno de 2026 (apenas se houver 2º turno presidencial)

- **Alvos por município:** abstenção no 2º turno e |margem| no 2º turno, com IC80 e IC95. Sem sinal e sem nomes.
- **Baseline pré-registrado:** abstenção_2T = abstenção_1T + Δ médio histórico da UF; |margem| por *swing* uniforme a partir do 1º turno, com transferências proporcionais.
- **Modelo (`geovoto.previsao`):** os votos dos demais candidatos (O) vão para A com fração π: s_A2 = (A1 + π·O1)/(A1 + B1 + O1). π nacional segue a preditiva t (n−1 g.l.) das eleições de calibração (2014, 2018, 2022), com escala mínima de 0,10. O ruído municipal em logit tem variância τ² + κ²·o1² + ν/aptos. Abstenção: logit(ab2) = logit(ab1) + c + δ_mun + ε, com c nacional pela preditiva t (escala mínima de 0,05) e δ_mun = média histórica do município encolhida para a da UF (Bayes empírico). São 2.000 simulações (seed fixa). Na apuração parcial, a abstenção do 1º turno usa o eleitorado das seções já totalizadas.
- **Validação já feita (deixando uma eleição de fora):** o modelo vence o baseline na margem nas 3 eleições e na abstenção em 2 de 3 (perde em 2014 por 0,05 p.p.). Os intervalos saíram conservadores (cobertura de 80% entre 0,89 e 0,99), porque com 2 eleições de treino a t tem 1 g.l.
- **Avaliação:** MAE ponderado por aptos, CRPS e cobertura dos ICs, comparados ao baseline.
- **Publicação:** até 22/10/2026 (máximo 24/10). Avaliação publicada qualquer que seja o resultado.

## 7. Exploratórias (sem critério confirmatório)

Voto econômico por papel (ex-H3), continuidade do grupo local (ex-H1), alienação e cadastro (ex-H7, artigo separado), desertos de notícia e fatia de municípios que oscilam (Pedersen entre blocos).

## 8. Limitações declaradas

Falácia ecológica (as afirmações valem para lugares, não para eleitores); MAUP (escalas município, microrregião e seção); confusão espacial (a "vizinhança" é dependência residual, não contágio); cadastro desatualizado (abstenção); defasagem das covariáveis censitárias.

## Desvios

(nenhum até o momento)
