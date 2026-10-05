# Entre lugares e dentro deles

Geografia da divisão eleitoral no Brasil, 2014–2026 (análise ecológica, por município).

- `PLAN.md`: plano, fontes, riscos e escopo
- `HIPOTESES.md`: pré-registro (rascunho até a tag `prereg-v1`)
- `legacy/`: versão anterior; **contém dados sintéticos, não usar como evidência** (ver `legacy/LEIAME.md`)

## Rodar

```sh
uv sync
make download     # ~1,5 GB do TSE + diretório de municípios (Base dos Dados)
make verificar    # confere os hashes em raw.sha256
make all          # painel municipal + testes
```

Saída: `data/processed/painel_presidente.parquet`, com uma linha por ano × turno × município e as contagens
de aptos, comparecimento, abstenção, válidos, brancos, nulos, votos de A e B (1º e 2º colocados nacionais
no 1º turno) e o NEC. Os dados ficam fora do git.
