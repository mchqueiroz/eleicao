# PLAN.md: Geografia do voto no Brasil, 2014–2026

**Versão:** 0.1 (rascunho para revisão) · **Data:** 2026-10-04 (dia do 1º turno) · **Status:** só planejamento, nada implementado

---

## Estado atual (2026-10-05)

| Parte | Situação |
|---|---|
| Dados 2014–2022 (município, local de votação, Censos 2010/2022, malha, REGIC, RAIS, Bolsa Família, prefeitos) | prontos, com testes de consistência e conferência externa (`DATA.md`) |
| 1º turno 2026 provisório | coletado com 100% apurado (snapshot 05/10 12:53) |
| Previsão do 2º turno | pacote congelado em `reports/previsao_2T_2026/`, publicado na release `prereg-v1` |
| Eixos 1–4, robustez e veredito automático | pré-registro congelado (tag `prereg-v1`); `make eixos veredito bym2` liberado |
| Poder do desenho | rodado em 05/10 (`data/output/poder/poder.md`). T1: refutada com Δ ≤ 2 p.p., suportada com Δ ≥ 11 p.p., dividida entre 3 e 7 p.p. T2: a medida antiga subestimava o salto e foi corrigida; agora um salto de 3 p.p. sai suportado em 30–50% (limiar) e um de 5 p.p. em 80–95% |
| Exploratórias H1, H3, H7 | rodadas (`data/output/exploratorio/`); rascunho do artigo curto em `reports/` |
| Mapa público | publicado como artefato privado |
| Histórico do GitHub | reescrito em 05/10 sem dados (backup em `../backup-eleicao-antes-reescrita-2026-10-05.bundle`) |

---

## 0. Antes de tudo: o que encontrei no repositório

Leia isto antes do resto, porque muda a ordem de prioridade.

1. **Os resultados que já existem vêm de dados sintéticos.**
   - `notebooks/gerar_dados_reais.py` gera `idhm ~ Beta`, `coronelismo_idx ~ Uniform(0,1)` e `pedersen = 35 − 8·coronelismo + …` com ruído, e grava tudo em `data/processed/eleitoral/pedersen.parquet` e `data/processed/historico/coronelismo_proxy.parquet`.
   - `notebooks/02_03_testes_avancados.py` gera `var_renda_real`, `taxa_desemprego`, `voto_vizinhanca_lag` e `voto_incumbente` com `np.random` e já embute os coeficientes.
   - Esses arquivos alimentam `final_model_data.parquet`, `03_modelo_bayesian*.py`, `04_modelo_hierarquico_pymc.py`, `h1_coeficientes.csv`, `pymc_summary.csv` e os mapas de "coronelismo". **Nenhum desses resultados é evidência.** Eles só recuperam os coeficientes que foram colocados no gerador.
   - O commit `96b9a72` descreve a integração como "TSE+IBGE+Coronelismo (5570 municípios)", e os parquets sintéticos estão versionados e enviados para `github.com/mchqueiroz/eleicao`. Se esse repositório for público, isso é um risco de reputação. Ação: colocar em quarentena, apagar e reescrever o histórico (ver Pergunta 1).
2. **O único dado real é a parte do TSE**: `detalhe_votacao_munzona_2022` (comparecimento, abstenção, brancos e nulos por município e zona) e `ibge_populacao.parquet`. Não existe arquivo com **votos por candidato** (`votacao_candidato_munzona`). Por isso nenhuma variável de escolha de voto foi construída.
3. `03_modelo_bayesian.py` modela `PCT_VOTOS_VALIDOS` (válidos/comparecimento ≈ 96%), que é uma variável de *alienação*, não de escolha. Além disso, usa uma Normal sobre porcentagens sem pesos.
4. Problemas de higiene: dados brutos e parquets no git (372 MB), cópia duplicada de `detalhe_votacao_munzona_2022/` fora do repo, `venv/` de 1,1 GB com Python 3.14, chave TSE↔IBGE vinda de um CSV de terceiros (`beta-git/tse-ibge`) sem teste, painel com 5.751 linhas (inclui os "municípios" do exterior, `SG_UF = ZZ`) e o diretório pai `~/` também é um repositório git.

**Conclusão:** daqui só aproveito a estrutura de pastas e a lista de dependências. Recomendo começar uma pipeline nova (Fase 0) e manter o código antigo em `legacy/` apenas como referência, ou apagá-lo.

---

## 1. O relógio: hoje é 04/10/2026

| Data | Evento | Consequência para o plano |
|---|---|---|
| **04/10 (hoje), ~17h** | Começa a divulgação dos resultados provisórios do 1º turno | O pré-registro "antes dos dados de 2026" **só é limpo se for congelado hoje, antes das 17h**. Depois disso, ele precisa declarar que os resultados provisórios já foram vistos. |
| 05–24/10 | Janela da previsão do 2º turno | Só há 3 semanas, e só vale se houver 2º turno presidencial (ou de governador) |
| 25/10 | 2º turno | Prazo final para a previsão estar publicada (meta: até 22/10) |
| nov/26 em diante | Arquivos finais do TSE no portal de dados abertos | Toda análise de 2026 é refeita sobre os arquivos finais. A versão provisória fica só para a previsão. |

