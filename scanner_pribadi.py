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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. FUNGSI KIRIM TELEGRAM ---
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown" # Biar bisa Huruf Tebal
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Gagal kirim Telegram: {e}")

# --- 3. ANALISIS AI SWING ---
def get_ai_swing_advice(ticker, price):
    prompt = f"""
    Kamu Advisor Pribadi. Saham {ticker} (Harga {price}) secara teknikal sedang UPTREND (Diatas MA20).
    
    TUGAS:
    1. Googling berita singkat seminggu terakhir.
    2. Apakah ada sentimen negatif fatal? (Isu korupsi, PKPU, Laba anjlok drastis).
    
    JAWAB (Singkat Padat untuk Telegram):
    - Jika Aman: "✅ AMAN. [Alasan singkat 5 kata]"
    - Jika Bahaya: "⚠️ WASPADA. [Sebutkan isunya]"
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp', 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_modalities=["TEXT"]
            )
        )
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text: return part.text.strip()
        return "Info berita minim, cek manual."
    except:
        return "Analisis AI Timeout."

# --- 4. SCANNER UTAMA ---
def scan_my_portfolio():
    print("--- 🕵️‍♂️ PRIVATE SWING SCANNER MULAI ---")
    
    # Daftar Saham Pilihan (Liquid & Fundamental Oke)
    # Tidak ada saham 'gorengan' murni disini
    watchlist = [
        'BBRI.JK', 'BBCA.JK', 'BMRI.JK', 'BBNI.JK', 'TLKM.JK', 'ASII.JK',
        'UNTR.JK', 'ICBP.JK', 'INDF.JK', 'KLBF.JK', 'MDKA.JK', 'ANTM.JK',
        'ADRO.JK', 'PTBA.JK', 'PGAS.JK', 'AKRA.JK', 'AMMN.JK', 'BRIS.JK',
        'GOTO.JK', 'CPIN.JK', 'JPFA.JK', 'SMGR.JK', 'JSMR.JK', 'MYOR.JK'
    ]
    
    candidates = []

    for ticker in watchlist:
        try:
            # Ambil data Harian (Daily) untuk Swing
            df = yf.download(ticker, period='3mo', interval='1d', progress=False)
            if len(df) < 50: continue
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Hitung MA20 (Garis Tren Bulanan)
            df['MA20'] = df['Close'].rolling(window=20).mean()
            
            # Hitung RSI
            delta = df['Close'].diff(1)
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            last_price = float(df['Close'].iloc[-1])
            ma20 = float(df['MA20'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])

            # --- LOGIKA SWING (Trend Follower) ---
            # 1. Harga DI ATAS MA20 (Wajib Uptrend)
            # 2. RSI Antara 40 - 65 (Momentum ada, tapi belum kemahalan)
            
            if last_price > ma20 and 40 <= rsi <= 65:
                # Cek Jarak ke MA20 (Semakin dekat semakin Low Risk)
                jarak_ma = ((last_price - ma20) / ma20) * 100
                
                candidates.append({
                    'ticker': ticker,
                    'price': last_price,
                    'rsi': rsi,
                    'jarak': jarak_ma
                })
                print(f"   [CANDIDATE] {ticker}")

        except Exception: continue

    # Kirim Laporan ke Telegram jika ada kandidat
    if candidates:
        # Urutkan berdasarkan RSI terendah (Buy on Weakness) atau Jarak terdekat
        candidates = sorted(candidates, key=lambda x: x['rsi'])[:5] # Ambil 5 terbaik
        
        report = "🦅 *LAPORAN SWING PRIBADI*\n"
        report += f"📅 {time.strftime('%d-%m-%Y')}\n\n"
        
        for stock in candidates:
            ticker = stock['ticker']
            ai_advice = get_ai_swing_advice(ticker, stock['price'])
            
            report += f"💎 *{ticker}* (Rp {stock['price']:.0f})\n"
            report += f"   • RSI: {stock['rsi']:.1f} (Sehat)\n"
            report += f"   • Posisi: {stock['jarak']:.1f}% di atas MA20\n"
            report += f"   • 🤖 {ai_advice}\n\n"
        
        report += "_Disarankan HOLD 1-2 Minggu selama harga diatas MA20._"
        send_telegram(report)
        print("Laporan terkirim ke Telegram!")
    else:
        send_telegram("Market sedang jelek/sideways. Tidak ada sinyal swing hari ini. 😴")

if __name__ == "__main__":
    scan_my_portfolio()