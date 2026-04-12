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
# Formatação numérica
# ----------------------------
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
    Ticks com 3 algarismos significativos FIXOS, mantendo zeros finais.
    """
    try:
        if x == 0:
            return "0"
        ax = abs(x)
        exp = int(math.floor(math.log10(ax)))

        # notação científica para valores muito grandes/pequenos
        if exp >= 3 or exp <= -4:
            mant = ax / (10 ** exp)
            sign = "-" if x < 0 else ""
            return f"{sign}{mant:.2f}e{exp}"

        # notação fixa com casas necessárias para garantir 3 AS
        dec = 2 - exp
        if dec < 0:
            dec = 0
        return f"{x:.{dec}f}"
    except Exception:
        return str(x)


sig3_formatter = FuncFormatter(lambda x, pos: sig3_tick(x))


def apply_sig3(ax):
    """Aplica formatter 3 AS nos eixos x e y e remove textos de offset."""
    ax.xaxis.set_major_formatter(sig3_formatter)
    ax.yaxis.set_major_formatter(sig3_formatter)
    ax.xaxis.get_offset_text().set_visible(False)
    ax.yaxis.get_offset_text().set_visible(False)


# ----------------------------
# Cache dos cálculos (reduz custo de reruns e evita estouro)
# ----------------------------
@st.cache_data(ttl=3600, max_entries=256)
def compute_series(L, g, theta0, n_cycles, N):
    """
    Retorna constantes e séries temporais para gráficos.
    Usa float32 para reduzir RAM no Streamlit Cloud.
    """
    L = float(L)
    g = float(g)
    theta0 = float(theta0)

    T = 2 * math.pi * math.sqrt(L / g)
    f = 1.0 / T
    omega0 = 2 * math.pi / T

    thetaM = abs(theta0)
    phi = (math.pi / 2) if theta0 >= 0 else (-math.pi / 2)

    t_max = n_cycles * T
    N = int(N)

    # arrays em float32 (metade da RAM vs float64)
    t = np.linspace(0, t_max, N, dtype=np.float32)

    w = np.float32(omega0)
    ph = np.float32(phi)
    thM = np.float32(thetaM)

    theta = thM * np.sin(w * t + ph)
    theta_dot = thM * w * np.cos(w * t + ph)
    theta_ddot = -thM * (w ** 2) * np.sin(w * t + ph)

    # Energia (m = 1 kg) no regime harmônico: U = 1/2 m g L theta^2 ; K = 1/2 m (L theta_dot)^2
    m = np.float32(1.0)
    Lf = np.float32(L)
    gf = np.float32(g)

    U = 0.5 * m * gf * Lf * (theta ** 2)
    K = 0.5 * m * ((Lf * theta_dot) ** 2)
    E = U + K

    return T, f, omega0, phi, t, theta, theta_dot, theta_ddot, U, K, E


@st.cache_data(ttl=3600, max_entries=256)
def build_anim_html(L, g, theta0, T, omega0, phi):
    """Gera HTML/JS do canvas. Cacheado para não recriar string gigante sempre."""
    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
  .wrap {{
    width: 100%;
    display: flex;
    gap: 16px;
    align-items: flex-start;
    flex-wrap: wrap;
  }}
  canvas {{
    border: 1px solid #ddd;
    border-radius: 14px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    background: #fff;
  }}
  .meta {{
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    min-width: 260px;
  }}
  .meta h4 {{
    margin: 0 0 8px 0;
    font-size: 16px;
  }}
  .badge {{
    display:inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    background: #f3f4f6;
    margin: 4px 6px 0 0;
    font-size: 12px;
  }}
  .small {{
    color: #444;
    font-size: 13px;
    line-height: 1.35;
  }}
</style>
</head>
<body>
<div class="wrap">
  <canvas id="cv" width="640" height="420"></canvas>
  <div class="meta">
    <h4>Parâmetros (3 algarismos significativos)</h4>
    <div class="badge">L = {fmt3(L)} m</div>
    <div class="badge">g = {fmt3(g)} m/s²</div>
    <div class="badge">θ₀ = {fmt3(theta0)} rad</div>
    <div class="badge">T = {fmt3(T)} s</div>
    <div class="badge">ω₀ = {fmt3(omega0)} rad/s</div>
    <div class="badge">φ = {fmt3(phi)} rad</div>
    <p class="small">
      Convenção: direita (+), esquerda (−).<br/>
      θ(t)=|θ₀|·sin(ω₀t+φ).
    </p>
  </div>
</div>

<script>
(() => {{
  const L = {float(L)};
  const theta0 = {float(theta0)};
  const w = {float(omega0)};
  const phi = {float(phi)};
  const thetaM = Math.abs(theta0);

  const cv = document.getElementById("cv");
  const ctx = cv.getContext("2d");

  const W = cv.width, H = cv.height;
  const pivot = {{x: W*0.5, y: 40}};
  const Lmax = 5.0;
  const lengthPx = (H - 120) * (L / Lmax);

  const bobR = 16;
  const toPrec3 = (x) => Number(x).toPrecision(3);

  let t0 = performance.now();

  function draw(now) {{
    const t = (now - t0)/1000.0;
    const th = thetaM * Math.sin(w*t + phi);

    const x = pivot.x + lengthPx * Math.sin(th);
    const y = pivot.y + lengthPx * Math.cos(th);

    ctx.clearRect(0,0,W,H);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0,0,W,H);

    ctx.strokeStyle = "#e5e7eb";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, pivot.y);
    ctx.lineTo(W, pivot.y);
    ctx.stroke();

    ctx.strokeStyle = "#111827";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(pivot.x - 60, pivot.y);
    ctx.lineTo(pivot.x + 60, pivot.y);
    ctx.stroke();

    ctx.strokeStyle = "#374151";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(pivot.x, pivot.y);
    ctx.lineTo(x, y);
    ctx.stroke();

    ctx.fillStyle = "#2563eb";
    ctx.beginPath();
    ctx.arc(x, y, bobR, 0, Math.PI*2);
    ctx.fill();

    ctx.strokeStyle = "rgba(17,24,39,0.35)";
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = "#111827";
    ctx.font = "14px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillText("t = " + toPrec3(t) + " s", 16, 22);
    ctx.fillText("θ(t) = " + toPrec3(th) + " rad", 16, 42);

    requestAnimationFrame(draw);
  }}

  requestAnimationFrame(draw);
}})();
</script>
</body>
</html>
"""


