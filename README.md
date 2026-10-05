# Entre lugares e dentro deles

Geografia da divisão eleitoral no Brasil, 2014–2026 (análise ecológica, por município e local de votação).

- `PLAN.md`: plano, fontes, riscos e escopo
- `HIPOTESES.md`: pré-registro (**rascunho até a tag `prereg-v1`**)
- `legacy/`: versão anterior; **contém dados sintéticos, não usar como evidência** (ver `legacy/LEIAME.md`)

## Rodar

```sh
uv sync                    # Python 3.12 gerenciado pelo uv (o PyTensor precisa de Python.h)
make download verificar    # TSE 2014–2022, diretório de municípios, malha 2025 (+ hashes em raw.sha256)
make all                   # painel municipal + testes
make secoes censo vizinhanca
make provisorio2026 previsao   # snapshot provisório do 1º turno 2026 e previsão do 2º turno
make eixos veredito bym2   # análise dos eixos: só roda depois de `git tag prereg-v1`
make economia prefeitos exploratorio mapa   # exploratórias e mapa público
```

| Módulo | Saída (`data/processed/`) |
|---|---|
| `geovoto.tse` | `painel_presidente.parquet`: ano × turno × município, contagens e votos de A/B (1º/2º nacionais no 1º turno) |
| `geovoto.secao` | `locais_presidente.parquet`: votos de A/B por local de votação |
| `geovoto.divulga` | `painel_2026_t1_provisorio.parquet` (provisório, com % totalizado) |
| `geovoto.previsao` | `backtest.csv`, `previsao_2T_2026.csv` (abstenção e \|margem\|, quantis) |
| `geovoto.ibge` | `censo2010_municipio.parquet`, `censo2022_municipio.parquet`, `economia_anual.parquet` |
| `geovoto.espacial` | `vizinhanca.parquet` (queen ∪ kNN1, conexo), `centroides.parquet` |
| `geovoto.eixos`, `geovoto.bym2` | `data/output/` (bloqueado até o pré-registro) |
| `geovoto.veredito` | `data/output/eixos/veredito.md`: critérios do pré-registro aplicados mecanicamente |
| `geovoto.economia` | `rais_municipio.parquet` (2011–2024), `bolsa_familia.parquet` (quebra de série em 2022) |
| `geovoto.municipal` | `prefeitos.parquet`: continuidade partidária e pessoal 2016–2024, margem do prefeito |
| `geovoto.exploratorio` | `data/output/exploratorio/relatorio.md` (H1, H3, H7; exploratório) |
| `geovoto.mapa` | `reports/mapa/` (página publicada como artefato privado) |

Os dados ficam fora do git. Os testes (`make test`) usam os dados reais só para checar consistência
(totais, identidades, cobertura). A lógica estatística é testada em dados simulados dentro dos próprios testes.
