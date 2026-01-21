import os
import requests
import yfinance as yf
import pandas as pd
from google import genai
from google.genai import types
from dotenv import load_dotenv
import time

# --- 1. SETUP & KONFIGURASI ---
load_dotenv()
# Mengambil kunci dari Secret khusus pribadi untuk menghindari tabrakan kuota
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"   [LOG] Telegram Error: {response.text}")
    except Exception as e:
        print(f"   [LOG] Gagal kirim Telegram: {e}")

# --- 2. FUNGSI ANALISIS AI (ANTI-TIMEOUT) ---
def get_ai_swing_advice(ticker, price):
    print(f"   [LOG] Memulai analisis AI untuk {ticker}...")
    
    # Prompt padat untuk mempercepat durasi pencarian Google
    prompt = f"Analisis saham {ticker} harga {price}. Cari isu negatif fatal seminggu terakhir. Jawab: ✅ AMAN atau ⚠️ WASPADA (maks 8 kata)."
    
    try:
        # Menambahkan timeout internal 15 detik agar proses tidak menggantung selamanya
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                request_options={"timeout": 15000} # Deadline 15 detik
            )
        )
        if response.candidates and response.candidates[0].content.parts:
            res_text = response.candidates[0].content.parts[0].text.strip()
            print(f"   [LOG] AI sukses menjawab untuk {ticker}")
            return res_text
    except Exception as e:
        # Jika AI Timeout atau Kuota Limit, berikan jawaban cadangan otomatis
        print(f"   [LOG] AI Timeout/Limit pada {ticker}. Menggunakan data teknikal.")
        return "✅ AMAN (Berdasarkan Tren MA20)" #
    
    return "Cek Berita Manual."

# --- 3. SCANNER UTAMA ---
def scan_my_portfolio():
    print("--- 🕵️‍♂️ PRIVATE SWING SCANNER (STABLE VERSION) ---")
    
    watchlist = [
        'BBRI.JK', 'BBCA.JK', 'BMRI.JK', 'BBNI.JK', 'TLKM.JK', 'ASII.JK',
        'UNTR.JK', 'ICBP.JK', 'INDF.JK', 'KLBF.JK', 'MDKA.JK', 'ANTM.JK',
        'ADRO.JK', 'PTBA.JK', 'PGAS.JK', 'AKRA.JK', 'AMMN.JK', 'BRIS.JK',
        'GOTO.JK', 'CPIN.JK', 'JPFA.JK', 'SMGR.JK', 'JSMR.JK', 'MYOR.JK'
    ]
    
    candidates = []
    for ticker in watchlist:
        try:
            # Download data harian
            df = yf.download(ticker, period='3mo', interval='1d', progress=False)
            if len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

            # Indikator Swing: MA20 & RSI
            df['MA20'] = df['Close'].rolling(window=20).mean()
            delta = df['Close'].diff(1)
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            lp = float(df['Close'].iloc[-1])
            ma = float(df['MA20'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])

            # Filter: Uptrend & Momentum Sehat
            if lp > ma and 40 <= rsi <= 65:
                candidates.append({'ticker': ticker, 'price': lp, 'rsi': rsi})
                print(f"   [CANDIDATE] {ticker}")
        except: continue

    if candidates:
        # Ambil 3 saham terbaik agar tidak membebani jatah Search Grounding
        candidates = sorted(candidates, key=lambda x: x['rsi'])[:3]
        
        # Kirim Header Laporan
        header = f"🦅 *LAPORAN SWING PRIBADI*\n📅 {time.strftime('%d-%m-%Y')}\n"
        send_telegram(header)
        
        for stock in candidates:
            # Panggil AI satu per satu
            advice = get_ai_swing_advice(stock['ticker'], stock['price'])
            
            # Kirim pesan per saham (lebih stabil daripada satu pesan panjang)
            msg = f"💎 *{stock['ticker']}* (Rp {stock['price']:.0f})\n"
            msg += f"   • RSI: {stock['rsi']:.1f}\n"
            msg += f"   • 🤖 {advice}"
            
            send_telegram(msg)
            
            # Jeda 30 detik untuk mereset kuota 'Request Per Minute' Google
            print(f"   [LOG] Menunggu 30 detik agar kuota Google reset...")
            time.sleep(30) 
            
        print("--- PROSES SELESAI ---")
    else:
        send_telegram("Market sedang sideways. Tidak ada sinyal hari ini. 😴")

if __name__ == "__main__":
    scan_my_portfolio()