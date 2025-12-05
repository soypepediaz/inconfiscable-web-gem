import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Inconfiscable.xyz",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS DE ALTO IMPACTO (MODO CYBERPUNK/PRO) ---
st.markdown("""
<style>
    /* Importar fuente futurista */
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&display=swap');

    /* --- RESET GENERAL --- */
    .stApp {
        background-color: #050505; /* Casi negro */
        font-family: 'Rajdhani', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    p, label {
        color: #E0E0E0 !important;
        font-size: 1.1rem;
    }

    /* --- HEADER PERSONALIZADO --- */
    .main-header {
        text-align: center;
        padding: 40px 0;
        border-bottom: 2px solid #333;
        margin-bottom: 30px;
        background: radial-gradient(circle, #1a1a1a 0%, #000000 100%);
    }
    .main-title {
        font-size: 3.5rem;
        background: -webkit-linear-gradient(#00FF41, #008F24);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0px 0px 20px rgba(0, 255, 65, 0.3);
    }
    .subtitle {
        color: #888;
        font-size: 1.2rem;
        margin-top: -10px;
    }

    /* --- INPUTS MEJORADOS (ALTO CONTRASTE) --- */
    /* Forzar visibilidad en inputs */
    div[data-baseweb="input"] {
        background-color: #111111 !important;
        border: 1px solid #444444 !important;
        border-radius: 4px !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #111111 !important;
        border: 1px solid #444444 !important;
        color: #FFFFFF !important;
    }
    input {
        color: #00FF41 !important; /* Texto verde neón al escribir */
        font-weight: bold;
    }
    label[data-testid="stLabel"] {
        color: #00FF41 !important;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    /* --- TARJETAS DE PASOS (INFOGRAFÍA) --- */
    .step-card {
        background: #111;
        border: 1px solid #333;
        padding: 20px;
        border-radius: 8px;
        height: 100%;
        transition: transform 0.3s ease;
    }
    .step-card:hover {
        transform: translateY(-5px);
        border-color: #00FF41;
    }
    .step-icon { font-size: 2rem; margin-bottom: 10px; display: block; }
    .step-title { color: #fff; font-size: 1.2rem; font-weight: bold; margin-bottom: 5px; }
    .step-desc { color: #aaa; font-size: 0.9rem; }

    /* --- BOTÓN DE ACCIÓN --- */
    .stButton > button {
        background: linear-gradient(90deg, #00FF41 0%, #008F24 100%);
        color: #000;
        font-weight: 800;
        font-family: 'Rajdhani', sans-serif;
        font-size: 1.2rem;
        border: none;
        padding: 15px 0;
        text-transform: uppercase;
        letter-spacing: 2px;
        width: 100%;
        border-radius: 4px;
        margin-top: 20px;
        box-shadow: 0 0 15px rgba(0, 255, 65, 0.4);
    }
    .stButton > button:hover {
        box-shadow: 0 0 25px rgba(0, 255, 65, 0.6);
        color: #000;
    }

    /* --- RESULTADOS (TARJETAS PERSONALIZADAS) --- */
    .result-container {
        display: flex;
        gap: 20px;
        margin-top: 20px;
    }
    .card-trap {
        background-color: #1a0505;
        border: 1px solid #FF3333;
        border-left: 8px solid #FF3333;
        border-radius: 8px;
        padding: 25px;
        flex: 1;
    }
    .card-sov {
        background-color: #051a05;
        border: 1px solid #00FF41;
        border-left: 8px solid #00FF41;
        border-radius: 8px;
        padding: 25px;
        flex: 1;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 0.9rem;
        text-transform: uppercase;
        color: #888;
        margin-top: 15px;
    }
    .highlight-red { color: #FF3333; }
    .highlight-green { color: #00FF41; }
    
    /* Ocultar elementos molestos */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE LÓGICA (Misma funcionalidad robusta) ---
@st.cache_data
def get_bitcoin_data():
    try:
        btc = yf.download("BTC-USD", start="2009-01-01", progress=False)
        if btc is None or btc.empty: return None
        
        # Corrección de columnas robusta
        if isinstance(btc.columns, pd.MultiIndex):
            try: btc_close = btc.xs('Close', axis=1, level=0)
            except: 
                try: btc_close = btc.xs('Close', axis=1, level=1)
                except: btc_close = btc.iloc[:, 0] # Fallback
            if isinstance(btc_close, pd.Series): btc_close = btc_close.to_frame()
            btc = btc_close
        else:
            btc = btc[['Close']] if 'Close' in btc.columns else btc.iloc[:, 0:1]

        btc.columns = ['BTC-USD']
        btc.index = pd.to_datetime(btc.index).tz_localize(None)
        return btc
    except: return None

def calculate_dca(df, start_date, amount, frequency, day_param):
    start_ts = pd.to_datetime(start_date)
    mask = (df.index >= start_ts)
    dca_df = df.loc[mask].copy()
    
    if dca_df.empty: return None, 0, 0
    
    target_dates = []
    if frequency == "Diaria":
        target_dates = dca_df.index
    elif frequency == "Semanal":
        target_dates = dca_df[dca_df.index.dayofweek == day_param].index
    elif frequency == "Mensual":
        grouped = dca_df.groupby([dca_df.index.year, dca_df.index.month])
        for _, group in grouped:
            try:
                specific_date = group[group.index.day == day_param]
                if not specific_date.empty: target_dates.append(specific_date.index[0])
                else: target_dates.append(group.index[-1])
            except: pass
        target_dates = pd.DatetimeIndex(target_dates)

    dca_df = dca_df.loc[dca_df.index.isin(target_dates)].copy()
    if dca_df.empty: return None, 0, 0

    dca_df['Invested_Fiat'] = amount
    dca_df['BTC_Bought'] = dca_df['Invested_Fiat'] / dca_df['BTC-USD']
    dca_df['Total_BTC'] = dca_df['BTC_Bought'].cumsum()
    dca_df['Total_Invested'] = dca_df['Invested_Fiat'].cumsum()
    
    return dca_df, dca_df['Total_BTC'].iloc[-1], dca_df['Total_Invested'].iloc[-1]

def calculate_cagr(start_val, end_val, years):
    if start_val <= 0 or years <= 0: return 0
    return (end_val / start_val)**(1 / years) - 1

# --- UI PRINCIPAL ---

# 1. HEADER GRÁFICO
st.markdown("""
<div class="main-header">
    <div class="main-title">INCONFISCABLE.XYZ</div>
    <div class="subtitle">LA PROPIEDAD PRIVADA DEFINITIVA</div>
</div>
""", unsafe_allow_html=True)

# 2. SECCIÓN VISUAL (HTML Cards en lugar de columnas estándar)
st.markdown("### EL CAMINO A LA SOBERANÍA")
c1, c2, c3, c4 = st.columns(4)

def card_html(icon, title, text, color):
    return f"""
    <div class="step-card" style="border-top: 3px solid {color}">
        <span class="step-icon">{icon}</span>
        <div class="step-title" style="color:{color}">{title}</div>
        <div class="step-desc">{text}</div>
    </div>
    """

with c1: st.markdown(card_html("🏛️", "LA TRAMPA", "Exchange Centralizado. Trazabilidad total. Fondos congelables.", "#FF3333"), unsafe_allow_html=True)
with c2: st.markdown(card_html("🔌", "LA ILUSIÓN", "Autocustodia vigilada. Tienen tus llaves públicas asociadas a tu ID.", "#FFAA00"), unsafe_allow_html=True)
with c3: st.markdown(card_html("🔨", "LA RUPTURA", "Anonimización de fondos. Romper el rastro on-chain.", "#00AAFF"), unsafe_allow_html=True)
with c4: st.markdown(card_html("🛡️", "INCONFISCABLE", "Soberanía pura. Nadie sabe cuánto tienes. Nadie te lo quita.", "#00FF41"), unsafe_allow_html=True)

st.markdown("---")

# 3. CALCULADORA
st.markdown("### 🧮 SIMULADOR DE ESCENARIOS")

# Contenedor con borde sutil
with st.container():
    col_input1, col_input2, col_input3 = st.columns(3)
    
    with col_input1:
        start_date = st.date_input("FECHA INICIO", datetime.date(2018, 1, 1))
        amount = st.number_input("INVERSIÓN PERIÓDICA ($)", min_value=10, value=100)
    
    with col_input2:
        freq_option = st.selectbox("FRECUENCIA", ["Diaria", "Semanal", "Mensual"])
        day_param = 0
        if freq_option == "Semanal":
            days = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5, "Domingo":6}
            day_param = days[st.selectbox("DÍA SEMANA", list(days.keys()))]
        elif freq_option == "Mensual":
            day_param = st.number_input("DÍA DEL MES", 1, 31, 1)

    with col_input3:
        future_price = st.number_input("PRECIO FUTURO BTC ($)", min_value=10000.0, value=1000000.0, step=50000.0)
        future_date = st.date_input("FECHA OBJETIVO", datetime.date(2030, 12, 31))

calc_btn = st.button("CALCULAR IMPACTO PATRIMONIAL")

if calc_btn:
    with st.spinner('Analizando Blockchain...'):
        df_btc = get_bitcoin_data()
        
        if df_btc is None or df_btc.empty:
            st.error("Error de conexión con datos de mercado.")
        else:
            dca_table, total_btc, total_invested = calculate_dca(df_btc, start_date, amount, freq_option, day_param)
            
            if dca_table is None:
                st.error("No hay datos para esa fecha. Selecciona una fecha pasada.")
            else:
                # Cálculos
                val_futuro_bruto = total_btc * future_price
                
                # A: Trampa (Impuestos)
                ganancia = val_futuro_bruto - total_invested
                impuestos = ganancia * 0.25 if ganancia > 0 else 0
                neto_A = val_futuro_bruto - impuestos
                
                years = (future_date - start_date).days / 365.25
                cagr_A = calculate_cagr(total_invested, neto_A, years) * 100
                
                # B: Inconfiscable (0 impuestos)
                neto_B = val_futuro_bruto
                cagr_B = calculate_cagr(total_invested, neto_B, years) * 100
                
                diff = neto_B - neto_A

                # --- RESULTADOS CON DISEÑO HTML PURO ---
                st.markdown(f"""
                <div class="result-container">
                    <!-- TARJETA TRAMPA -->
                    <div class="card-trap">
                        <h3 style="color:#FF3333; margin:0;">🏛️ ESCENARIO A: LA TRAMPA</h3>
                        <p style="color:#aaa; font-size:0.9rem;">Exchange Centralizado + KYC</p>
                        
                        <div class="metric-label">Impuesto al "Patrimonio" (25%)</div>
                        <div class="metric-value highlight-red">-${impuestos:,.0f}</div>
                        
                        <div class="metric-label">Patrimonio Neto Final</div>
                        <div class="metric-value">${neto_A:,.0f}</div>
                        
                        <div style="margin-top:20px; border-top:1px solid #500; padding-top:10px;">
                            <span style="color:#aaa;">Rentabilidad:</span> 
                            <span style="color:#fff; font-weight:bold;">{cagr_A:.2f}% CAGR</span>
                        </div>
                    </div>

                    <!-- TARJETA SOBERANO -->
                    <div class="card-sov">
                        <h3 style="color:#00FF41; margin:0;">🛡️ ESCENARIO B: INCONFISCABLE</h3>
                        <p style="color:#aaa; font-size:0.9rem;">Autocustodia + Privacidad</p>
                        
                        <div class="metric-label">Impuestos Pagados</div>
                        <div class="metric-value highlight-green">$0</div>
                        
                        <div class="metric-label">Patrimonio Neto Final</div>
                        <div class="metric-value" style="color:#fff; text-shadow:0 0 10px #00FF41;">${neto_B:,.0f}</div>
                        
                        <div style="margin-top:20px; border-top:1px solid #050; padding-top:10px;">
                            <span style="color:#aaa;">Rentabilidad:</span> 
                            <span style="color:#fff; font-weight:bold;">{cagr_B:.2f}% CAGR</span>
                        </div>
                    </div>
                </div>
                
                <div style="background:#222; border:1px solid #444; padding:20px; margin-top:20px; border-radius:8px; text-align:center;">
                    <h2 style="color:#fff; font-size:1.5rem; margin:0;">
                        COSTO DE LA OBEDIENCIA: 
                        <span style="color:#FF3333; text-decoration:underline;">${diff:,.0f}</span>
                    </h2>
                    <p style="margin-top:10px; color:#ccc;">
                        Ese es el dinero que el sistema te confisca por no operar de manera privada.
                    </p>
                </div>
                """, unsafe_allow_html=True)

# 4. CAPTACIÓN
st.markdown("---")
st.markdown("### 🔓 ÚNETE A LA RESISTENCIA")
st.markdown("Recibe la guía paso a paso para ejecutar el **Escenario B** sin errores técnicos.")

with st.form("lead_form"):
    email = st.text_input("EMAIL", placeholder="tu@email.com")
    sub_btn = st.form_submit_button("ENVIARME LA ESTRATEGIA")
    
    if sub_btn and email:
        st.success(f"✅ Protocolo enviado a {email}. Revisa tu bandeja de entrada.")

# FOOTER
st.markdown("<br><br><div style='text-align:center; color:#444;'>INCONFISCABLE.XYZ v2.0</div>", unsafe_allow_html=True)
