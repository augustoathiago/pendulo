import math
from pathlib import Path

import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import streamlit.components.v1 as components
from matplotlib.ticker import FuncFormatter

# ----------------------------
# Configuração geral
# ----------------------------
st.set_page_config(page_title="Pêndulo Simples Física II", layout="wide")

# ----------------------------
# Helpers de compatibilidade
# ----------------------------
def st_image_full_width(image_path: str):
    try:
        st.image(image_path, use_container_width=True)
    except TypeError:
        st.image(image_path, use_column_width=True)


def st_pyplot_full_width(fig):
    try:
        st.pyplot(fig, use_container_width=True)
    except TypeError:
        st.pyplot(fig)

# ----------------------------
# Formatação numérica
# ----------------------------
def fmt3(x):
    try:
        if x == 0:
            return "0"
        return f"{x:.3g}"
    except Exception:
        return str(x)


def latex_num(x):
    s = fmt3(x)
    if "e" in s or "E" in s:
        base, exp = s.replace("E", "e").split("e")
        return rf"{base}\times 10^{{{int(exp)}}}"
    return s


def sig3_tick(x):
    try:
        if x == 0:
            return "0"
        ax = abs(x)
        exp = int(math.floor(math.log10(ax)))
        if exp >= 3 or exp <= -4:
            mant = ax / (10 ** exp)
            sign = "-" if x < 0 else ""
            return f"{sign}{mant:.2f}e{exp}"
        dec = max(0, 2 - exp)
        return f"{x:.{dec}f}"
    except Exception:
        return str(x)


sig3_formatter = FuncFormatter(lambda x, pos: sig3_tick(x))


def apply_sig3(ax):
    ax.xaxis.set_major_formatter(sig3_formatter)
    ax.yaxis.set_major_formatter(sig3_formatter)
    ax.xaxis.get_offset_text().set_visible(False)
    ax.yaxis.get_offset_text().set_visible(False)

# ----------------------------
# Cache dos cálculos
# ----------------------------
@st.cache_data(ttl=3600, max_entries=256)
def compute_series(L, g, theta0, n_cycles, N):
    T = 2 * math.pi * math.sqrt(L / g)
    f = 1.0 / T
    omega0 = 2 * math.pi / T

    t = np.linspace(0, n_cycles * T, N, dtype=np.float32)
    thetaM = abs(theta0)
    phi = math.pi / 2 if theta0 >= 0 else -math.pi / 2

    w = np.float32(omega0)
    thM = np.float32(thetaM)

    theta = thM * np.sin(w * t + phi)
    theta_dot = thM * w * np.cos(w * t + phi)
    theta_ddot = -thM * w**2 * np.sin(w * t + phi)

    U = 0.5 * g * L * theta**2
    K = 0.5 * (L * theta_dot) ** 2
    E = U + K

    return T, f, omega0, phi, t, theta, theta_dot, theta_ddot, U, K, E

# ----------------------------
# ✅ Animação com FPS limitado
# ----------------------------
@st.cache_data(ttl=3600, max_entries=256)
def build_anim_html(L, g, theta0, T, omega0, phi):
    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<style>
canvas {{
  border: 1px solid #ddd;
  border-radius: 14px;
  background: #fff;
}}
</style>
</head>
<body>

<canvas id="cv" width="640" height="420"></canvas>

<script>
(() => {{
  const L = {float(L)};
  const theta0 = {float(theta0)};
  const w = {float(omega0)};
  const phi = {float(phi)};
  const thetaM = Math.abs(theta0);

  const FPS = 20;
  const interval = 1000 / FPS;
  let last = 0;

  const cv = document.getElementById("cv");
  const ctx = cv.getContext("2d");
  const W = cv.width, H = cv.height;

  const pivot = {{x: W/2, y: 40}};
  const lengthPx = H * 0.6;
  const bobR = 14;

  let t0 = performance.now();

  function draw(now) {{
    if (now - last < interval) {{
      requestAnimationFrame(draw);
      return;
    }}
    last = now;

    const t = (now - t0) / 1000;
    const th = thetaM * Math.sin(w*t + phi);

    const x = pivot.x + lengthPx * Math.sin(th);
    const y = pivot.y + lengthPx * Math.cos(th);

    ctx.clearRect(0,0,W,H);

    ctx.strokeStyle = "#111";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(pivot.x, pivot.y);
    ctx.lineTo(x, y);
    ctx.stroke();

    ctx.fillStyle = "#2563eb";
    ctx.beginPath();
    ctx.arc(x, y, bobR, 0, Math.PI*2);
    ctx.fill();

    ctx.fillStyle = "#111";
    ctx.font = "14px system-ui";
    ctx.fillText("t = " + t.toPrecision(3) + " s", 16, 24);
    ctx.fillText("θ = " + th.toPrecision(3) + " rad", 16, 44);

    requestAnimationFrame(draw);
  }}

  requestAnimationFrame(draw);
})();
</script>

</body>
</html>
"""

# ----------------------------
# Interface
# ----------------------------
st.title("Pêndulo Simples – Física II")

L = st.slider("Comprimento L (m)", 0.5, 5.0, 1.0, 0.01)
g = st.slider("Gravidade g (m/s²)", 1.0, 20.0, 9.81, 0.01)
theta0 = st.slider("Ângulo inicial θ₀ (rad)", -1.5, 1.5, 0.2, 0.001)

T, f, omega0, phi, t, theta, theta_dot, theta_ddot, U, K, E = compute_series(
    L, g, theta0, 5, 1500
)

st.subheader("Animação")
components.html(build_anim_html(L, g, theta0, T, omega0, phi), height=460)

st.subheader("Gráficos")

fig, ax = plt.subplots()
ax.plot(t, theta)
ax.set_xlabel("t (s)")
ax.set_ylabel("θ (rad)")
apply_sig3(ax)
st_pyplot_full_width(fig)
plt.close(fig)
