import math
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import streamlit.components.v1 as components
from matplotlib.ticker import FuncFormatter
from pathlib import Path

# ----------------------------
# Configuração geral
# ----------------------------
st.set_page_config(page_title="Pêndulo Simples Física II", layout="wide")

def fmt3(x):
    """3 algarismos significativos (string) - para badges/textos."""
    try:
        if x == 0:
            return "0"
        return f"{x:.3g}"
    except Exception:
        return str(x)

def latex_num(x):
    """Número com 3 algarismos significativos para LaTeX."""
    s = fmt3(x)
    if "e" in s or "E" in s:
        base, exp = s.replace("E", "e").split("e")
        exp = int(exp)
        return rf"{base}\times 10^{{{exp}}}"
    return s

def sig3_tick(x):
    """
    Formata ticks com 3 algarismos significativos FIXOS, mantendo zeros finais.
    Exemplos:
      0.2   -> 0.200
      0.15  -> 0.150
      0.05  -> 0.0500
      1.2   -> 1.20