Por isso divido o projeto em duas trilhas:

- **Trilha A (crítica no tempo, 3 semanas):** pré-registro, ingestão mínima e previsão neutra do 2º turno, que depois é avaliada.
- **Trilha B (o artigo, cerca de 4 a 6 meses):** fases 1 a 5 com a pergunta central e H1 a H4.

A Trilha A é o que mais corre risco de não acontecer. Se faltar tempo, ela tem prioridade sobre tudo da Trilha B.

---

## 1b. Título, teses e estrutura (versão 0.2)

**Título de trabalho:** *Entre lugares e dentro deles: estrutura, território e a geografia da divisão eleitoral no Brasil (2014–2026)*

**Pergunta-mãe:** a divisão eleitoral brasileira é uma divisão **de lugares** (território, fronteira, vizinhança) ou **de perfis** (estrutura social), e ela se concentra **entre** municípios ou **dentro** deles?

**Desfecho principal (todas as eleições):** a participação de cada um dos dois mais votados do 1º turno (A/B por posição, os dois sinais), além de comparecimento e |margem|. Esse desfecho existe nos 4 anos com ou sem 2º turno. O 2º turno entra como robustez.

Regra: as teses abaixo são **rivais e pré-registradas**. O trabalho não parte de uma conclusão. Cada eixo tem critérios de decisão fixados antes dos dados finais de 2026.

| Eixo | Tese rival A | Tese rival B | Evidência | Critério de decisão (rascunho) |
|---|---|---|---|---|
| **1. O que explica o mapa** | **T1, Estruturação:** a parcela explicada pela estrutura cresceu e a do território caiu entre 2014 e 2026 | **T2, Território persistente:** municípios estruturalmente parecidos votam diferente conforme a UF, e esse salto não diminuiu | Decomposição de Shapley (estrutura / vizinhança / UF) para as 4 eleições, com o mesmo método; pares de municípios de fronteira entre UFs com efeito fixo do par | T1: tendência da parcela estrutural ≥ +5 p.p. com IC90% > 0. T2: salto médio na fronteira ≥ 3 p.p. em 2026 e sem queda significativa desde 2014. **As duas podem vencer ou perder**, e os quatro resultados são reportados |
| **2. Onde está a divisão** | **P1-entre:** a variância migrou para os níveis entre UF e entre municípios | **P1-dentro:** a variância está e permanece dentro dos municípios (entre seções) | Decomposição de variância UF → município → seção (`votacao_secao`), 4 eleições | Vence o lado cuja parcela variar ≥ 5 p.p. com IC90% que exclua 0; caso contrário, "estável" |
| **3. Quem convive com quem** | **P2-separação:** o isolamento local de cada bloco cresceu | **P2-estabilidade:** a exposição ao outro lado não mudou | Índices de isolamento e de exposição por município e por seção, **calculados para A e B** | Separação se o isolamento sobe ≥ 0,05 para os dois blocos; mudanças assimétricas reportadas sem adjetivo |

| **4. Qual diferença divide** | **T4-renda:** a diferença econômica é a que mais separa o voto dos municípios, e isso se manteve desde 2014 | **T4-deslocamento:** o peso migrou da renda para a escolaridade e/ou a religião | Decomposição de Shapley **dentro** do bloco estrutural, por dimensão, nas 4 eleições; efeitos únicos e compartilhados; inclinações por região | T4-renda: a dimensão econômica tem a maior parcela nos 4 anos. Deslocamento: a parcela de outra dimensão cresce ≥ 5 p.p. e passa a da renda em 2022 ou 2026 |

**Dimensões estruturais (eixo 4).** O bloco "estrutura" deixa de ser um número único:

| Dimensão | Variáveis | Fonte (2010 / 2022) |
|---|---|---|
| Econômica | renda per capita, % até ½ SM (comparável 2010–2022), % renda de outras fontes (Gini municipal 2022 indisponível na API), formalidade, emprego público, emprego agro, PIB per capita | Censo, RAIS, MDS, IBGE |
| Educacional | anos de estudo 25+, % ensino superior, analfabetismo 15+, IDEB | Censo, INEP |
| Religiosa | % evangélicos, % católicos, % sem religião | Censo |
| Demográfica | idade mediana, % 60+, urbanização, densidade, log do eleitorado | Censo, TSE |
| Cor/raça | % pretos e pardos, % indígenas | Censo |
| Acesso | distância ao centro REGIC, banda larga, saneamento | REGIC, Anatel, Censo |
| Saúde e segurança | mortalidade infantil (longevidade), homicídios | SIM/SINASC |

Cuidados: renda e escolaridade têm correlação próxima de 0,8 entre municípios, então a parcela **compartilhada** é reportada separadamente e não é atribuída a nenhuma das duas. Afirmações valem para **lugares**, nunca para eleitores ("municípios com mais ensino superior", não "eleitores com diploma"). Linguagem: "diferença educacional", nunca "intelectual".

