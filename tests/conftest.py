import sys
from pathlib import Path

# Permite importar app.py e o pacote despacho a partir dos testes.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