# ----------------------------
# Cabeçalho (logo + título + descrição)
# ----------------------------
logo_path = Path("logo_maua.png")
cols = st.columns([1, 6])

with cols[0]:
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
    else:
        st.caption("⚠️ Coloque `logo_maua.png` na mesma pasta do `app.py`.")

with cols[1]:
    st.title("Pêndulo Simples Física II")
    st.write("**Descrição:** Altere os parâmetros para estudar o comportamento de um pêndulo simples liberado do repouso.")

st.divider()


# ----------------------------
# Controles: modo de atualização
# ----------------------------
st.subheader("Parâmetros")

st.caption(
    "Dica: se o app estiver pesado no Streamlit Cloud, desative **Atualizar automaticamente** "
    "para recalcular só quando clicar em **Aplicar**."
)

auto_update = st.toggle("Atualizar automaticamente", value=True)

# Estado inicial
defaults = {
    "L_slider": 1.00, "L_input": 1.00,
    "g_slider": 9.81, "g_input": 9.81,
    "theta0_slider": 0.200, "theta0_input": 0.200,
    "N": 1500,
    "sync_lock": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ----------------------------
# Sincronização robusta slider <-> input (evita "ping-pong")
# ----------------------------
def _sync_pair(src_key, dst_key):
    if st.session_state.sync_lock:
        return
    st.session_state.sync_lock = True
    st.session_state[dst_key] = st.session_state[src_key]
    st.session_state.sync_lock = False


def sync_L_from_slider():
    _sync_pair("L_slider", "L_input")


def sync_L_from_input():
    _sync_pair("L_input", "L_slider")


def sync_g_from_slider():
    _sync_pair("g_slider", "g_input")


def sync_g_from_input():
    _sync_pair("g_input", "g_slider")


def sync_theta_from_slider():
    _sync_pair("theta0_slider", "theta0_input")


def sync_theta_from_input():
    _sync_pair("theta0_input", "theta0_slider")


# ----------------------------
# UI dos parâmetros (com ou sem form)
# ----------------------------
def parameter_widgets():
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])

    with c1:
        st.markdown("**Comprimento do pêndulo L (m)**")
        st.slider("L_slider", 0.5, 5.0, key="L_slider", step=0.01, on_change=sync_L_from_slider, label_visibility="collapsed")
        st.number_input("L_input", 0.5, 5.0, key="L_input", step=0.01, on_change=sync_L_from_input, label_visibility="collapsed")

    with c2:
        st.markdown("**Aceleração da gravidade g (m/s²)**")
        st.slider("g_slider", 1.0, 20.0, key="g_slider", step=0.01, on_change=sync_g_from_slider, label_visibility="collapsed")
        st.number_input("g_input", 1.0, 20.0, key="g_input", step=0.01, on_change=sync_g_from_input, label_visibility="collapsed")

    with c3:
        st.markdown("**Ângulo inicial θ₀ (rad)** (direita: + / esquerda: −)")
        st.slider("theta0_slider", -1.50, 1.50, key="theta0_slider", step=0.001, on_change=sync_theta_from_slider, label_visibility="collapsed")
        st.number_input("theta0_input", -1.50, 1.50, key="theta0_input", step=0.001, on_change=sync_theta_from_input, label_visibility="collapsed")

    with c4:
        st.markdown("**Resolução N (pontos)**")
        st.slider("N", 400, 2500, key="N", step=50, label_visibility="collapsed")


