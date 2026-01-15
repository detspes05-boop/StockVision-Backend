from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load env jika di laptop (di Render ini otomatis dilewati)
load_dotenv()

app = FastAPI()

# 1. KONEKSI DATABASE
DB_URL = os.getenv("DB_URL")

# Fungsi untuk cek koneksi (Safety Check)
try:
    if DB_URL:
        # Ganti 'postgres://' jadi 'postgresql://' jika perlu (fix bug library lama)
        if DB_URL.startswith("postgres://"):
            DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(DB_URL)
        print("✅ Database Connected via Main API")
    else:
        print("⚠️ DB_URL not found!")
        engine = None
except Exception as e:
    print(f"❌ Connection Failed: {e}")
    engine = None

@app.get("/")
def read_root():
    return {
        "status": "Server is ON",
        "message": "Welcome to StockVision API. Access /api/signals to see data."
    }

# 2. ENDPOINT UTAMA: /api/signals
@app.get("/api/signals")
def get_signals():
    if not engine:
        raise HTTPException(status_code=500, detail="Database connection not setup")
    
    try:
        # Ambil data terbaru dari tabel detected_patterns
        # Urutkan dari yang paling baru (created_at DESC)
        query = text("SELECT * FROM detected_patterns ORDER BY created_at DESC LIMIT 20")
        
        with engine.connect() as conn:
            result = conn.execute(query)
            # Ubah hasil database menjadi list (JSON)
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            return data

    except Exception as e:
        # Jika tabel belum ada atau error lain
        print(f"Error reading DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))