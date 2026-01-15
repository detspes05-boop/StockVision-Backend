import os
from dotenv import load_dotenv
import yfinance as yf
from sqlalchemy import create_engine
import pandas as pd
import google.generativeai as genai
import time

# --- 1. LOAD RAHASIA ---
load_dotenv()
DB_URL = os.getenv("DB_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- 2. SETUP GEMINI AI ---
genai.configure(api_key=GEMINI_API_KEY)

# GUNAKAN GEMINI 1.5 FLASH (Kuota Gratis Paling Besar)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3. RSI ---
def calculate_rsi(series, period=14):
    delta = series.diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- 4. AI ANALYSIS ---
def get_ai_analysis(ticker, price, rsi):
    print(f"   ...Meminta pendapat Gemini soal {ticker}...")
    prompt = f"""
    Bertindaklah sebagai Analis Saham.
    Saham: {ticker} | Harga: {price} | RSI: {rsi:.2f}
    Berikan komentar 1 kalimat singkat (Maks 10 kata).
    Jika RSI < 40 katakan 'Potensi BUY'. Jika RSI > 65 katakan 'Potensi SELL'.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Gagal analisa AI: {e}"

# --- 5. SCANNER UTAMA ---
def scan_market():
    print("--- STOCKVISION AI: STARTED (SAFE MODE) ---")
    
    if not DB_URL:
        print("[ERROR] DB_URL Kosong!")
        return

    try:
        engine = create_engine(DB_URL)
    except Exception as e:
        print(f"[FATAL] Koneksi DB Gagal: {e}")
        return

    daftar_saham = ['BBRI.JK', 'BBCA.JK', 'GOTO.JK', 'ANTM.JK', 'ASII.JK']
    
    for ticker in daftar_saham:
        print(f"\n1. Mengambil Data {ticker}...")
        try:
            df = yf.download(ticker, period='3mo', progress=False)
            if len(df) < 20: continue
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df['RSI'] = calculate_rsi(df['Close'])
            last_rsi = float(df['RSI'].iloc[-1])
            last_price = float(df['Close'].iloc[-1])
            
            pattern_label = f"RSI: {last_rsi:.1f}"
            if last_rsi < 40: pattern_label = "AI SIGNAL: BUY"
            elif last_rsi > 65: pattern_label = "AI SIGNAL: SELL"
            else: pattern_label = "AI SIGNAL: NEUTRAL"

            # Tanya Gemini
            ai_story = get_ai_analysis(ticker, last_price, last_rsi)
            print(f"   -> [AI SAYS]: {ai_story}")

            # Simpan
            data_to_save = pd.DataFrame({
                'ticker': [ticker],
                'pattern_name': [pattern_label],
                'price': [last_price],
                'story': [ai_story]
            })
            
            data_to_save.to_sql('detected_patterns', engine, if_exists='append', index=False)
            print("   -> [DATABASE] Data tersimpan!")
            
            # --- PENTING: Istirahat 10 Detik agar tidak error 429 ---
            print("   ...Istirahat 10 detik (Anti-Banned)...")
            time.sleep(10) 

        except Exception as e:
            print(f"   [ERROR] {ticker}: {e}")
            time.sleep(10) # Tetap istirahat walaupun error

if __name__ == "__main__":
    scan_market()