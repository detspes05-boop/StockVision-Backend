from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import pandas as pd

# Load env jika di laptop (di Render ini otomatis dilewati)
load_dotenv()

app = FastAPI()

# 1. KONEKSI DATABASE
DB_URL = os.getenv("DB_URL")

try:
    if DB_URL:
        # Ganti 'postgres://' jadi 'postgresql://' jika perlu
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
        "message": "Welcome to StockVision API. Access /api/signals to see latest Top Gainers."
    }

# 2. ENDPOINT UTAMA: /api/signals (VERSI UPDATE)
@app.get("/api/signals")
def get_signals():
    if not engine:
        raise HTTPException(status_code=500, detail="Database connection not setup")
    
    try:
        # PERBAIKAN UTAMA:
        # 1. ORDER BY created_at DESC -> Mengambil data waktu terbaru
        # 2. LIMIT 15 -> Hanya menampilkan 15 saham teratas (Top Gainers)
        query = text("SELECT ticker, pattern_name, price, story, created_at FROM detected_patterns ORDER BY created_at DESC LIMIT 15")
        
        with engine.connect() as conn:
            result = conn.execute(query)
            # Ubah hasil database menjadi list dictionary (JSON)
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            return data
            
    except Exception as e:
        print(f"❌ Query Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)