**Capítulos de apoio:** P3 alinhamento social vira o eixo 4 e absorve H4, o paradoxo de Simpson e os componentes do IDH; P4 fatia de municípios que oscilam (Pedersen entre blocos); H2 vira métrica-base do eixo 1 (dependência residual).

**Fora do núcleo:** H3 (voto econômico) e H1 (grupo local) ficam como exploratórias ou apêndice; H5 é substituída por P1 e P2, que medem separação melhor que o landslide; H6 é absorvida pelo eixo 1; H7 e o problema do cadastro viram um **artigo curto separado**.

**Produtos:**
1. Artigo principal (eixos 1 a 3).
2. Nota técnica com a previsão pré-registrada do 2º turno e sua avaliação.
3. Artigo curto sobre alienação e cadastro.
4. Base harmonizada e código abertos.
5. Opcional: mapa público com as métricas simétricas.

---

## 2. Críticas ao desenho (antes das hipóteses)

1. **A partição Estrutura / Vizinhança / Território não é identificada de forma única.** A estrutura socioeconômica já é espacialmente autocorrelacionada, e o UF é colinear com ela e com o espaço. Logo, a parte atribuída a cada componente depende da ordem em que entram no modelo (*spatial confounding*: um efeito ICAR absorve covariáveis espacialmente suaves). **Mitigação:** reportar uma decomposição de Shapley do R² bayesiano, que é a média sobre todas as 3! ordens, junto com o **intervalo** (mínimo e máximo entre as ordens), e não um número único. O componente "único" de cada bloco funciona como limite inferior.
2. **"Vizinhança" aqui é dependência espacial descritiva, não *spillover* causal.** Num corte transversal, o ρ do SAR não separa contágio de confusão por variável omitida espacialmente suave (Gibbons & Overman, 2012). O texto deve dizer "dependência espacial residual", nunca "efeito de vizinhança".
3. **H2 é praticamente certa.** Com n ≈ 5.570, o I de Moran sempre será significativo. Ela só se torna informativa se medida por **tamanho de efeito**: a razão I_resíduo / I_bruto e o correlograma (a distância em que I cai abaixo de 0,1).
4. **Valores-p com n = 5.570 são quase inúteis.** Os critérios de falsificação usam tamanho de efeito com ROPE (região de equivalência prática), e não p < 0,05.
5. **O "bloco incumbente" degenera em 2018.** O partido do presidente em exercício teve votação marginal, sem candidato competitivo. Decisão proposta: H3 usa 2014, 2022 e 2026, e 2018 entra só como robustez. O lado bom: o papel de incumbente troca de lado entre 2014, 2022 e 2026, o que ajuda a separar voto econômico de partidarismo fixo num painel de variações com efeito fixo de município.
6. **H1 é a hipótese mais cara e a mais fraca em identificação.** Exige codificar coligações de 27 UFs × 4 eleições, além de casar sobrenomes. A continuidade do grupo local e a estabilidade do voto têm causa comum (preferências estáveis). É associação, não persistência causal. Proponho uma versão reduzida (§6).
7. **Faltam dados intercensitários.** As covariáveis de 2014 e 2018 vêm do Censo 2010, e as de 2022 e 2026 do Censo 2022. Variações entre censos misturam mudança real com mudança de questionário. Para H3, só séries anuais (RAIS, Bolsa Família, PIB municipal), nunca o censo.
8. **Cadastro desatualizado infla a abstenção.** Eleitores falecidos ou que migraram continuam aptos até a revisão do cadastro. A abstenção entre anos e entre municípios fica contaminada, o que afeta H7 e a previsão. Controle: razão aptos / população 18+ (Censo) como covariável.
9. **Porcentagens não são dados gaussianos.** Use contagens com verossimilhança Binomial ou Beta-Binomial (ou logit com pesos). Os municípios vão de cerca de 1 mil a cerca de 9 milhões de eleitores, e modelar sem pesos dá a Borá o mesmo peso de São Paulo.
10. **Não precisa construir um IDH próprio.** H4 já pede para decompor o IDH. Basta usar os três componentes diretamente e dispensar o índice composto. Isso economiza trabalho e remove um passo arbitrário de agregação. O índice "não oficial" só seria necessário para um mapa, e é opcional.

---

## 3. Hipóteses (rascunho para HIPOTESES.md)

Convenções:
- **Unidade:** município (5.570 até 2022; 5.571 em 2026, ver §5.2). DF e Fernando de Noronha entram, exterior (ZZ) sai.
- **Blocos:** A/B no 2º turno, ou os dois mais votados no 1º turno. "Incumbente" é o candidato do partido do presidente em exercício ou da sua coligação formal (registro de candidatura no TSE). Toda variável com lado é reportada nos dois sinais.
- **Desfecho principal da pergunta central:** logit da participação do bloco incumbente no 2º turno (ou nos dois primeiros do 1º turno), comparecimento e |margem|. As três decomposições são reportadas.
- **ROPE padrão:** efeitos padronizados |β| < 0,05 contam como "nulo prático".

