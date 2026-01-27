import os
import time
import requests
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- 1. SETUP ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
        print("   ✅ Pesan terkirim.")
    except Exception as e:
        print(f"   ❌ Gagal kirim Telegram: {e}")

# --- 2. MAKRO EKONOMI ---
def get_global_market_sentiment():
    print("\n🌍 Membaca kondisi pasar Global & IHSG...")
    prompt = """
    Analisis singkat pasar hari ini: IHSG, Rupiah (IDR/USD), dan Harga Komoditas (Emas/Minyak/CPO).
    Apakah Risk-On (Berani Beli) atau Risk-Off (Hati-hati)?
    Jawab 1 kalimat. Contoh: "Pasar Risk-Off, IHSG merah -1%, Rupiah melemah."
    """
    try:
        response = client.models.generate_content(
            model='gemini-flash-latest', 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1
            )
        )
        if response.candidates and response.candidates[0].content.parts:
            sentiment = response.candidates[0].content.parts[0].text.strip()
            print(f"   👉 Sentimen: {sentiment}")
            return sentiment
    except: return "Pasar Netral (Data Gagal)"

# --- 3. OTAK PRO (AI + RISK CALCULATION + STRICT TABLE) ---
def get_pro_swing_advice(ticker, price, rsi, ma20, volume_status, market_context):
    print(f"   🧠 AI sedang menganalisis {ticker}...")
    
    # Hitung data risiko untuk disuapkan ke AI
    risk_per_share = price - ma20
    risk_percent = (risk_per_share / price) * 100
    
    # PROMPT UTAMA (Versi "Galak" - Wajib Tabel)
    prompt_utama = f"""
    Role: Trading Signal Bot (NOT Assistant).
    Context: "{market_context}"
    Data: {ticker} | Price: {price} | MA20: {ma20} | RSI: {rsi:.1f} | Vol: {volume_status}
    
    TASK:
    Analyze news (7 days) & technicals. Decide BUY/WAIT/SKIP.
    
    CRITICAL INSTRUCTION:
    1. NO conversational fillers (Do not say "Sure", "Here is the analysis").
    2. OUTPUT MUST BE ONLY THE TABLE BELOW.
    3. Use Bahasa Indonesia for the content inside the table.
    
    REQUIRED OUTPUT FORMAT:
    | PARAMETER | VALUE |
    | :--- | :--- |
    | 🎯 ACTION | [🟢 BUY / 🔴 WAIT / ⚫ SKIP] |
    | 📝 ALASAN | [Sebutkan berita/teknikal dalam 1 kalimat pendek] |
    | 💰 AREA BELI | [Range Harga, misal: {price}-{price+10}] |
    | 🚀 TARGET | [Harga Jual, misal: {price*1.05:.0f}] |
    | 🛑 STOP LOSS | [Harga dibawah {ma20:.0f}] |
    """
    
    # PROMPT CADANGAN (Emergency Mode)
    prompt_cadangan = f"""
    Buatkan Tabel Sinyal Trading untuk saham {ticker} (Harga {price}, MA20 {ma20}).
    Format Tabel: ACTION, ALASAN, AREA BELI, TARGET, STOP LOSS.
    JANGAN pakai basa-basi. Langsung Tabel.
    """

    # --- MEKANISME RETRY PINTAR (Loop 3x) ---
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Gunakan 'gemini-1.5-flash' (Kuota Besar & Stabil)
            response = client.models.generate_content(
                model='gemini-flash-latest', 
                contents=prompt_utama,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())], 
                    temperature=0.1 # Rendah agar AI patuh format
                )
            )
            
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text.strip()
                
        except Exception as e:
            # Cek jika errornya adalah Kuota Habis (429)
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = 30 # Tunggu 30 detik
                print(f"   ⏳ Kuota Limit! Menunggu {wait_time} detik... ({attempt+1}/{max_retries})")
                time.sleep(wait_time) 
                continue # Coba lagi
            else:
                # Jika error lain, langsung switch ke cadangan
                break 

    # --- JIKA UTAMA GAGAL, PAKAI CADANGAN (TANPA SEARCH) ---
    try:
        response = client.models.generate_content(
            model='gemini-flash-latest', 
            contents=prompt_cadangan,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        if response.candidates and response.candidates[0].content.parts:
             return response.candidates[0].content.parts[0].text.strip()
    except Exception:
        pass

    return "⚠️ Data tidak tersedia (Cek Koneksi)."

# --- 4. SCANNER UTAMA ---
import os
import time
import requests
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- 1. SETUP ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_API_KEY)

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        # disable_web_page_preview=True agar link stockbit tidak bikin preview gambar besar
        payload = {
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": message, 
            "parse_mode": "Markdown", 
            "disable_web_page_preview": True 
        }
        requests.post(url, json=payload)
        print("   ✅ Pesan terkirim.")
    except Exception as e:
        print(f"   ❌ Gagal kirim Telegram: {e}")

