import google.generativeai as genai

# --- MASUKKAN API KEY ANDA DI SINI ---
API_KEY = "AIzaSyBWXhTJQRbQE6q6fUQwdicYZPy-xT50jZw"
genai.configure(api_key=API_KEY)

print("--- SEDANG MENGHUBUNGI GOOGLE... ---")
try:
    # Kita minta daftar semua model yang tersedia
    for m in genai.list_models():
        # Kita hanya cari model yang bisa 'generateContent' (bisa diajak ngobrol)
        if 'generateContent' in m.supported_generation_methods:
            print(f"MODEL DITEMUKAN: {m.name}")
            
except Exception as e:
    print(f"TERJADI ERROR: {e}")