### H1: Persistência do grupo local (núcleo reduzido)
- **Enunciado:** municípios com maior continuidade do grupo que governa a prefeitura (2016→2020→2024) apresentam (i) menor volatilidade entre eleições presidenciais e (ii) maior divergência entre o voto do bloco para presidente e para governador.
- **Variáveis X:** reeleição do prefeito ou do mesmo partido (0, 1 ou 2 continuidades), margem do prefeito em 2024, vínculos públicos municipais / população ocupada (RAIS).
- **Y:** (i) Pedersen entre eleições presidenciais consecutivas; (ii) |share_pres(bloco) − share_gov(bloco alinhado)|, com o alinhamento pela regra de coligação formal.
- **Modelo:** Beta (ou logit-normal) multinível com UF aleatório, BYM2 e controles estruturais.
- **Falsificação:** o IC 90% de β_continuidade fica dentro do ROPE ou tem sinal oposto em (i) **e** (ii).
- **Limitação declarada:** associação, não persistência causal. O voto dividido é ecológico e não identifica eleitores que dividiram o voto.

### H2: Autocorrelação espacial
- **Enunciado:** o voto tem I de Moran global > 0,3 (k = 6 e queen), e os resíduos do modelo estrutural + UF mantêm I_res / I_bruto > 0,25.
- **Falsificação:** I_res / I_bruto < 0,1 nas duas matrizes de vizinhança, ou seja, estrutura + UF explicam quase toda a dependência.
- **Entregas:** correlograma por faixa de distância e LISA com correção de FDR.

### H3: Voto econômico (bloco incumbente por papel)
- **Enunciado:** Δ(logit share incumbente)ₜ − Δₜ₋₁ cresce com a melhora relativa local da massa salarial formal, do emprego formal e das transferências per capita nos 2 anos antes da eleição.
- **Modelo:** painel de primeiras diferenças, eleições 2014, 2022 e 2026, com efeito fixo de eleição × UF (absorve choques nacionais e estaduais) e erro espacial (BYM2 nas diferenças).
- **Falsificação:** o IC 90% de β_renda e β_emprego cai dentro do ROPE em ≥ 2 das 3 eleições, ou o sinal se inverte entre eleições.
- **Riscos:** quebra do CAGED em 2020 (usar só RAIS); expansões de transferências são endógenas à pobreza (controlar o nível e não só a variação).

### H4: Clivagem de desenvolvimento heterogênea por região
- **Enunciado:** a inclinação do voto em relação a (a) educação, (b) renda e (c) longevidade varia entre regiões. O desvio-padrão entre regiões de cada inclinação é > 0,5 × |média nacional|, e há inversão de sinal em pelo menos uma região (paradoxo de Simpson geográfico).
- **Modelo:** inclinações aleatórias por região (e por UF como robustez), componentes entrando separadamente e juntos, com VIF reportado e versão PCA.
- **Falsificação:** σ_inclinação < 0,25 × |μ| para os três componentes e nenhuma inversão de sinal com probabilidade posterior > 0,9.

### Exploratórias (rotuladas, sem critério confirmatório)
- **H5 Ordenamento:** índice de landslide (cortes 15/20/30 p.p., ponderado por eleitores) e teste de dip de Hartigan, 2014→2026. Armadilha: a composição muda entre turnos e entre anos.
- **H6 Nacionalização:** decomposição de variância do *swing* municipal em componentes nacional, de UF e de município (Stokes / Kawato).
- **H7 Alienação:** (abstenção + brancos + nulos) ~ distância geodésica ao centro REGIC ≥ Capital Regional + escolaridade + renda + aptos/população 18+.

---

## 4. Dicionário de métricas (fórmula e armadilha)