if auto_update:
    parameter_widgets()
    applied = True
else:
    with st.form("params_form", clear_on_submit=False):
        parameter_widgets()
        applied = st.form_submit_button("Aplicar")


# Lê parâmetros (sincronizados)
L = float(st.session_state.L_slider)
g = float(st.session_state.g_slider)
theta0 = float(st.session_state.theta0_slider)
N = int(st.session_state.N)
n_cycles = 5


if abs(theta0) > 0.2:
    st.info("ℹ️ Para |θ₀| grande, a aproximação de **pequenos ângulos** perde precisão. "
            "Aqui usamos o modelo de movimento harmônico simples.")


# ----------------------------
# Só calcula/mostra se o usuário aplicou (no modo manual)
# ----------------------------
if not applied:
    st.stop()


# ----------------------------
# Cálculos + séries (cacheado)
# ----------------------------
T, f, omega0, phi, t, theta, theta_dot, theta_ddot, U, K, E = compute_series(L, g, theta0, n_cycles, N)

st.divider()
st.subheader("Cálculos")

cA, cB, cC = st.columns(3)
with cA:
    st.markdown("**Período**")
    st.latex(rf"T = 2\pi\sqrt{{\frac{{L}}{{g}}}} = 2\pi\sqrt{{\frac{{{latex_num(L)}}}{{{latex_num(g)}}}}} = {latex_num(T)}\ \text{{s}}")
with cB:
    st.markdown("**Frequência**")
    st.latex(rf"f = \frac{{1}}{{T}} = \frac{{1}}{{{latex_num(T)}}} = {latex_num(f)}\ \text{{Hz}}")
with cC:
    st.markdown("**Frequência angular natural**")
    st.latex(rf"\omega_0 = \frac{{2\pi}}{{T}} = \frac{{2\pi}}{{{latex_num(T)}}} = {latex_num(omega0)}\ \text{{rad/s}}")


