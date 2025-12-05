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

# --- ESTILOS CSS "CLEAN FINTECH" (FONDO BLANCO / PROFESIONAL) ---
st.markdown("""
<style>
    /* Importar fuente Inter (Estándar UI moderna) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

    /* --- RESET GENERAL PARA MODO CLARO --- */
    .stApp {
        background-color: #FFFFFF;
        font-family: 'Inter', sans-serif;
        color: #1f2937; /* Gris muy oscuro para texto */
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #111827;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    
    p, label, li {
        color: #4b5563 !important; /* Gris medio */
        font-size: 1rem;
        line-height: 1.6;
    }

    /* --- HEADER --- */
    .main-header {
        text-align: center;
        padding: 60px 0 40px 0;
        margin-bottom: 40px;
        background: linear-gradient(180deg, #F3F4F6 0%, #FFFFFF 100%);
        border-bottom: 1px solid #E5E7EB;
    }
    .main-title {
        font-size: 3rem;
        color: #111827;
        margin-bottom: 10px;
    }
    .subtitle {
        color: #6B7280;
        font-size: 1.25rem;
        font-weight: 300;
    }

    /* --- TARJETAS (CARD UI) --- */
    .feature-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        height: 100%;
        transition: all 0.2s ease;
    }
    .feature-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border-color: #D1D5DB;
    }
    .card-icon { font-size: 2rem; margin-bottom: 1rem; display: block; }
    .card-title { font-weight: 700; font-size: 1.1rem; margin-bottom: 0.5rem; color: #111827; }
    .card-text { font-size: 0.9rem; color: #6B7280; }

    /* --- INPUTS PERSONALIZADOS --- */
    div[data-baseweb="input"] {
        background-color: #F9FAFB !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #F9FAFB !important;
        border: 1px solid #E5E7EB !important;
        color: #111827 !important;
    }
    
    /* --- BOTÓN DE ACCIÓN --- */
    .stButton > button {
        background-color: #10B981; /* Verde Esmeralda */
        color: white;
        font-weight: 600;
        border: none;
        padding: 16px 0;
        border-radius: 8px;
        font-size: 1.1rem;
        box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.3);
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #059669;
        box-shadow: 0 6px 8px -1px rgba(16, 185, 129, 0.4);
        color: white;
    }

    /* --- RESULTADOS --- */
    .result-box {
        padding: 30px;
        border-radius: 16px;
        text-align: center;
        height: 100%;
    }
    .result-trap {
        background-color: #FEF2F2; /* Rojo muy pálido */
        border: 1px solid #FECACA;
        color: #991B1B;
    }
    .result-sov {
        background-color: #ECFDF5; /* Verde muy pálido */
        border: 1px solid #A7F3D0;
        color: #065F46;
    }
    .big-number {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 10px 0;
        letter-spacing: -1px;
    }
    .label-small {
        text-transform: uppercase;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 1px;
        opacity: 0.8;
    }

    /* --- FORMULARIO LEAD --- */
    .lead-section {
        background-color: #111827; /* Sección oscura para contraste al final */
        color: white;
        padding: 40px;
        border-radius: 16px;
        margin-top: 40px;
        text-align: center;
    }
    
    /* Ocultar elementos de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE LÓGICA (MANTIENEN LA ROBUSTEZ) ---
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
                except: btc_close = btc.iloc[:, 0]
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

# 1. HEADER
st.markdown("""
<div class="main-header">
    <div class="main-title">Inconfiscable.xyz</div>
    <div class="subtitle">Recupera la propiedad de tu esfuerzo. Escapa del control.</div>
</div>
""", unsafe_allow_html=True)

# 2. SECCIÓN VISUAL (CARDS LIMPIAS)
st.markdown("### El Camino a la Soberanía")
c1, c2, c3, c4 = st.columns(4)

def clean_card(icon, title, text):
    return f"""
    <div class="feature-card">
        <span class="card-icon">{icon}</span>
        <div class="card-title">{title}</div>
        <div class="card-text">{text}</div>
    </div>
    """

with c1: st.markdown(clean_card("🏛️", "La Trampa", "Exchanges centralizados. Tus datos y fondos están expuestos."), unsafe_allow_html=True)
with c2: st.markdown(clean_card("🔌", "La Ilusión", "Autocustodia vigilada. Tienen tus claves públicas."), unsafe_allow_html=True)
with c3: st.markdown(clean_card("🔨", "La Ruptura", "Tecnología de privacidad para romper el rastro on-chain."), unsafe_allow_html=True)
with c4: st.markdown(clean_card("🛡️", "Inconfiscable", "Soberanía total. Nadie sabe lo que tienes. Eres libre."), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 3. CALCULADORA
st.markdown("### 🧮 Calculadora de Impacto Patrimonial")
st.write("Compara el resultado de invertir en el sistema tradicional vs. el sistema soberano.")

with st.container():
    # Usamos st.columns para un layout de inputs limpio
    col_input1, col_input2, col_input3 = st.columns(3)
    
    with col_input1:
        start_date = st.date_input("Fecha Inicio", datetime.date(2018, 1, 1))
        amount = st.number_input("Inversión Periódica ($)", min_value=10, value=100)
    
    with col_input2:
        freq_option = st.selectbox("Frecuencia", ["Diaria", "Semanal", "Mensual"])
        day_param = 0
        if freq_option == "Semanal":
            days = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5, "Domingo":6}
            day_param = days[st.selectbox("Día Semana", list(days.keys()))]
        elif freq_option == "Mensual":
            day_param = st.number_input("Día del Mes", 1, 31, 1)

    with col_input3:
        future_price = st.number_input("Precio Futuro BTC ($)", min_value=10000.0, value=1000000.0, step=50000.0)
        future_date = st.date_input("Fecha Objetivo", datetime.date(2030, 12, 31))

st.markdown("<br>", unsafe_allow_html=True)
calc_btn = st.button("CALCULAR MI FUTURO")

if calc_btn:
    with st.spinner('Procesando datos históricos...'):
        df_btc = get_bitcoin_data()
        
        if df_btc is None or df_btc.empty:
            st.error("⚠️ Error de conexión. No se pudieron descargar los datos de mercado.")
        else:
            dca_table, total_btc, total_invested = calculate_dca(df_btc, start_date, amount, freq_option, day_param)
            
            if dca_table is None:
                st.error("⚠️ La fecha seleccionada no tiene datos históricos. Elige una fecha pasada.")
            else:
                # Cálculos
                val_futuro_bruto = total_btc * future_price
                
                # A: Trampa
                ganancia = val_futuro_bruto - total_invested
                impuestos = ganancia * 0.25 if ganancia > 0 else 0
                neto_A = val_futuro_bruto - impuestos
                years = (future_date - start_date).days / 365.25
                cagr_A = calculate_cagr(total_invested, neto_A, years) * 100
                
                # B: Inconfiscable
                neto_B = val_futuro_bruto
                cagr_B = calculate_cagr(total_invested, neto_B, years) * 100
                diff = neto_B - neto_A

                # --- RESULTADOS VISUALES LIMPIOS ---
                res_c1, res_c2 = st.columns(2)

                with res_c1:
                    st.markdown(f"""
                    <div class="result-box result-trap">
                        <div class="label-small" style="color:#991B1B;">Escenario A: La Trampa</div>
                        <h3>Exchange Centralizado</h3>
                        <div style="margin: 20px 0; border-top: 1px dashed #FECACA; border-bottom: 1px dashed #FECACA; padding: 15px 0;">
                            <div class="label-small">Impuestos (25%)</div>
                            <div style="font-size: 1.5rem; font-weight: 600;">-${impuestos:,.0f}</div>
                        </div>
                        <div class="label-small">Patrimonio Final</div>
                        <div class="big-number">${neto_A:,.0f}</div>
                        <div style="font-size:0.9rem;">Rentabilidad Real: <strong>{cagr_A:.2f}%</strong></div>
                    </div>
                    """, unsafe_allow_html=True)

                with res_c2:
                    st.markdown(f"""
                    <div class="result-box result-sov">
                        <div class="label-small" style="color:#065F46;">Escenario B: Inconfiscable</div>
                        <h3>Soberanía & Privacidad</h3>
                        <div style="margin: 20px 0; border-top: 1px dashed #A7F3D0; border-bottom: 1px dashed #A7F3D0; padding: 15px 0;">
                            <div class="label-small">Impuestos (No Venta)</div>
                            <div style="font-size: 1.5rem; font-weight: 600;">$0</div>
                        </div>
                        <div class="label-small">Patrimonio Final</div>
                        <div class="big-number" style="color:#059669">${neto_B:,.0f}</div>
                        <div style="font-size:0.9rem;">Rentabilidad Real: <strong>{cagr_B:.2f}%</strong></div>
                    </div>
                    """, unsafe_allow_html=True)

                # Caja de conclusión
                st.markdown(f"""
                <div style="background-color: #111827; color: white; padding: 20px; border-radius: 12px; margin-top: 20px; text-align: center;">
                    <h3 style="color: white; margin: 0;">EL PRECIO DE NO SER SOBERANO: <span style="color: #EF4444;">${diff:,.0f}</span></h3>
                    <p style="color: #9CA3AF; margin-top: 5px; font-size: 0.9rem;">
                        Dinero entregado al sistema por operar de forma visible. <br>
                        En el escenario B, usas tus {total_btc:.4f} BTC como colateral para obtener liquidez sin vender.
                    </p>
                </div>
                """, unsafe_allow_html=True)

# 4. CAPTACIÓN (Diseño oscuro para contraste final)
st.markdown("<br><br>", unsafe_allow_html=True)

st.markdown("""
<div class="lead-section">
    <h2 style="color:white; margin-bottom: 10px;">Entra en la Madriguera</h2>
    <p style="color:#D1D5DB; max-width: 600px; margin: 0 auto 20px auto;">
        La teoría está bien, pero la ejecución lo es todo. Te enviaré el paso a paso exacto para:
        <br>1. Crear tu banco. 2. Comprar sin KYC. 3. Borrar tu huella.
    </p>
</div>
""", unsafe_allow_html=True)

# Formulario (integrado visualmente)
with st.form("lead_form"):
    col_email, col_submit = st.columns([3, 1])
    with col_email:
        email = st.text_input("Email", placeholder="tu@email.com", label_visibility="collapsed")
    with col_submit:
        sub_btn = st.form_submit_button("RECIBIR LA GUÍA")
    
    if sub_btn and email:
        st.success(f"Protocolo enviado a {email}.")

# FOOTER
st.markdown("<br><div style='text-align:center; color:#9CA3AF; font-size: 0.8rem;'>© 2025 Inconfiscable.xyz</div>", unsafe_allow_html=True)
