import google.generativeai as genai

# 1. SETUP KONEKSI
# Tempel API Key Anda di dalam tanda kutip
API_KEY = "AIzaSyBWXhTJQRbQE6q6fUQwdicYZPy-xT50jZw" 
genai.configure(api_key=API_KEY)

# 2. PILIH MODEL OTAK
# Kita pakai 'gemini-1.5-flash' karena cepat dan murah/gratis
model = genai.GenerativeModel('gemini-1.5-flash')

def tanya_gemini():
    print("Sedang mengirim data ke Gemini...")
    
    # 3. BUAT PERTANYAAN (PROMPT)
    # Kita pura-pura jadi scanner yang mengirim data saham
    prompt = """
    Saya adalah trader saham. Tolong analisa data berikut secara singkat dan tegas:
    
    Saham: BBRI (Bank Rakyat Indonesia)
    Indikator Teknikal: RSI di angka 28 (Sangat Rendah/Oversold).
    Berita Terkini: "BBRI Cetak Rekor Laba Tertinggi Sepanjang Sejarah".
    
    Tugasmu:
    1. Tentukan Sinyal: STRONG BUY, BUY, SELL, atau NEUTRAL.
    2. Buat satu kalimat alasan yang meyakinkan untuk trader pemula.
    
    Jawab dengan format JSON sederhana: {"sinyal": "...", "alasan": "..."}
    """
    
    # 4. KIRIM
    response = model.generate_content(prompt)
    
    # 5. HASIL
    print("\n--- JAWABAN GEMINI ---")
    print(response.text)

if __name__ == "__main__":
    tanya_gemini()