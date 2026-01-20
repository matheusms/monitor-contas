import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page Config
st.set_page_config(page_title="Monitor de Contas Light RJ", layout="wide")
st.title("⚡ Monitor de Contas de Luz & Clima 🌤️")

# --- Sidebar ---
with st.sidebar:
    st.header("Opções")
    if st.button("🔄 Atualizar Dados"):
        with st.spinner("Processando novas faturas e clima..."):
            try:
                # Lazy import to avoid circular dependencies or startup issues
                from extract_bill_data import process_all_faturas
                from extract_weather import update_weather_data
                
                # Run updates
                new_bills = process_all_faturas()
                weather_updated = update_weather_data()
                
                # Clear cache to reload new JSONs
                st.cache_data.clear()
                
                success_msg = f"Sucesso! {new_bills} nova(s) fatura(s) processada(s)."
                if weather_updated:
                    success_msg += " Clima atualizado."
                st.success(success_msg)
                
                # Rerun to show new data
                st.rerun()
                
            except Exception as e:
                st.error(f"Erro ao atualizar: {e}")

# --- Data Loading ---
@st.cache_data
def load_data():
    # Load Bills
    bills_data = []
    try:
        with open("bills_history.json", "r", encoding="utf-8") as f:
            bills_data = json.load(f)
    except FileNotFoundError:
        st.error("Arquivo bills_history.json não encontrado.")
        return pd.DataFrame(), pd.DataFrame()

    # Load Weather
    weather_data_raw = {}
    try:
        with open("weather_history.json", "r", encoding="utf-8") as f:
            weather_data_raw = json.load(f)
    except FileNotFoundError:
        st.warning("Arquivo weather_history.json não encontrado. Dados climáticos não serão exibidos.")
    
    # Process Weather to DataFrame
    weather_df = pd.DataFrame()
    if weather_data_raw:
        weather_df = pd.DataFrame(weather_data_raw.get("daily", {}))
        weather_df["time"] = pd.to_datetime(weather_df["time"])
        weather_df.set_index("time", inplace=True)

    # Process Bills to DataFrame & Correlate
    processed_bills = []
    for bill in bills_data:
        # Convert date
        try:
            read_date = datetime.strptime(bill["leitura_atual"], "%d/%m/%Y")
        except:
            continue
            
        bill["data_leitura"] = read_date
        
        # Calculate Avg Temp for previous 30 days
        avg_temp = None
        if not weather_df.empty:
            start_date = read_date - timedelta(days=30)
            mask = (weather_df.index >= start_date) & (weather_df.index <= read_date)
            period_temps = weather_df.loc[mask, "temperature_2m_mean"]
            if not period_temps.empty:
                avg_temp = period_temps.mean()
        
        bill["temp_media"] = avg_temp
        processed_bills.append(bill)
        
    df_bills = pd.DataFrame(processed_bills)
    
    # Sorting
    if not df_bills.empty:
        df_bills.sort_values("data_leitura", inplace=True)

    return df_bills, weather_df

df_bills, df_weather = load_data()

if df_bills.empty:
    st.write("Sem dados para exibir.")
    st.stop()

# --- KPI Metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Gasto Total", f"R$ {df_bills['valor_total'].sum():.2f}")
col2.metric("Consumo Total", f"{df_bills['consumo_kwh'].sum()} kWh")
col3.metric("Média Mensal", f"R$ {df_bills['valor_total'].mean():.2f}")
col4.metric("Temp. Média Geral", f"{df_bills['temp_media'].mean():.1f} °C" if 'temp_media' in df_bills else "N/A")

# --- Charts ---

# 1. Timeline Chart (Dual Axis)
st.subheader("Evolution: Consumption vs. Temperature")
fig_combo = go.Figure()

# Bar: Consumption
fig_combo.add_trace(go.Bar(
    x=df_bills["mes_referencia"],
    y=df_bills["consumo_kwh"],
    name="Consumo (kWh)",
    marker_color='#F5B041'
))

# Line: Temperature
if not df_weather.empty:
    fig_combo.add_trace(go.Scatter(
        x=df_bills["mes_referencia"],
        y=df_bills["temp_media"],
        name="Temp. Média (°C)",
        yaxis="y2",
        line=dict(color='#E74C3C', width=3)
    ))

fig_combo.update_layout(
    yaxis=dict(title="Consumo (kWh)"),
    yaxis2=dict(title="Temperatura (°C)", overlaying="y", side="right"),
    legend=dict(x=0, y=1.2, orientation="h")
)
st.plotly_chart(fig_combo, use_container_width=True)

# 2. Scatter Plot Correlation
st.subheader("Correlation: Temperature vs. Cost")
if not df_weather.empty and 'temp_media' in df_bills.columns:
    # Map flags to colors
    color_map = {
        "Verde": "green",
        "Amarela": "yellow",
        "Vermelha": "red",
        "Amarela e Vermelha": "orange" 
    }
    
    # Handle cases where flag might be null or mixed case
    df_bills['bandeira_tarifaria'] = df_bills['bandeira_tarifaria'].fillna('Verde')
    
    fig_scatter = px.scatter(
        df_bills, 
        x="temp_media", 
        y="valor_total", 
        size="consumo_kwh", 
        color="bandeira_tarifaria",
        hover_data=["mes_referencia"],
        title="Impacto da Temperatura no Valor da Conta",
        labels={"temp_media": "Temperatura Média (°C)", "valor_total": "Valor da Conta (R$)"}
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

# --- Detailed Data ---
with st.expander("Ver Dados Detalhados"):
    st.dataframe(df_bills[["mes_referencia", "valor_total", "consumo_kwh", "bandeira_tarifaria", "temp_media", "vencimento"]])