| Métrica | Fórmula | Armadilha | Decisão |
|---|---|---|---|
| I de Moran global | I = (n/W)·Σᵢⱼ wᵢⱼ zᵢ zⱼ / Σ zᵢ² | Sempre significativo com n grande; depende de W | Núcleo; reportar com k = 6, queen e distância |
| Local Moran (LISA) | Iᵢ = zᵢ Σⱼ wᵢⱼ zⱼ | Milhares de testes; municípios grandes dominam o mapa | Núcleo; FDR (BH), permutação condicional |
| Margem absoluta | \|sA − sB\| | Depende do turno e da base (válidos vs aptos) | Núcleo; base = válidos, e aptos como robustez |
| Landslide | Σ eleitores em munic. com \|margem\| > c / total | Sensível ao corte e ao tamanho dos municípios | Exploratória; c ∈ {15, 20, 30} |
| Bimodalidade | Dip de Hartigan; coeficiente de bimodalidade | Mistura de regiões gera bimodalidade espúria | Exploratória; também dentro de cada região |
| Esteban-Ray | Σᵢⱼ πᵢ^(1+α) πⱼ \|yᵢ − yⱼ\| | Exige posições individuais; com 2 blocos degenera numa função das parcelas | **Cortar** |
| NEC (Laakso-Taagepera) | 1 / Σ pᵢ² | Só faz sentido no 1º turno | Núcleo descritivo |
| Pedersen | ½ Σ \|pᵢₜ − pᵢₜ₋₁\| | Exige mapear partidos para blocos entre anos; candidatos mudam de partido | Núcleo (entre blocos); "dentro do bloco" é exploratória |
| Nacionalização | Decomposição de variância do swing | Confunde nacionalização com homogeneização regional | Exploratória (H6) |
| Persistência | corr(sₜ, sₜ₋₁) ponderada; inclinação de sₜ sobre sₜ₋₁ | Regressão à média | Núcleo |
| Alienação | (abst + brancos + nulos) / aptos | Cadastro desatualizado | Núcleo, com controle aptos/pop 18+ |
| Voto dividido | \|s_pres − s_gov alinhado\| | Ecológico; alinhamento subjetivo | Só H1, com regra explícita |
| Decomposição da variância por nível | Var total = Var_UF + Var_mun\|UF + Var_seção\|mun (multinível, logit, ponderado) | Seções mudam entre anos; agregação de seções em locais de votação | **Núcleo (eixo 2)**; não exige georreferenciamento |
| Isolamento e exposição | Isolamento_A = Σᵢ (aᵢ/A)·(aᵢ/tᵢ); exposição_A→B = Σᵢ (aᵢ/A)·(bᵢ/tᵢ) | Depende da escala (município ≠ seção); sempre reportar os dois blocos | **Núcleo (eixo 3)** |
| Segregação intramunicipal espacial | Dissimilaridade com seções georreferenciadas | Exige seções geocodificadas + setores | **Cortar** (a versão sem georreferenciamento entra acima) |

---

## 5. Dados

### 5.1 Catálogo (verificado nesta sessão, salvo indicação)

| Fonte | O que existe | Nível | Status | Link |
|---|---|---|---|---|
| TSE: resultados 2014/18/22 | `votacao_candidato_munzona`, `detalhe_votacao_munzona`, `votacao_secao` (CSV latin-1, `;`) | Município × zona; seção | Disponível (só `detalhe_2022` está no disco) | https://dadosabertos.tse.jus.br/ |
| TSE: resultados 2026 provisórios | Divulgação em tempo real (JSON), boletins de urna por seção | Seção / município | Disponível a partir de hoje às 17h; **provisório** | https://resultados.tse.jus.br |
| TSE: resultados 2026 finais | Mesmos arquivos de dados abertos | Município × zona; seção | **Ainda não** (semanas após o pleito) | portal acima |
| TSE: eleitorado 2026 | Eleitorado, perfil por seção (por UF), eleitorado por local de votação | Seção / local | Disponível (verificado) | https://dadosabertos.tse.jus.br/dataset/eleitorado-2026 |
| TSE: coordenadas dos locais | Colunas de lat/long no arquivo de locais | Local | **Parcial / não verificado**: a página não lista o esquema; há relatos de valores ausentes. Checar no download. | idem |
| TSE: candidaturas e coligações | `consulta_cand`, `consulta_coligacao` | Candidato | Disponível (padrão conhecido; não reverificado) | portal acima |
| TSE: municipais 2016/20/24 | Resultados de prefeito e candidaturas | Município | Disponível (não reverificado) | portal acima |
| De-para TSE↔IBGE | Diretório da Base dos Dados (5.570, sem Boa Esperança do Norte) **e** config do TSE 2026 `mun-e006257-cm.json` (5.571, com código IBGE). Os dois coincidem 100% | Município | Disponível (verificado) | https://basedosdados.org/dataset/br-bd-diretorios-brasil |
| IBGE: malhas | Malha municipal anual (2022, 2024, 2025) | Município | Disponível | https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html |
| Censo 2022: universo | Agregados por setor (>3.000 variáveis: alfabetização, cor/raça, idade, domicílios) + malha de setores, nov/2024 | Setor, bairro, município | Disponível (verificado) | https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html |
| Censo 2022: educação (amostra) | Nível de instrução, anos de estudo, % superior | Município | Disponível, preliminar, fev/2025 (verificado) | https://sidra.ibge.gov.br/pesquisa/censo-demografico/demografico-2022/amostra-educacao |
| Censo 2022: trabalho e rendimento (amostra) | Renda pc média e mediana (t10295), composição da renda (t10297), classes de renda pc (t10296). **Gini (t10301) e a t10315 só vão até UF na API**: sem Gini municipal | Município (exceto Gini) | Disponível, preliminar, 09/10/2025 (verificado na API em 04/10/2026) | https://www.ibge.gov.br/novo-portal-destaques/44425-ibge-divulgara-em-9-de-outubro-de-2025-censo-demografico-2022-trabalho-e-rendimento-resultados-preliminares-da-amostra.html |
| Censo 2022: religião (amostra) | Grandes grupos religiosos | Município | Disponível, preliminar (verificado) | idem portal do Censo |
| Censo 2010 | Tudo o que entra no IDHM 2010 | Município, setor | Disponível | Atlas Brasil / SIDRA |
| IDHM oficial | **Só 2010** para municípios. Para 2022 e 2024 há IDHM por PNAD Contínua apenas para UF e RM | Município (2010) | **IDHM municipal 2022: não encontrado** | https://www.atlasbrasil.org.br |
| REGIC | Edição 2018 (publicada em 2020) é a mais recente | Município | Disponível; **não há edição nova** | https://www.ibge.gov.br/geociencias/cartas-e-mapas/redes-geograficas/15798-regioes-de-influencia-das-cidades.html |
| RAIS | Vínculos por natureza jurídica, setor e remuneração | Estabelecimento → município | Disponível (último ano não verificado) | http://pdet.mte.gov.br/microdados-rais-e-caged |
| INEP: IDEB | Por escola e município, bienal | Município | Disponível até 2023; 2025 não verificado | https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb |
| DATASUS: SIM/SINASC | Óbitos (homicídios X85–Y09) e nascidos vivos | Município de residência | Disponível; anos recentes são preliminares | https://opendatasus.saude.gov.br/ |
| Atlas da Violência | Homicídios estimados, edição municipal 2024 (PDF/painel) | Município | Disponível (verificado), mas derivado do SIM | https://www.ipea.gov.br/atlasviolencia/publicacoes/286/atlas-2024-municipios |
| Bolsa Família | Famílias e valores mensais | Município | Disponível (não reverificado) | https://aplicacoes.mds.gov.br/sagi/vis/data3/ |
| PIB municipal | Anual, defasagem de cerca de 2 anos | Município | Disponível (não reverificado) | SIDRA |
| Anatel: banda larga fixa | Acessos mensais | Município | Disponível (não reverificado) | https://informacoes.anatel.gov.br/paineis/acessos |

