from fastapi import FastAPI
from sqlalchemy import create_engine, text

app = FastAPI()

# --- KONFIGURASI DATABASE ---
# Ganti dengan password asli Anda!
DB_URL = 'postgresql://postgres:superuser14edb@localhost:5432/stockvision'
engine = create_engine(DB_URL)

@app.get("/")
def home():
    return {"pesan": "Server StockVision Aktif!", "status": "Online"}

@app.get("/api/patterns")
def get_patterns():
    # 1. Buka koneksi ke database
    with engine.connect() as connection:
        # 2. Ambil semua data dari tabel detected_patterns
        # Kita urutkan dari yang terbaru (DESC)
        result = connection.execute(text("SELECT * FROM detected_patterns ORDER BY id DESC"))
        
        # 3. Ubah hasil database menjadi format JSON (Daftar Kamus)
        data_saham = []
        for baris in result:
            data_saham.append({
                "id": baris.id,
                "ticker": baris.ticker,
                "pattern": baris.pattern_name,
                "price": baris.price,
                "story": baris.story
            })
            
    return data_saham