# ----------------------------
# Equações
# ----------------------------
st.divider()
st.subheader("Equações")

thetaM = abs(theta0)
A = thetaM
w = omega0
Aw = A * w
Aw2 = A * (w ** 2)

st.markdown("### Forma simbólica (letras)")
st.latex(r"\theta(t)=\theta_M\sin(\omega_0 t+\varphi)")
st.latex(r"\dot{\theta}(t)=\theta_M\omega_0\cos(\omega_0 t+\varphi)")
st.latex(r"\ddot{\theta}(t)=-\theta_M\omega_0^2\sin(\omega_0 t+\varphi)")

st.markdown("### Forma numérica (substituída e desenvolvida)")
st.latex(rf"\theta(t) = {latex_num(A)}\sin\!\left({latex_num(w)}\,t + {latex_num(phi)}\right)\ \text{{rad}}")
st.latex(rf"\dot{{\theta}}(t) = {latex_num(Aw)}\cos\!\left({latex_num(w)}\,t + {latex_num(phi)}\right)\ \text{{rad/s}}")
st.latex(rf"\ddot{{\theta}}(t) = -{latex_num(Aw2)}\sin\!\left({latex_num(w)}\,t + {latex_num(phi)}\right)\ \text{{rad/s}}^2")


# ----------------------------
# Animação (Canvas JS) — cacheado
# ----------------------------
st.divider()
st.subheader("Animação")

show_anim = st.toggle("Mostrar animação", value=True)

if show_anim:
    anim_html = build_anim_html(L, g, theta0, T, omega0, phi)
    components.html(anim_html, height=460, scrolling=False)
else:
    st.caption("Animação desativada para economizar recursos.")


# ----------------------------
# Gráficos (FECHAR FIGURAS é essencial)
# ----------------------------
st.divider()
st.subheader("Gráficos")


def plot_with_origin(ax, x, y, title, xlabel, ylabel, color):
    ax.plot(x, y, color=color, linewidth=2)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.35)

    ax.axhline(0, color="black", linewidth=2.5, zorder=0)
    ax.axvline(0, color="black", linewidth=2.5, zorder=0)

    apply_sig3(ax)


# Figura 1
fig1, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)

plot_with_origin(
    axes[0], t, theta,
    "Posição angular",
    "t (s)",
    r"$\theta$ (rad)",
    "#2563eb"
)
plot_with_origin(
    axes[1], t, theta_dot,
    "Velocidade angular",
    "t (s)",
    r"$\dot{\theta}$ (rad/s)",
    "#16a34a"
)
plot_with_origin(
    axes[2], t, theta_ddot,
    "Aceleração angular",
    "t (s)",
    r"$\ddot{\theta}$ (rad/s$^2$)",
    "#dc2626"
)

plt.tight_layout()
st.pyplot(fig1, use_container_width=True)
plt.close(fig1)  # <- MUITO IMPORTANTE: evita acumular memória em reruns


# Figura 2 (energias)
fig2, axE = plt.subplots(1, 1, figsize=(10, 4))
axE.plot(t, U, label="Energia potencial U", color="#7c3aed", linewidth=2)
axE.plot(t, K, label="Energia cinética K", color="#f59e0b", linewidth=2)
axE.plot(t, E, label="Energia mecânica total E", color="#16a34a", linewidth=2.5)

axE.set_title("Energia (m = 1 kg)")
axE.set_xlabel("t (s)")
axE.set_ylabel("Energia (J)")
axE.grid(True, alpha=0.35)
axE.axhline(0, color="black", linewidth=2.5, zorder=0)
axE.axvline(0, color="black", linewidth=2.5, zorder=0)

apply_sig3(axE)
axE.legend()

plt.tight_layout()
st.pyplot(fig2, use_container_width=True)
plt.close(fig2)  # <- MUITO IMPORTANTE

st.caption("Observação: energias calculadas no regime de pequenos ângulos (aproximação harmônica), com massa m = 1 kg.")