**O que NÃO existe e como contornar:**
- **IDHM municipal 2022:** usar os componentes diretamente (§2.10). Se precisar de um mapa, criar um `idx_desenv_2022_NAO_OFICIAL` = média geométrica de min-max dos componentes, com as balizas do IDHM 2010. O nome do arquivo e o rótulo deixam explícito que não é oficial.
- **Longevidade municipal 2022:** o Censo não publica esperança de vida por município. Usar como proxy a mortalidade infantil 2020–22 (SIM/SINASC), suavizada por Bayes empírico porque em municípios pequenos há muita variação.
- **Renda municipal anual:** não existe. Usar massa salarial formal da RAIS, PIB per capita e transferências per capita.
- **Tempo de viagem ao centro regional:** rotear todos os municípios é caro. Usar distância geodésica até o centro REGIC; tempo de viagem fica fora do escopo.

### 5.2 Problemas de harmonização (soluções explícitas)

1. **Código TSE (5 dígitos) vs IBGE (7 dígitos):** usar o diretório da Base dos Dados, com teste `test_depara`: correspondência 1:1, cobertura de 100% dos municípios em cada ano e nenhuma linha ZZ.
2. **Municípios novos:** os 5.570 estão estáveis desde 1/1/2013 e são iguais em 2014, 2018 e 2022. **Boa Esperança do Norte (MT)** foi instalado em 1/1/2025, a partir de Sorriso e Nova Ubiratã, e 2026 é a primeira eleição geral com ele. Solução: criar uma **AMC** (área mínima comparável) que junta Sorriso + Nova Ubiratã + Boa Esperança do Norte em todas as análises longitudinais. Nas análises transversais de 2026, ele entra separado.
3. **Seções e locais mudam entre eleições:** sem chave estável, por isso a análise principal é municipal. A seção só aparece numa checagem de MAUP em 1 ou 2 UFs, como opcional.
4. **Provisório vs final:**
   - Cada snapshot fica em `data/raw/tse/2026/divulga/<timestamp>/` com `SHA256SUMS` e a flag `provisorio=true` em todas as tabelas derivadas.
   - Quando saírem os arquivos finais, o teste `test_diff_provisorio_final` compara os dois e lista os municípios com |Δ votos| > 0,5%. Isso acontece, por exemplo, por votos *sub judice* ou por totalizações refeitas.
   - Nenhum resultado do artigo usa dados provisórios. A previsão usa e declara isso.
5. **Eleitores do exterior (ZZ) e voto em trânsito:** ficam fora do painel municipal e são reportados à parte.
6. **Ilhas no grafo (queen):** municípios como Fernando de Noronha, Ilhabela e outros insulares ficam sem vizinhos. O ICAR exige grafo conexo. Solução: grafo união queen ∪ kNN(1) e conferir o número de componentes = 1 antes de rodar o BYM2. A escala do BYM2 é calculada por componente.
7. **Dois censos:** cada eleição usa o censo mais próximo (2014 e 2018 → 2010; 2022 e 2026 → 2022). Só variáveis definidas da mesma forma nos dois censos entram em comparações entre anos.

---

## 6. Corte de escopo (uma pessoa)

