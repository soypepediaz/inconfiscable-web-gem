import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import datetime
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Inconfiscable.xyz",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS PERSONALIZADOS (MODO DARK/HACKER) ---
st.markdown("""
<style>
    /* Ocultar elementos de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebar"] {display: none;}
    
    /* Fondo y tipografía */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #00ff41; /* Verde Hacker */
        font-weight: bold;
    }
    
    /* Botones */
    .stButton>button {
        color: #0e1117;
        background-color: #00ff41;
        border: none;
        border-radius: 5px;
        font-weight: bold;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #00cc33;
        color: white;
        box-shadow: 0 0 10px #00ff41;
    }
    
    /* Inputs */
    .stDateInput, .stNumberInput, .stSelectbox {
        color: white;
    }
    
    /* Cajas de métricas */
    div[data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 10px;
        border-radius: 5px;
    }
    label[data-testid="stMetricLabel"] {
        color: #00ff41 !important;
    }
    
    /* Banner de alerta */
    .alert-box {
        padding: 20px;
        background-color: #2a0000;
        border-left: 5px solid #ff3333;
        margin-bottom: 25px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN MOOSEND (CAMBIAR AQUÍ TU URL DE ACCIÓN) ---
MOOSEND_ACTION_URL = "https://tu-cuenta.moosend.com/subscribe/..." 
MOOSEND_FIELD_ID = "field_email" 

# --- FUNCIONES DE LÓGICA ---

@st.cache_data
def get_bitcoin_data():
    """Descarga el histórico de Bitcoin con manejo robusto de errores y formatos."""
    try:
        # Descarga forzando un rango amplio
        btc = yf.download("BTC-USD", start="2009-01-01", progress=False)
        
        if btc is None or btc.empty:
            return None

        # --- CORRECCIÓN DE COLUMNAS (Fix para yfinance reciente) ---
        # yfinance puede devolver MultiIndex (Price, Ticker) o simplemente columnas
        # El objetivo es aislar la columna 'Close'
        
        # Si es MultiIndex (ej: niveles Price y Ticker)
        if isinstance(btc.columns, pd.MultiIndex):
            # Intentar extraer por nivel 'Price' si existe
            try:
                # Intenta sacar el nivel 0 si se llama 'Close' o 'Price'
                btc_close = btc.xs('Close', axis=1, level=0)
            except KeyError:
                try:
                    # A veces el nivel 0 es el Ticker y el nivel 1 es 'Close'
                    btc_close = btc.xs('Close', axis=1, level=1)
                except KeyError:
                    # Si falla, busca cualquier columna que contenga 'Close' en su nombre
                    cols = [c for c in btc.columns.get_level_values(0) if 'Close' in str(c)]
                    if cols:
                        btc_close = btc[cols[0]]
                    else:
                        # Fallback extremo: Primera columna numérica
                        btc_close = btc.iloc[:, 0]
            
            # Convertir a DataFrame simple si salió como Series
            if isinstance(btc_close, pd.Series):
                btc_close = btc_close.to_frame()
            
            btc = btc_close

        # Si es DataFrame plano (no MultiIndex)
        else:
            if 'Close' in btc.columns:
                btc = btc[['Close']]
            elif 'Adj Close' in btc.columns:
                btc = btc[['Adj Close']]
            else:
                # Quedarse con la primera columna si no encuentra nombres estándar
                btc = btc.iloc[:, 0:1]

        # Renombrar columna final para estandarizar
        btc.columns = ['BTC-USD']
        
        # Limpieza de índice temporal (Timezone naive)
        btc.index = pd.to_datetime(btc.index)
        if btc.index.tz is not None:
            btc.index = btc.index.tz_localize(None)
            
        return btc

    except Exception as e:
        # Log del error en consola (invisible al usuario) para debug
        print(f"Error descargando datos: {e}")
        return None

def calculate_dca(df, start_date, amount, frequency, day_param):
    """Calcula la estrategia DCA basada en fechas históricas."""
    # Asegurar formato de fecha
    start_ts = pd.to_datetime(start_date)
    
    # Filtrar desde fecha de inicio
    mask = (df.index >= start_ts)
    dca_df = df.loc[mask].copy()
    
    # Si no hay datos después del filtro (fecha muy futura o dataframe vacío)
    if dca_df.empty:
        return None, 0, 0
    
    # Lógica de Frecuencia
    target_dates = []
    
    if frequency == "Diaria":
        target_dates = dca_df.index
    elif frequency == "Semanal":
        # day_param: 0=Lunes, 6=Domingo
        target_dates = dca_df[dca_df.index.dayofweek == day_param].index
    elif frequency == "Mensual":
        # Agrupar por Año-Mes
        # day_param: 1 a 31
        grouped = dca_df.groupby([dca_df.index.year, dca_df.index.month])
        for _, group in grouped:
            try:
                # Intentar seleccionar el día específico
                specific_date = group[group.index.day == day_param]
                if not specific_date.empty:
                    target_dates.append(specific_date.index[0])
                else:
                    # Si no existe (ej: 31 feb), coger el último del mes
                    target_dates.append(group.index[-1])
            except:
                pass
        target_dates = pd.DatetimeIndex(target_dates)

    # Filtrar solo días de compra
    dca_df = dca_df.loc[dca_df.index.isin(target_dates)].copy()
    
    if dca_df.empty:
        return None, 0, 0

    # Ejecutar compras
    dca_df['Invested_Fiat'] = amount
    dca_df['BTC_Bought'] = dca_df['Invested_Fiat'] / dca_df['BTC-USD']
    dca_df['Total_BTC'] = dca_df['BTC_Bought'].cumsum()
    dca_df['Total_Invested'] = dca_df['Invested_Fiat'].cumsum()
    
    total_btc = dca_df['Total_BTC'].iloc[-1]
    total_invested = dca_df['Total_Invested'].iloc[-1]
    
    return dca_df, total_btc, total_invested

def calculate_cagr(start_value, end_value, num_years):
    if start_value <= 0 or num_years <= 0:
        return 0
    return (end_value / start_value)**(1 / num_years) - 1

# --- UI PRINCIPAL ---

# HEADER
st.title("🛡️ INCONFISCABLE.XYZ")
st.markdown("### Escapa del control. Recupera tu soberanía.")
st.markdown("---")

# SECCIÓN 1: EL CAMINO (INFOGRAFÍA INTERACTIVA)
st.subheader("El Camino Hacia Lo Inconfiscable")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.error("🏛️ 1. LA TRAMPA")
    st.write("**Exchanges Centralizados.**")
    st.caption("Trazabilidad 100%. Papá Estado sabe lo que tienes. Tus fondos pueden ser congelados con un clic.")

with col2:
    st.warning("🔌 2. LA ILUSIÓN")
    st.write("**Autocustodia (a medias).**")
    st.caption("Tienes las llaves, pero saben que las tienes. La cadena de bloques pública te delata si no anonimizas.")

with col3:
    st.info("🔨 3. LA RUPTURA")
    st.write("**Romper el rastro.**")
    st.caption("Intercambio por tokens anónimos o herramientas de privacidad. Aquí es donde te vuelves invisible.")

with col4:
    st.success("🛡️ 4. INCONFISCABLE")
    st.write("**Soberanía Total.**")
    st.caption("Activos descentralizados, autocustodiados y privados. Nadie puede confiscarlos. Eres tu propio banco.")

st.markdown("---")

# SECCIÓN 2: LA CALCULADORA DE LA VERDAD
st.header("🧮 Simulador: La Trampa vs. El Soberano")
st.markdown("""
Esta herramienta te muestra el costo real de permanecer en el sistema tradicional frente a la libertad financiera.
Introduce tus datos para simular una estrategia **DCA (Dollar Cost Averaging)**.
""")

# --- INPUTS ---
with st.container():
    c1, c2, c3 = st.columns(3)
    
    with c1:
        start_date = st.date_input("1) Fecha de inicio inversión", datetime.date(2018, 1, 1))
        amount = st.number_input("2) Cantidad periódica ($)", min_value=10, value=100)
    
    with c2:
        freq_option = st.selectbox("3) Frecuencia de recompra", ["Diaria", "Semanal", "Mensual"])
        
        day_param = 0
        if freq_option == "Semanal":
            days_week = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5, "Domingo":6}
            d_sel = st.selectbox("Día de la semana", list(days_week.keys()))
            day_param = days_week[d_sel]
        elif freq_option == "Mensual":
            day_param = st.number_input("Día del mes", min_value=1, max_value=31, value=1)

    with c3:
        future_price = st.number_input("4) Precio Futuro Bitcoin ($)", min_value=10000.0, value=1000000.0, step=10000.0)
        future_date = st.date_input("Fecha estimada del precio", datetime.date(2030, 12, 31))

# --- BOTÓN DE CÁLCULO ---
if st.button("CALCULAR MI FUTURO INCONFISCABLE", type="primary"):
    
    with st.spinner('Descargando blockchain... Calculando escenarios...'):
        # 1. Obtener Datos
        df_btc = get_bitcoin_data()
        
        # Validación de descarga
        if df_btc is None or df_btc.empty:
            st.error("⚠️ Error técnico: No se pudieron descargar los datos históricos de Bitcoin. Por favor, verifica tu conexión a internet o intenta más tarde.")
        else:
            try:
                # 2. Calcular DCA Histórico
                dca_table, total_btc, total_invested = calculate_dca(df_btc, start_date, amount, freq_option, day_param)
                
                if dca_table is None:
                    # Mensaje específico si la fecha es demasiado futura para los datos que tenemos
                    last_date_available = df_btc.index[-1].strftime('%Y-%m-%d')
                    st.error(f"⚠️ No hay datos suficientes para la fecha seleccionada. Datos disponibles hasta: {last_date_available}. Asegúrate de que la fecha de inicio no sea futura.")
                else:
                    # 3. Proyecciones
                    current_price = df_btc['BTC-USD'].iloc[-1]
                    current_value = total_btc * current_price 
                    future_gross_value = total_btc * future_price # Valor a futuro
                    
                    # --- ESCENARIO A: LA TRAMPA ---
                    # Venta con KYC, pagando impuestos
                    profit_A = future_gross_value - total_invested
                    tax_rate = 0.25
                    tax_paid = profit_A * tax_rate if profit_A > 0 else 0
                    net_result_A = future_gross_value - tax_paid
                    
                    # CAGR A
                    days_diff = (future_date - start_date).days
                    years_diff = days_diff / 365.25 if days_diff > 0 else 1
                    cagr_A = calculate_cagr(total_invested, net_result_A, years_diff) * 100

                    # --- ESCENARIO B: INCONFISCABLE ---
                    # Sin venta (Pignoración / Préstamo) o Privado. 0 impuestos realizados.
                    net_result_B = future_gross_value
                    cagr_B = calculate_cagr(total_invested, net_result_B, years_diff) * 100
                    
                    # Diferencia
                    difference = net_result_B - net_result_A

                    # --- RESULTADOS VISUALES ---
                    st.markdown("### 📊 Resultados Comparativos")
                    
                    res_col1, res_col2 = st.columns(2)
                    
                    with res_col1:
                        st.markdown("""<div class='alert-box' style='background-color: #330000; border-left: 5px solid red;'>
                        <h3 style='color:red'>ESCENARIO A: LA TRAMPA</h3>
                        <p>Exchange Centralizado + KYC + Hacienda</p>
                        </div>""", unsafe_allow_html=True)
                        st.metric("Total Invertido", f"${total_invested:,.2f}")
                        st.metric("Impuestos a Pagar (25%)", f"${tax_paid:,.2f}", delta="-Robo del estado", delta_color="inverse")
                        st.metric("Patrimonio Neto Final", f"${net_result_A:,.2f}")
                        st.metric("Rentabilidad Efectiva (CAGR)", f"{cagr_A:.2f}%")

                    with res_col2:
                        st.markdown("""<div class='alert-box' style='background-color: #003300; border-left: 5px solid #00ff41;'>
                        <h3 style='color:#00ff41'>ESCENARIO B: INCONFISCABLE</h3>
                        <p>Sin KYC + Autocustodia + Pignoración</p>
                        </div>""", unsafe_allow_html=True)
                        st.metric("Total Acumulado BTC", f"₿ {total_btc:.6f}")
                        st.metric("Impuestos (0% - No Venta)", "$0.00", delta="+Libertad", delta_color="normal")
                        st.metric("Patrimonio Neto Final", f"${net_result_B:,.2f}")
                        st.metric("Rentabilidad Efectiva (CAGR)", f"{cagr_B:.2f}%")

                    st.markdown("---")
                    st.markdown(f"### 💡 El Costo de la Sumisión: <span style='color:#ff3333; font-size: 1.2em; font-weight:bold;'>${difference:,.2f}</span> perdidos para siempre.", unsafe_allow_html=True)
                    
                    st.info(f"""
                    **Análisis:**
                    En el **Escenario Inconfiscable**, al no vender tus bitcoins, no generas un hecho imponible. 
                    Mantienes el 100% de tu poder adquisitivo y puedes utilizar tus {total_btc:.4f} BTC como colateral 
                    para obtener liquidez sin pedir permiso y sin pagar impuestos sobre la ganancia de capital.
                    """)
            
            except Exception as e:
                st.error(f"Ocurrió un error inesperado en el cálculo: {e}")

# --- SECCIÓN DE CAPTACIÓN (MOOSEND) ---
st.markdown("---")
st.header("🔓 La Madriguera de la Inconfiscabilidad")
st.markdown("""
¿Quieres saber **CÓMO** ejecutar los 4 pasos?
1. Configurar banco autocustodio.
2. Comprar On-chain.
3. Romper trazabilidad (Anonimizar).
4. DCA Descentralizado recurrente.

**Te enviaré la secuencia exacta por email. Nada de teoría, pura acción.**
""")

with st.form("lead_form"):
    st.write("Únete a la resistencia:")
    
    email = st.text_input("Tu mejor email", placeholder="nombre@ejemplo.com")
    submitted = st.form_submit_button("QUIERO SER INCONFISCABLE")
    
    if submitted:
        if email:
            st.markdown(f"""
            <div style="background-color: #00ff41; color: black; padding: 10px; border-radius: 5px;">
                ✅ <strong>Solicitud recibida para: {email}</strong><br>
                Revisa tu bandeja de entrada. El primer paso hacia la libertad acaba de comenzar.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("Por favor, introduce un email válido.")

# --- FOOTER ---
st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; color: #555;">
    <small>Inconfiscable.xyz - La propiedad privada definitiva.</small>
</div>
""", unsafe_allow_html=True)
