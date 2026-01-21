import os
import requests
import yfinance as yf
import pandas as pd
from google import genai
from google.genai import types
from dotenv import load_dotenv
import time

# --- 1. SETUP ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_PRIBADI")

client = genai.Client(api_key=GEMINI_API_KEY)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Gagal kirim Telegram: {e}")

# --- 2. FUNGSI ANALISIS AI (OPTIMASI FREE TIER) ---
def get_ai_swing_advice(ticker, price):
    print(f"   🤖 AI sedang menganalisis {ticker}...")
    
    # Prompt padat untuk menghemat token dan mempercepat respon
    prompt = f"""
    Analis emiten {ticker} (Harga {price}). 
    Cari berita seminggu terakhir. Apakah ada isu PKPU, korupsi, atau laba anjlok >50%?
    Jawab singkat: '✅ AMAN. [Alasan]' atau '⚠️ WASPADA. [Isu]'. Maksimal 10 kata.
    """
    
    # Strategi Retry jika kena Limit Kuota
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash', # Model tercepat & jatah paling banyak di Free Tier
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    request_options={"timeout": 30000}
                )
            )
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text.strip()
        except Exception as e:
            if "429" in str(e): # Error kuota habis
                print(f"   ⚠️ Limit tercapai, menunggu 20 detik untuk {ticker}...")
                time.sleep(20)
            else:
                print(f"   ❌ Gagal pada {ticker}: {e}")
    return "Skip (Kuota Limit)"

# --- 3. SCANNER UTAMA ---
def scan_my_portfolio():
    print("--- 🕵️‍♂️ PRIVATE SWING SCANNER (FREE TIER OPTIMIZED) ---")
    
    # Daftar Saham Pilihan
    watchlist = [
        'BBRI.JK', 'BBCA.JK', 'BMRI.JK', 'BBNI.JK', 'TLKM.JK', 'ASII.JK',
        'UNTR.JK', 'ICBP.JK', 'INDF.JK', 'KLBF.JK', 'MDKA.JK', 'ANTM.JK',
        'ADRO.JK', 'PTBA.JK', 'PGAS.JK', 'AKRA.JK', 'AMMN.JK', 'BRIS.JK',
        'GOTO.JK', 'CPIN.JK', 'JPFA.JK', 'SMGR.JK', 'JSMR.JK', 'MYOR.JK'
    ]
    
    candidates = []
    for ticker in watchlist:
        try:
            df = yf.download(ticker, period='3mo', interval='1d', progress=False)
            if len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

            df['MA20'] = df['Close'].rolling(window=20).mean()
            delta = df['Close'].diff(1)
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            lp = float(df['Close'].iloc[-1])
            ma = float(df['MA20'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])

            # Filter Teknis: Uptrend & RSI Sehat
            if lp > ma and 40 <= rsi <= 65:
                candidates.append({'ticker': ticker, 'price': lp, 'rsi': rsi})
                print(f"   [CANDIDATE] {ticker}")
        except: continue

    if candidates:
        # PENTING: Batasi maksimal 3 saham agar jatah Google Search tidak habis
        candidates = sorted(candidates, key=lambda x: x['rsi'])[:3]
        
        report = "🦅 *LAPORAN SWING PRIBADI*\n\n"
        for stock in candidates:
            res = get_ai_swing_advice(stock['ticker'], stock['price'])
            report += f"💎 *{stock['ticker']}* (Rp {stock['price']:.0f})\n"
            report += f"   • RSI: {stock['rsi']:.1f}\n"
            report += f"   • 🤖 {res}\n\n"
            
            # Jeda 15 detik antar saham agar aman dari deteksi bot Google
            time.sleep(15) 
        
        send_telegram(report)
        print("Selesai.")
    else:
        send_telegram("Tidak ada sinyal hari ini. 😴")

if __name__ == "__main__":
    scan_my_portfolio()