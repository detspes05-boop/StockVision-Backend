import os
from dotenv import load_dotenv
import yfinance as yf
from sqlalchemy import create_engine
import pandas as pd
from google import genai 
import time
import datetime # Import wajib untuk waktu

# --- 1. LOAD RAHASIA ---
load_dotenv()
DB_URL = os.getenv("DB_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- 2. SETUP CLIENT BARU ---
client = genai.Client(api_key=GEMINI_API_KEY)

# --- 3. RSI FUNCTION ---
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
        response = client.models.generate_content(
            model='gemini-flash-latest', 
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        if "429" in str(e): return "Sinyal: Menunggu Kuota AI..."
        return f"Gagal analisa AI: {e}"

# --- 5. SCANNER UTAMA ---
def scan_market():
    print("--- STOCKVISION AI: STARTED (TIMESTAMP MODE) ---")
    
    if not DB_URL:
        print("[ERROR] DB_URL Kosong!")
        return

    # Cek Database Tujuan (Masked)
    db_host = DB_URL.split('@')[1].split('/')[0] if '@' in DB_URL else "UNKNOWN"
    print(f"   [INFO] Mengirim data ke: ...@{db_host}")

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

            # Simpan dengan JAM SEKARANG
            now_wib = datetime.datetime.now()
            
            data_to_save = pd.DataFrame({
                'ticker': [ticker],
                'pattern_name': [pattern_label],
                'price': [last_price],
                'story': [ai_story],
                'created_at': [now_wib] # <--- INI PENTING
            })
            
            data_to_save.to_sql('detected_patterns', engine, if_exists='append', index=False)
            print("   -> [DATABASE] Data tersimpan dengan Timestamp!")
            
            # Istirahat 15 detik
            print("   ...Istirahat 15 detik...")
            time.sleep(15) 

        except Exception as e:
            print(f"   [ERROR] {ticker}: {e}")
            time.sleep(10)

if __name__ == "__main__":
    scan_market()