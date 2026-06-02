import pandas as pd

dados = {
    "municipio":   ["Sorocaba", "Sorocaba", "Sorocaba",
                    "Campinas", "Campinas", "Campinas"],
    "candidato":   ["Lula", "Bolsonaro", "Outros",
                    "Lula", "Bolsonaro", "Outros"],
    "votos":       [120000, 95000, 8000,
                    180000, 160000, 12000],
    "brancos":     [5000, 5000, 5000,
                    8000, 8000, 8000],
    "nulos":       [3000, 3000, 3000,
                    4000, 4000, 4000],
    "compareceu":  [231000, 231000, 231000,
                    364000, 364000, 364000],
}

df = pd.DataFrame(dados)

df['total_validos_municipio'] = df.groupby('municipio')['votos'].transform('sum')

df['pct_validos'] = (df['votos'] / df['total_validos_municipio']) * 100

# Vamos ver o resultado na tela
print(df[['municipio', 'candidato', 'votos', 'total_validos_municipio', 'pct_validos']])