| Núcleo (faz o artigo existir) | Exploratório (se sobrar tempo) | Descartar |
|---|---|---|
| Painel municipal presidencial 2014–2026 (1º e 2º turnos) + seções (`votacao_secao`) | H3, H1, P5 (desertos de notícia) | MGWR (O(n²), redundante com inclinações aleatórias) |
| Métricas: Moran/LISA, margem, NEC, Pedersen entre blocos, persistência, alienação, decomposição por nível, isolamento e exposição | H7 e cadastro (artigo separado) | Segregação intramunicipal espacial (georreferenciada) |
| Pares de fronteira entre UFs (eixo 1, T2) | | RDD geográfico completo |
| Modelo central BYM2 + UF + estrutura e decomposição de Shapley | XGBoost + SHAP com CV espacial em blocos, só como checagem de não linearidade | Esteban-Ray |
| Eixos 1–3 (§1b) + P3 (com H4) + P4; H2 como métrica-base | Gradiente REGIC com splines (vira covariável no núcleo, sem módulo próprio) | Casamento de sobrenomes (H1) |
| | H1 completa com voto dividido para governador | Tempo de viagem por rede viária |
| SAR/SEM no spreg como robustez frequentista | Checagem de MAUP por seção em 1 ou 2 UFs | SDM, além do SAR/SEM |
| Pré-registro + previsão do 2º turno | | DVC (Makefile + checksums bastam) |

Se só der para fazer uma coisa nas próximas 3 semanas, faça a Trilha A. Se só der para fazer uma hipótese no artigo, faça a pergunta central (decomposição) + H2. As duas usam o mesmo modelo.

---

## 7. Fases, marcos e critérios de aceitação

### Trilha A: pré-registro e previsão (04/10 → 25/10, depois avaliação)

| Marco | Prazo | Critério de aceitação |
|---|---|---|
| A0 Pré-registro | **04/10 antes das 17h** (ou declarar que os dados já foram vistos) | `HIPOTESES.md` commitado, com tag git `prereg-v1` e timestamp externo (release no GitHub + DOI no Zenodo, ou OSF). Inclui a declaração do que já foi visto: pesquisas de opinião, resultados provisórios |
| A1 Quarentena | 05/10 | Dados sintéticos e saídas derivadas apagados ou movidos; README avisando; decisão sobre o histórico (Pergunta 1) |
| A2 Ingestão mínima | 09/10 | 2014, 2018 e 2022 (1º e 2º turnos) + snapshot de 2026 por município; `test_depara` e totais nacionais conferem com o TSE (±0) |
| A3 Backtest | 15/10 | Modelo 1º turno → 2º turno treinado em 2014 e 2018 e testado em 2022. Previsões de abstenção e \|margem\| por município, com MAE ponderado < baseline (persistência + swing uniforme) e cobertura de IC80 entre 75% e 85% |
| A4 Previsão publicada | **22/10** (máximo 24/10) | Arquivo `forecast_2T_2026.csv` (município, abstenção, \|margem\|, IC80, IC95) + hash + release congelada. Sem nomes de candidatos, sem lado |
| A5 Avaliação | após os arquivos finais | MAE, CRPS, cobertura vs baseline, nos termos fixados em A0. Relatório publicado mesmo se a previsão for ruim |

Desenho da previsão: o 2º turno é previsto a partir do 1º turno por município, com transferências estimadas por regressão ecológica (Goodman com restrição, ou EI hierárquico) treinadas nos pares 1T→2T de 2014, 2018 e 2022. Abstenção do 2º turno = abstenção do 1º turno + Δ histórico por município (encolhido para a média da UF).

### Trilha B: artigo

| Fase | Duração | Marco e critério de aceitação |
|---|---|---|
| 0 Setup | 3 dias | `uv` com Python fixo; `make all` roda do zero; `pytest` verde; `data/` no `.gitignore`; config em `config/*.yaml`; seed global |
| 1 Ingestão e harmonização | 3 a 4 semanas | Painel `muni × eleição × turno` com contagens; 100% dos municípios casados; AMC para Boa Esperança do Norte; covariáveis com dicionário (fonte, ano, definição, tratamento, risco); testes de faixa e de soma (votos ≤ comparecimento ≤ aptos) |
| 2 Descritivas e métricas | 2 semanas | Todas as métricas do núcleo calculadas para 4 eleições; mapas; um gráfico de sensibilidade por métrica (W, corte) |
| 3 Modelos centrais | 5 a 6 semanas | BYM2 convergindo (R̂ < 1,01, ESS > 400, sem divergências), checagem preditiva posterior; decomposição de Shapley com intervalo; H2, H3, H4 e H1-reduzida com veredito pelos critérios do pré-registro |
| 4 Robustez | 3 semanas | W (k = 4, 6, 8, queen, distância), escala (município vs microrregião, para MAUP), com e sem colineares (VIF / PCA), SAR/SEM, XGBoost + SHAP com CV espacial em blocos, BH nas famílias de testes |
| 5 Comunicação | 3 semanas | Texto com seção de limitações (falácia ecológica, MAUP, confusão espacial, cadastro); `make paper` reproduz figuras e tabelas |

---

## 8. Estrutura proposta do repositório

