import os
import time
import requests
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- 1. KONFIGURASI LOKAL ---
load_dotenv() # Membaca file .env

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. FUNGSI KIRIM TELEGRAM ---
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": message, 
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
        print("   ✅ Pesan terkirim ke Telegram.")
    except Exception as e:
        print(f"   ❌ Gagal kirim Telegram: {e}")

# --- 3. OTAK AI (MODE SINYAL EKSEKUSI) ---
def get_ai_swing_advice(ticker, price, rsi, ma20):
    print(f"   🧠 AI sedang meracik Sinyal Trading untuk {ticker}...")
    
    # Prompt: Gabungan Teknikal (Data) + Fundamental (Google Search)
    prompt = f"""
    Bertindaklah sebagai Pelatih Swing Trading Profesional.
    Data Saham: {ticker}
    - Harga Saat Ini: Rp {price}
    - Support Kuat (MA20): Rp {ma20}
    - RSI: {rsi:.1f} (Momentum)

    TUGAS FUNDAMENTAL (WAJIB):
    Gunakan Google Search untuk cek berita/sentimen 3-5 hari terakhir.
    1. Jika ada berita FATAL (Korupsi, PKPU, Laba Anjlok Parah) -> Putuskan SKIP/WAIT.
    2. Jika berita Positif/Netral -> Putuskan BUY/HOLD.

    OUTPUT TABLE (JANGAN PAKAI FORMAT LAIN):
    ACTION: [🟢 BUY / 🔴 WAIT / ⚫ SKIP]
    ALASAN: [1 Kalimat Singkat tentang Berita/Katalis Fundamental]
    AREA BELI: [Range Harga di dekat MA20]
    TARGET JUAL: [Harga +5% sampai +10%]
    STOP LOSS: [Harga dibawah {ma20}]
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-flash-latest', 
            contents=prompt,
            config=types.GenerateContentConfig(
                # INI BUKTI BAHWA DIA TETAP CARI BERITA
                tools=[types.Tool(google_search=types.GoogleSearch())], 
                temperature=0.2 # Rendah agar angka konsisten
            )
        )
        
        if response.candidates and response.candidates[0].content.parts:
            return response.candidates[0].content.parts[0].text.strip()
            
    except Exception as e:
        print(f"   ⚠️ Error AI pada {ticker}: {e}")
        return "⚠️ Gagal hitung sinyal."
    
    return "Data tidak ditemukan."

# --- 4. SCANNER UTAMA ---
def scan_local_portfolio():
    print("\n" + "="*50)
    print("   🚀 STOCKVISION: ACTION PLAN GENERATOR")
    print("   💻 Mode: Local Laptop (Unlimited Search)")
    print("="*50 + "\n")
    
    watchlist = [
        'BBRI.JK', 'BBCA.JK', 'BMRI.JK', 'BBNI.JK', 'TLKM.JK', 'ASII.JK',
        'UNTR.JK', 'ICBP.JK', 'INDF.JK', 'KLBF.JK', 'MDKA.JK', 'ANTM.JK',
        'ADRO.JK', 'PTBA.JK', 'PGAS.JK', 'AKRA.JK', 'AMMN.JK', 'BRIS.JK',
        'GOTO.JK', 'CPIN.JK', 'JPFA.JK', 'SMGR.JK', 'JSMR.JK', 'MYOR.JK',
        'HRUM.JK', 'MEDC.JK', 'ISAT.JK', 'EXCL.JK', 'MAPI.JK', 'ACES.JK'
    ]
    
    candidates = []
    
    # TAHAP 1: FILTER TEKNIKAL
    print("🔍 Tahap 1: Scanning Teknikal (MA20 & RSI)...")
    for ticker in watchlist:
        try:
            df = yf.download(ticker, period='6mo', interval='1d', progress=False)
            if len(df) < 50: continue
            
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)

            df['MA20'] = df['Close'].rolling(window=20).mean()
            delta = df['Close'].diff(1)
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            last_price = float(df['Close'].iloc[-1])
            ma20 = float(df['MA20'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])

            # Syarat: Harga > MA20 DAN RSI Sehat (40-65)
            if last_price > ma20 and 40 <= rsi <= 65:
                # Filter Volume Likuid
                if df['Volume'].iloc[-5:].mean() > 1000000: 
                    candidates.append({
                        'ticker': ticker,
                        'price': last_price,
                        'rsi': rsi,
                        'ma20': ma20
                    })
                    print(f"   ✨ Lolos Filter: {ticker} (RSI: {rsi:.1f})")
                    
        except Exception: continue

    # TAHAP 2: ANALISIS AI & KIRIM SINYAL
    if candidates:
        print(f"\n🔍 Tahap 2: Membuat Action Plan untuk {len(candidates)} saham...")
        candidates = sorted(candidates, key=lambda x: x['rsi'])
        
        send_telegram(f"🦅 *STOCKVISION ACTION PLAN*\n📅 {time.strftime('%d-%m-%Y %H:%M')}\n🔎 Ditemukan {len(candidates)} Saham Potensial")
        
        for stock in candidates:
            # Memanggil AI dengan data MA20
            plan = get_ai_swing_advice(stock['ticker'], stock['price'], stock['rsi'], stock['ma20'])
            
            msg = f"💎 *{stock['ticker']}* (Rp {stock['price']:.0f})\n"
            msg += f"   • RSI: {stock['rsi']:.1f} | MA20: {stock['ma20']:.0f}\n"
            msg += f"{plan}" # Langsung tempel hasil Plan dari AI
            
            send_telegram(msg)
            
            # Jeda 10 detik agar aman
            print("   ...Cooldown 10 detik...")
            time.sleep(10)
            
        send_telegram("✅ *Sesi Selesai.* \n_Disclaimer: Do Your Own Research._")
        print("\n✅ SEMUA TUGAS SELESAI.")
        
    else:
        send_telegram("Market Sideways. Tidak ada sinyal swing yang valid hari ini. 😴")

if __name__ == "__main__":
    scan_local_portfolio()