# --- 2. MAKRO EKONOMI (STABIL) ---
def get_global_market_sentiment():
    print("\n🌍 Membaca kondisi pasar Global & IHSG...")
    prompt = """
    Analisis singkat pasar hari ini: IHSG, Rupiah (IDR/USD), dan Harga Komoditas (Emas/Minyak/CPO).
    Apakah Risk-On (Berani Beli) atau Risk-Off (Hati-hati)?
    Jawab 1 kalimat. Contoh: "Pasar Risk-Off, IHSG merah -1%, Rupiah melemah."
    """
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1
            )
        )
        if response.candidates and response.candidates[0].content.parts:
            sentiment = response.candidates[0].content.parts[0].text.strip()
            print(f"   👉 Sentimen: {sentiment}")
            return sentiment
    except: return "Pasar Netral (Data Gagal)"

# --- 3. OTAK PRO (AI + TABEL STRICT + RETRY) ---
def get_pro_swing_advice(ticker, price, rsi, ma20, volume_status, market_context):
    print(f"   🧠 AI sedang menganalisis {ticker}...")
    
    # Prompt Utama (Versi "Galak" - WAJIB TABEL)
    prompt_utama = f"""
    Role: Trading Signal Bot (Strict Mode).
    Context: "{market_context}"
    Data: {ticker} | Price: {price} | MA20: {ma20} | RSI: {rsi:.1f} | Vol: {volume_status}
    
    TASK:
    Analyze news (3 days) & technicals. Decide BUY/WAIT/SKIP.
    
    CRITICAL INSTRUCTION:
    1. NO conversational fillers (DO NOT say "Sure", "Here is the analysis").
    2. OUTPUT MUST BE ONLY THE TABLE BELOW.
    3. Use Bahasa Indonesia for the content inside the table.
    
    REQUIRED OUTPUT FORMAT:
    | PARAMETER | VALUE |
    | :--- | :--- |
    | 🎯 ACTION | [🟢 BUY / 🔴 WAIT / ⚫ SKIP] |
    | 📝 ALASAN | [Sebutkan berita/teknikal dalam 1 kalimat pendek] |
    | 💰 AREA BELI | [Range Harga, misal: {price}-{price+10}] |
    | 🚀 TARGET | [Harga Jual, misal: {price*1.05:.0f}] |
    | 🛑 STOP LOSS | [Harga dibawah {ma20:.0f}] |
    """
    
    # Prompt Cadangan
    prompt_cadangan = f"""
    Buatkan Tabel Sinyal Trading untuk saham {ticker} (Harga {price}, MA20 {ma20}).
    Format Tabel: ACTION, ALASAN, AREA BELI, TARGET, STOP LOSS.
    JANGAN pakai basa-basi. Langsung Tabel.
    """

    # --- MEKANISME RETRY PINTAR (Loop 3x) ---
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=prompt_utama,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())], 
                    temperature=0.1 
                )
            )
            
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text.strip()
                
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = 30
                print(f"   ⏳ Kuota Limit! Menunggu {wait_time} detik... ({attempt+1}/{max_retries})")
                time.sleep(wait_time) 
                continue 
            else:
                break 

    # --- MODE CADANGAN ---
    try:
        response = client.models.generate_content(
            model='gemini-flash-latest', 
            contents=prompt_cadangan,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        if response.candidates and response.candidates[0].content.parts:
             return response.candidates[0].content.parts[0].text.strip()
    except Exception:
        pass

    return "⚠️ Data tidak tersedia (Cek Koneksi)."

# --- 4. SCANNER UTAMA (FITUR BARU + LOGIKA LAMA) ---
def scan_local_portfolio():
    print("\n" + "="*60)
    print("   🚀 STOCKVISION PRO: SMART EXECUTION EDITION")
    print("="*60 + "\n")
    
    # DAFTAR SAHAM (Sama Persis dengan Punya Anda)
    watchlist = [
        'TLKM.JK', 'ASII.JK', 'UNTR.JK', 'ICBP.JK', 'INDF.JK', 'KLBF.JK', 
        'MDKA.JK', 'ANTM.JK', 'ADRO.JK', 'PTBA.JK', 'PGAS.JK', 'AKRA.JK', 
        'AMMN.JK', 'BRIS.JK', 'CPIN.JK', 'JPFA.JK', 'SMGR.JK', 'JSMR.JK', 
        'MYOR.JK', 'HRUM.JK', 'MEDC.JK', 'ISAT.JK', 'EXCL.JK', 'MAPI.JK', 
        'ACES.JK', 'INKP.JK', 'TKIM.JK', 'LSIP.JK'
    ]
    
    market_sentiment = get_global_market_sentiment()
    candidates = []
    
    print("\n🔍 Tahap 1: Technical & Volume Screening...")
    for ticker in watchlist:
        try:
            df = yf.download(ticker, period='6mo', interval='1d', progress=False)
            if len(df) < 50: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

            # --- INDIKATOR DASAR (Sama Persis) ---
            df['MA20'] = df['Close'].rolling(window=20).mean()
            delta = df['Close'].diff(1)
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # --- VOLUME ANALYSIS (Sama Persis) ---
            vol_avg = df['Volume'].iloc[-20:].mean()
            vol_now = df['Volume'].iloc[-1]
            vol_ratio = vol_now / vol_avg
            
            if vol_ratio > 1.2: vol_status = "🔥 High Volume (Akumulasi)"
            elif vol_ratio < 0.8: vol_status = "❄️ Low Volume (Sepi)"
            else: vol_status = "Normal Volume"

            # --- [FITUR BARU 1] SHADOW ANALYSIS (Deteksi Jejak Guyuran) ---
            # Bagian ini hanya menambah INFO, tidak memfilter saham
            high = float(df['High'].iloc[-1])
            low = float(df['Low'].iloc[-1])
            close = float(df['Close'].iloc[-1])
            open_price = float(df['Open'].iloc[-1])
            
            candle_range = high - low
            if candle_range == 0: candle_range = 1 
            
            upper_shadow = high - max(close, open_price)
            shadow_ratio = upper_shadow / candle_range
            
            if shadow_ratio > 0.4:
                orderbook_note = "⚠️ Awas Guyuran (Ekor Atas Panjang)"
            else:
                orderbook_note = "✅ Selling Pressure Rendah"

            lp = close
            ma20 = float(df['MA20'].iloc[-1])
            rsi = float(df['RSI'].iloc[-1])

            # --- LOGIC FILTER (SAMA PERSIS DENGAN KODE LAMA ANDA) ---
            # 1. Uptrend (Harga > MA20)
            # 2. RSI Sehat (40 - 65)
            # 3. Volume Likuid (> 500k)
            if lp > ma20 and 40 <= rsi <= 65:
                if vol_avg > 500000:
                    candidates.append({
                        'ticker': ticker, 'price': lp, 'rsi': rsi, 
                        'ma20': ma20, 'vol_status': vol_status,
                        'ob_note': orderbook_note # Info tambahan disimpan
                    })
                    print(f"   ✨ Lolos: {ticker} | {vol_status}")

        except: continue

    if candidates:
        print(f"\n🔍 Tahap 2: AI Risk Assessment...")
        # Prioritas tetap sama: Volume Tinggi dulu
        candidates = sorted(candidates, key=lambda x: (x['vol_status'] != "🔥 High Volume (Akumulasi)", x['rsi']))
        
        header = f"🦅 *STOCKVISION PRO*\n📅 {time.strftime('%d-%m-%Y')}\n"
        header += f"🌍 _Sentiment: {market_sentiment}_\n"
        send_telegram(header)
        
        for stock in candidates:
            # Hitung Risiko Rupiah
            risk_rupiah = (stock['price'] - stock['ma20']) * 100
            
            # Panggil AI (Strict Table)
            plan = get_pro_swing_advice(
                stock['ticker'], stock['price'], stock['rsi'], 
                stock['ma20'], stock['vol_status'], market_sentiment
            )
            
            # [FITUR BARU 2] Buat Link Pintas (Deep Link)
            clean_ticker = stock['ticker'].replace('.JK', '')
            link_sb = f"https://stockbit.com/symbol/{clean_ticker}"
            
            msg = f"💎 *{stock['ticker']}* (Rp {stock['price']:.0f})\n"
            msg += f"   📊 Vol: {stock['vol_status']}\n"
            msg += f"   🛡️ OB Info: _{stock['ob_note']}_\n" # Info Guyuran
            msg += f"{plan}\n"
            msg += f"⚠️ *RISIKO PER LOT:* -Rp {risk_rupiah:,.0f}\n" 
            msg += f"📲 [Cek Orderbook di Stockbit]({link_sb})" # Link Klik
            
            send_telegram(msg)
            print("   ...Cooldown 10 detik...")
            time.sleep(10)
            
        send_telegram("✅ *Sesi Selesai.*")
    else:
        send_telegram(f"Market Tidak Mendukung. ({market_sentiment}) 😴")

if __name__ == "__main__":
    scan_local_portfolio()
