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

# --- Forecasting & Visualization Integration ---

# Filter valid bills for model
valid_bills = df_bills.dropna(subset=['temp_media', 'consumo_kwh', 'valor_total'])
projection_data = None

if not df_weather.empty and not valid_bills.empty:
    # 1. Model Training
    valid_bills['efficiency_factor'] = valid_bills['consumo_kwh'] / valid_bills['temp_media']
    avg_factor = valid_bills['efficiency_factor'].mean()
    avg_cost_kwh = (valid_bills['valor_total'] / valid_bills['consumo_kwh']).mean()
    
    # 2. Hybrid Forecast Calculation
    try:
        from extract_weather import fetch_forecast, get_start_date
        
        # Determine Current Billing Cycle
        last_bill_date = valid_bills["data_leitura"].iloc[-1]
        cycle_start = last_bill_date + timedelta(days=1)
        cycle_end = cycle_start + timedelta(days=30)
        today = datetime.now()
        
        # Case A: Current date is within the cycle
        if today > cycle_start:
            # Days past: Get real weather from history
            days_past = (today - cycle_start).days
            days_future = (cycle_end - today).days
            
            # Fetch Forecast
            forecast_data = fetch_forecast(days=max(1, days_future + 5)) # Buffer
            
            past_temps = []
            future_temps = []
            
            # Get Past Temps (Real)
            mask = (df_weather.index >= cycle_start) & (df_weather.index < today)
            past_temps = df_weather.loc[mask, "temperature_2m_mean"].tolist()
            
            # Get Future Temps (Forecast)
            if forecast_data and 'daily' in forecast_data:
                f_dates = forecast_data['daily']['time']
                f_temps = forecast_data['daily']['temperature_2m_mean']
                
                for d, t in zip(f_dates, f_temps):
                    d_obj = datetime.strptime(d, "%Y-%m-%d")
                    if d_obj >= today and d_obj <= cycle_end:
                         future_temps.append(t)
            
            # Fill missing future days with average if forecast is short
            full_temps = past_temps + future_temps
            if len(full_temps) < 30:
                missing = 30 - len(full_temps)
                avg_so_far = sum(full_temps)/len(full_temps) if full_temps else 25.0
                full_temps.extend([avg_so_far] * missing)
                
            # Hybrid Average
            hybrid_avg_temp = sum(full_temps) / len(full_temps)
            
            # Predict
            pred_consumption = avg_factor * hybrid_avg_temp
            pred_cost = pred_consumption * avg_cost_kwh
            
            # Create Projection Data Entry
            next_month_date = cycle_start + timedelta(days=15)
            month_map = {
                1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
                5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
                9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
            }
            next_month_pt = month_map.get(next_month_date.month, "MÊS")
            next_month_str = f"{next_month_pt}/{next_month_date.year}"
            
            projection_data = {
                "mes_referencia": f"PROJEÇÃO {next_month_str}",
                "consumo_kwh": pred_consumption,
                "valor_total": pred_cost,
                "temp_media": hybrid_avg_temp,
                "type": "Projeção"
            }
            
    except Exception as e:
        st.warning(f"Erro na projeção: {e}")

# --- Charts (Updated) ---

st.subheader("Evolution: Consumption vs. Temperature")

# Prepare Chart Data
chart_df = df_bills.copy()
chart_df["type"] = "Real"

if projection_data:
    # Append projection
    proj_df = pd.DataFrame([projection_data])
    chart_df = pd.concat([chart_df, proj_df], ignore_index=True)

fig_combo = go.Figure()

# Bar: Consumption (Color by Type)
colors = ['#F5B041' if t == "Real" else '#AED6F1' for t in chart_df["type"]] # Orange for Real, Light Blue for Proj

fig_combo.add_trace(go.Bar(
    x=chart_df["mes_referencia"],
    y=chart_df["consumo_kwh"],
    name="Consumo (kWh)",
    marker_color=colors,
    text=[f"{v:.0f}" for v in chart_df["consumo_kwh"]], # Show values
    textposition='auto'
))

# Line: Temperature
if not df_weather.empty:
    fig_combo.add_trace(go.Scatter(
        x=chart_df["mes_referencia"],
        y=chart_df["temp_media"],
        name="Temp. Média (°C)",
        yaxis="y2",
        line=dict(color='#E74C3C', width=3, dash='dot') # Dashed line for effect
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

# --- Forecasting Card ---
if projection_data:
    st.markdown("---")
    st.subheader("🔮 Status do Mês Atual")
    c1, c2, c3 = st.columns(3)
    c1.metric("Projeção de Fechamento", f"R$ {projection_data['valor_total']:.2f}", delta="Estimado")
    c2.metric("Consumo Esperado", f"{projection_data['consumo_kwh']:.0f} kWh")
    c3.metric("Temp. Média Híbrida", f"{projection_data['temp_media']:.1f} °C", help="Média dos dias passados (real) + dias futuros (previsão)")
    st.caption(f"*Cálculo baseado no ciclo provável de 30 dias após a última leitura.")
