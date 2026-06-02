"""
Rode após instalar o requirements.txt:
    python tests/verificar_ambiente.py
"""
import sys

pacotes = [
    ("pandas","2.1"), ("numpy","1.26"), ("geopandas","0.14"),
    ("libpysal","4.9"), ("esda","2.5"), ("spreg","1.6"),
    ("pymc","5.9"), ("arviz","0.18"), ("sklearn","1.4"),
    ("xgboost","2.0"), ("statsmodels","0.14"), ("scipy","1.12"),
    ("matplotlib","3.8"), ("plotly","5.18"), ("requests","2.31"),
]

print(f"Python {sys.version}\n")
print(f"{'Pacote':<20} {'Status':<10} {'Versão'}")
print("-" * 45)
erros = []
for nome, vmin in pacotes:
    try:
        mod = __import__(nome)
        v = getattr(mod, "__version__", "?")
        print(f"{nome:<20} {'ok':<10} {v}")
    except ImportError:
        print(f"{nome:<20} {'FALTANDO':<10}")
        erros.append(nome)
print()
if erros:
    print(f"Faltam: {', '.join(erros)}")
    print("pip install " + " ".join(erros))
else:
    print("Ambiente ok.")