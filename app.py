import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

# ------------------------------
# Utility Functions
# ------------------------------

def get_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_volume_spike(data):
    recent_volume = data['Volume'][-1]
    avg_volume = data['Volume'].rolling(window=20).mean()[-1]
    return recent_volume > 1.5 * avg_volume

def get_short_float(symbol):
    url = f"https://www.nasdaq.com/market-activity/stocks/{symbol.lower()}/short-interest"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        value = soup.find('span', {'class': 'symbol-page-header__data'}).text.strip('%')
        return float(value)
    except:
        return None

def check_earnings_surprise(ticker):
    try:
        earnings = ticker.earnings_dates
        if earnings is not None and not earnings.empty:
            latest = earnings.iloc[0]
            surprise = latest.get('Surprise(%)', 0)
            return surprise and float(surprise) > 0
    except:
        return False
    return False

def check_news_catalyst(symbol):
    # Very basic check — for demo purposes
    query = f"{symbol} insider buying OR news"
    url = f"https://www.google.com/search?q={query}"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        return "insider" in response.text.lower() or "buying" in response.text.lower()
    except:
        return False

def analyze_stock(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="3mo")
        if data.empty or len(data) < 20:
            return None
        
        rsi = get_rsi(data).iloc[-1]
        vol_spike = get_volume_spike(data)
        short_float = get_short_float(symbol)
        earnings_surprise = check_earnings_surprise(ticker)
        news_catalyst = check_news_catalyst(symbol)

        if (
            rsi > 60 and
            vol_spike and
            short_float and short_float > 10 and
            earnings_surprise and
            news_catalyst
        ):
            return {
                "Symbol": symbol,
                "RSI": round(rsi, 2),
                "Volume Spike": vol_spike,
                "Short Float %": short_float,
                "Earnings Surprise": earnings_surprise,
                "News Catalyst": news_catalyst
            }
        return None
    except Exception as e:
        return None

# ------------------------------
# Streamlit UI
# ------------------------------

st.title("📈 Short Squeeze Predictor")

uploaded_file = st.file_uploader("Upload your Excel file with stock symbols (one sheet per list)", type=["xlsx"])

if uploaded_file:
    stock_sheets = pd.ExcelFile(uploaded_file).sheet_names
    selected_sheet = st.selectbox("Select Stock List", stock_sheets)
    
    analyze_button = st.button("Analyze Stocks")
    
    if analyze_button:
        try:
            stock_df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)
            if 'Symbol' not in stock_df.columns:
                st.error("❌ Error: The selected sheet doesn't have a 'Symbol' column.")
            else:
                symbols = stock_df['Symbol'].dropna().tolist()

                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, symbol in enumerate(symbols):
                    status_text.text(f"🔍 Analyzing {symbol} ({i+1}/{len(symbols)})...")
                    result = analyze_stock(symbol)
                    if result:
                        results.append(result)
                    progress_bar.progress((i + 1) / len(symbols))
                
                if results:
                    st.success("✅ Analysis Complete")
                    result_df = pd.DataFrame(results)
                    st.dataframe(result_df)
                    st.download_button("📥 Download Results", result_df.to_csv(index=False), file_name="short_squeeze_candidates.csv")
                else:
                    st.warning("⚠️ No stocks matched the criteria.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")
