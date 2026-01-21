# ⚡ Monitor de Contas de Luz & Clima (Light RJ)

Este projeto é uma ferramenta de **inteligência de dados para contas de energia**.

O objetivo é automatizar a leitura de faturas da **Light RJ**, extrair dados de consumo e valores, e cruzar essas informações com **dados históricos de temperatura**. Isso permite visualizar claramente se os aumentos na conta de luz estão correlacionados com ondas de calor.

## 🚀 Funcionalidades

- **Extração Automática de PDFs**: Usa a IA do **Google Gemini** para ler faturas em PDF e extrair:
    - Valor Total (R$)
    - Consumo (kWh)
    - Bandeira Tarifária (Verde, Amarela, Vermelha) e Adicionais
    - Datas de Leitura e Vencimento
- **Monitoramento Climático**: Busca automaticamente o histórico de temperatura diária (Mínima, Máxima e Média) para a região (configurado para Ricardo de Albuquerque, RJ) usando a API **Open-Meteo**.
- **Processamento em Lote**: Processa múltiplas faturas de uma só vez e mantém uma base de dados histórica (`json`), evitando reprocessamentos.
- **Dashboard Interativo**: Painel visual feito em **Streamlit** que exibe:
    - Gráfico de Evolução (Consumo x Temperatura Média)
    - Gráfico de Dispersão (Correlação de Custo x Temperatura)
    - Indicadores de Custo Anual e Médias.
    - **Previsão de Gastos (Beta)**: Estima o valor da próxima fatura com base na previsão do tempo e no seu histórico de consumo.
    - Botão para atualizar dados diretamente pela interface.

## 🛠️ Instalação e Configuração

### 1. Pré-requisitos
- Python instalado.
- Uma chave de API do Google Gemini (Google AI Studio).

### 2. Instalação
Clone o projeto e instale as dependências:
```bash
pip install -r requirements.txt
# Ou instale manualmente:
pip install google-generativeai python-dotenv streamlit plotly pandas requests
```

### 3. Configuração da API
Crie um arquivo `.env` na raiz do projeto e adicione sua chave:
```toml
GEMINI_API_KEY="sua_chave_aqui"
```

## 🖥️ Como Usar

### 1. Adicionar Faturas
Coloque seus arquivos PDF das contas de luz na pasta:
```
/Faturas
```

### 2. Executar o Dashboard
A forma mais fácil de rodar é clicando duas vezes no arquivo:
👉 **`run_dashboard.bat`**

Ou via terminal:
```bash
streamlit run dashboard.py
```

### 3. Atualizar Dados
No Dashboard, abra a barra lateral e clique em **"Atualizar Dados"**. O sistema irá:
1.  Ler os novos PDFs na pasta `Faturas`.
2.  Buscar os dados de temperatura recentes.
3.  Atualizar os gráficos automaticamente.

## 📂 Estrutura do Projeto
- `dashboard.py`: Aplicação principal do Streamlit.
- `extract_bill_data.py`: Script de extração de dados dos PDFs (Gemini).
- `extract_weather.py`: Script de extração de dados climáticos (Open-Meteo).
- `bills_history.json`: Banco de dados local das faturas processadas.
- `weather_history.json`: Banco de dados local do histórico de clima.

---

## 🎓 Sobre

Este projeto foi desenvolvido com o auxílio do **Google Antigravity** e seus agentes inteligentes, como parte de um estudo sobre desenvolvimento assistido por IA e automação.