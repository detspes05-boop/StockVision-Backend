import os
from dotenv import load_dotenv
import yfinance as yf
from sqlalchemy import create_engine
import pandas as pd
from google import genai 
import time
import datetime

# --- 1. LOAD RAHASIA ---
load_dotenv()
DB_URL = os.getenv("DB_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- 2. SETUP CLIENT ---
client = genai.Client(api_key=GEMINI_API_KEY)

# --- 3. AI ANALYSIS (DIOPTIMALKAN UNTUK SAHAM LIAR) ---
def get_ai_analysis(ticker, price, change_pct):
    prompt = f"""
    Bertindaklah sebagai Analis Saham Day Trading.
    Saham: {ticker} | Harga: {price} | Naik: {change_pct:.2f}%
    Berikan komentar 1 kalimat singkat (Maks 10 kata).
    Fokus pada momentum kenaikan harga.
    """
    try:
        response = client.models.generate_content(
            model='gemini-flash-latest', 
            contents=prompt
        )
        return response.text.strip()
    except Exception:
        return f"Momentum kuat, naik {change_pct:.1f}% hari ini."

# --- 4. SCANNER UTAMA (TOP GAINERS MODE) ---
def scan_top_gainers():
    print("--- STOCKVISION AI: TOP GAINERS SCANNER STARTED ---")
    
    if not DB_URL:
        print("[ERROR] DB_URL Kosong!")
        return

    try:
        engine = create_engine(DB_URL)
    except Exception as e:
        print(f"[FATAL] Koneksi DB Gagal: {e}")
        return

    # Daftar 50 Saham Campuran (Bluechip + Volatil/Lapis 2 & 3)
    daftar_50 = [
        'BBRI.JK', 'BBCA.JK', 'BMRI.JK', 'TLKM.JK', 'ASII.JK', 'GOTO.JK', 'ANTM.JK', 'BRMS.JK',
        'BUMI.JK', 'DEWA.JK', 'ADRO.JK', 'PTBA.JK', 'ITMG.JK', 'UNTR.JK', 'PGAS.JK', 'MEDC.JK',
        'AMMN.JK', 'BBNI.JK', 'BRIS.JK', 'TPIA.JK', 'INKP.JK', 'TKIM.JK', 'KLBF.JK', 'UNVR.JK',
        'ICBP.JK', 'INDF.JK', 'CPIN.JK', 'JPFA.JK', 'SMGR.JK', 'INTP.JK', 'MDKA.JK', 'MBMA.JK',
        'HRUM.JK', 'AKRA.JK', 'BRPT.JK', 'ADMR.JK', 'BUKA.JK', 'BELI.JK', 'BSDE.JK', 'PWON.JK',
        'CTRA.JK', 'SMRA.JK', 'JSMR.JK', 'SSIA.JK', 'ASPI.JK', 'PACK.JK', 'CBRE.JK', 'STRK.JK',
        'CUAN.JK', 'BREN.JK'
    ]

    results = []
    
    print(f"Memulai pemindaian {len(daftar_50)} saham...")
    
    for ticker in daftar_50:
        try:
            # Ambil data 2 hari terakhir untuk hitung perubahan harga
            df = yf.download(ticker, period='2d', interval='1d', progress=False)
            if len(df) < 2: continue
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            last_price = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            
            # Hitung % Kenaikan
            change_pct = ((last_price - prev_close) / prev_close) * 100
            
            # Filter: Hanya ambil yang naik (Gainers)
            if change_pct > 0:
                results.append({
                    'ticker': ticker,
                    'price': last_price,
                    'change_pct': change_pct
                })
                print(f"   [FOUND] {ticker}: +{change_pct:.2f}%")

        except Exception as e:
            print(f"   [SKIP] {ticker}: {e}")

    # Urutkan berdasarkan kenaikan tertinggi dan ambil 15 Teratas
    top_gainers = sorted(results, key=lambda x: x['change_pct'], reverse=True)[:15]

    print(f"\n--- Memproses {len(top_gainers)} Top Gainers dengan AI ---")

    for stock in top_gainers:
        ticker = stock['ticker']
        last_price = stock['price']
        change_pct = stock['change_pct']

        # Label Sinyal berdasarkan kekuatan kenaikan
        if change_pct > 5.0:
            pattern_label = "AI SIGNAL: STRONG BUY (MOMENTUM)"
        else:
            pattern_label = "AI SIGNAL: NEUTRAL (GAINER)"

        ai_story = get_ai_analysis(ticker, last_price, change_pct)
        print(f"   -> {ticker} (+{change_pct:.1f}%): {ai_story}")

        # Simpan ke Database
        now_wib = datetime.datetime.now()
        data_to_save = pd.DataFrame({
            'ticker': [ticker],
            'pattern_name': [pattern_label],
            'price': [last_price],
            'story': [ai_story],
            'created_at': [now_wib]
        })
        
        try:
            data_to_save.to_sql('detected_patterns', engine, if_exists='append', index=False)
        except Exception as e:
            print(f"   [DB ERROR] Gagal simpan {ticker}: {e}")

        time.sleep(2) # Jeda singkat antar AI request

    print("\n--- SCAN SELESAI: DATABASE UPDATED ---")

if __name__ == "__main__":
    scan_top_gainers()