```
eleicoes-geo/
├── PLAN.md  HIPOTESES.md  DATA.md (catálogo + dicionário)  README.md
├── pyproject.toml  uv.lock  Makefile
├── config/
│   ├── fontes.yaml        # URLs, anos, checksums esperados
│   └── params.yaml        # seeds, cortes, W, priors
├── src/geovoto/
│   ├── ingest/            # um módulo por fonte (tse.py, ibge.py, rais.py…)
│   ├── harmonize.py       # de-para, AMC, painel
│   ├── metrics.py
│   ├── spatial.py         # W, Moran, LISA
│   ├── models/            # bym2.py, panel_h3.py, forecast.py
│   └── viz.py
├── tests/                 # test_depara, test_totais, test_metrics (pytest + asserts)
├── notebooks/             # só exploração, nunca usados pela pipeline
├── reports/  (paper/, figuras/)
└── data/  (fora do git)
    ├── raw/<fonte>/<ano>/ + SHA256SUMS   # imutável
    ├── interim/
    └── processed/
```

Começo com poucos arquivos. Um módulo novo só é criado quando o existente passar de algumas centenas de linhas.

---

## 9. Registro de riscos

| # | Risco | Tipo | Prob. | Impacto | Mitigação |
|---|---|---|---|---|---|
| R1 | Resultados sintéticos tratados como reais / já publicados | Integridade | Já ocorreu | Alto | Quarentena (A1), reescrever o histórico, nota no README |
| R2 | Pré-registro feito depois de ver os dados | Metodológico | Alta (hoje) | Alto | Congelar antes das 17h, ou declarar exatamente o que foi visto |
| R3 | Sem 2º turno presidencial | Escopo | Desconhecida | Médio | Previsão passa para governadores com 2º turno, ou Trilha A vira só a avaliação do 1º turno contra um baseline pré-registrado |
| R4 | Partição E/V/T não identificada (confusão espacial) | Metodológico | Certa | Alto | Shapley com intervalo; linguagem "dependência", não "efeito" |
| R5 | Falácia ecológica | Metodológico | Certa | Médio | Declarada; nenhuma afirmação sobre indivíduos |
| R6 | MAUP | Metodológico | Certa | Médio | Microrregião vs município; seção em 1 ou 2 UFs |
| R7 | Arquivos finais do TSE atrasam | Técnico | Média | Médio | Pipeline parametrizada por snapshot; teste de diferença |
| R8 | BYM2 lento ou sem convergir com 5.570 nós | Técnico | Média | Médio | Parametrização não centrada, priors PC, `nutpie`; subamostra por região para depurar |
| R9 | Codificação de blocos e coligações subjetiva | Metodológico | Alta | Médio | Regra escrita no pré-registro (coligação formal no TSE); análise de sensibilidade |
| R10 | Cadastro desatualizado distorce a abstenção | Metodológico | Alta | Médio | Covariável aptos/pop 18+; reportar a abstenção "ajustada" como robustez |
| R11 | Defasagem de covariáveis (Censo 2022 para 2026) | Metodológico | Certa | Baixo | Declarado; séries anuais para variações |
| R12 | Comparações múltiplas (LISA, inclinações, H1–H7) | Metodológico | Certa | Médio | BH por família + encolhimento hierárquico |
| R13 | Escopo grande para uma pessoa | Gestão | Alta | Alto | §6; Trilha A primeiro; exploratórias só depois da Fase 3 |
| R14 | Python 3.14 sem wheels de PyMC, PyTensor ou spreg | Técnico | Média | Baixo | Fixar a versão com `uv` (3.12 até verificar compatibilidade) |
| R15 | Linguagem enviesada em figuras e texto | Neutralidade | Média | Alto | Paleta neutra (sem cores partidárias), A/B por papel, revisão com checklist antes de publicar |

---

## 10. Perguntas para você (bloqueiam a implementação)

1. **Repositório:** o `github.com/mchqueiroz/eleicao` é público? Posso (a) reescrever o histórico para remover os parquets sintéticos e os dados brutos, ou (b) começar um repositório novo e arquivar o antigo?
2. **Pré-registro hoje:** você quer congelar o HIPOTESES.md **antes das 17h de hoje**? Onde: release no GitHub + Zenodo, ou OSF? O que você já viu (pesquisas, boca de urna, resultados parciais)? Isso precisa constar na declaração.
3. **Desfecho principal da pergunta central:** concorda com logit da participação do bloco incumbente + comparecimento + |margem|, com as três decomposições reportadas? Ou prefere uma só?
4. **Cargos:** só presidente, ou também governador? Governador é necessário para o voto dividido de H1 e dobra o trabalho de codificação.
5. **Regra de bloco:** aceita "coligação formal registrada no TSE" como critério para alinhar candidatos a governador aos blocos presidenciais?
6. **2018 em H3:** concorda em excluir 2018 da análise principal, já que o bloco incumbente teve votação marginal?
7. **Sem 2º turno presidencial:** a previsão migra para governadores ou a Trilha A é cancelada?
8. **Tempo e produto:** quantas horas por semana você tem e qual o destino (periódico, tese, relatório público)? Isso define o tamanho das fases 3 a 5.
9. **Python:** posso fixar 3.12 via `uv` e descartar o `venv/` atual?
10. **Uma versão do H1 que você não quer perder:** a parte de sobrenome é importante para você? No plano ela foi cortada.
