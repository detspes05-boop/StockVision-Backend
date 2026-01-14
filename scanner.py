import os
from dotenv import load_dotenv
import yfinance as yf
from sqlalchemy import create_engine
import pandas as pd
import google.generativeai as genai
import time

# --- 1. LOAD RAHASIA DARI FILE .ENV ---
load_dotenv() # Membaca file .env

# Ambil password & API Key dari lingkungan aman
DB_URL = os.getenv("DB_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- 2. SETUP GEMINI AI ---
genai.configure(api_key=GEMINI_API_KEY)

# Kita gunakan logika 'try-except' untuk memilih model yang tersedia
def get_gemini_model():
    try:
        # Coba model terbaru dulu
        return genai.GenerativeModel('gemini-1.5-flash-latest')
    except:
        # Fallback ke model standar
        return genai.GenerativeModel('gemini-pro')

model = get_gemini_model()

# --- 3. FUNGSI HITUNG RSI ---
def calculate_rsi(series, period=14):
    delta = series.diff(1)
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- 4. FUNGSI ANALISA AI ---
def get_ai_analysis(ticker, price, rsi):
    print(f"   ...Meminta pendapat Gemini soal {ticker}...")
    
    prompt = f"""
    Bertindaklah sebagai Analis Saham Profesional.
    Data Real-time: {ticker} | Harga: {price} | RSI: {rsi:.2f}

    Tugas: Berikan komentar 1 kalimat singkat (Maks 15 kata).
    
    ATURAN FORMAT:
    1. RSI < 40: WAJIB pakai kata "Sangat Murah" atau "Potensi Naik".
    2. RSI > 65: WAJIB pakai kata "Terlalu Mahal" atau "Rawan Turun".
    3. RSI 40-65: Sebut "Netral" atau "Wait and See".
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Gagal analisa AI: {e}"

# --- 5. FUNGSI UTAMA (SCANNER) ---
def scan_market():
    print("--- STOCKVISION AI: STARTED (SECURE MODE) ---")
    
    # Pastikan DB_URL ada
    if not DB_URL:
        print("[ERROR] DB_URL tidak ditemukan di file .env!")
        return

    engine = create_engine(DB_URL)
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
            
            # Label
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
            time.sleep(2) 

        except Exception as e:
            print(f"   [ERROR] {ticker}: {e}")

if __name__ == "__main__":
    scan_market()