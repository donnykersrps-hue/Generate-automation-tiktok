import streamlit as st
import google.generativeai as genai
import os
from render_engine import get_pexels_video, create_voiceover, assemble_video

# --- 1. SETUP & KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AI TikTok Studio", layout="wide")
st.title("🎬 AI-Powered TikTok Content Studio")
st.markdown("Otomatiskan pembuatan konten dari teks ke video hanya dengan satu klik.")

# Inisialisasi Session State (Agar data tidak hilang saat layar me-refresh)
if "step" not in st.session_state:
    st.session_state.step = 1
if "voiceover_text" not in st.session_state:
    st.session_state.voiceover_text = ""
if "pexels_keyword" not in st.session_state:
    st.session_state.pexels_keyword = ""
if "final_video_path" not in st.session_state:
    st.session_state.final_video_path = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 2. SIDEBAR (Pengaturan API Key) ---
gemini_key = st.secrets.get("GEMINI_API_KEY", "")
pexels_key = st.secrets.get("PEXELS_API_KEY", "")

with st.sidebar:
    st.header("🔑 Pengaturan API Key")
    if not gemini_key:
        gemini_key = st.text_input("Gemini API Key", type="password")
    else:
        st.success("✅ Gemini Key Terdeteksi (Secrets)")

    if not pexels_key:
        pexels_key = st.text_input("Pexels API Key", type="password")
    else:
        st.success("✅ Pexels Key Terdeteksi (Secrets)")

    st.markdown("---")
    st.caption("Aplikasi berjalan menggunakan Serverless Cloud.")
    
# --- 3. BAGIAN 1: PEMBUATAN NASKAH & STORYBOARD ---
st.header("📝 1. Tentukan Topik Konten")
topic = st.text_input("Masukkan ide konten (contoh: Fakta unik game GTA, arsitektur rumah modern, dll)")

if st.button("✨ Generate Naskah & Visual Plan"):
    if not gemini_key:
        st.error("Masukkan Gemini API Key di sidebar terlebih dahulu ya, Kak!")
    elif not topic:
        st.warning("Topiknya diisi dulu dong, Kak.")
    else:
        with st.spinner("Meminta AI meracik naskah..."):
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Prompt yang dikunci formatnya agar mudah dibaca oleh Python
            prompt = f"""
            Buatkan rancangan 1 scene video TikTok tentang: {topic}.
            Durasi narasi sekitar 15-20 detik.
            Berikan format jawaban persis seperti ini (tanpa awalan/akhiran lain):
            VOICEOVER: [Teks narasi bahasa Indonesia yang menarik dan natural]
            KEYWORD: [1-2 kata kunci bahasa Inggris yang relevan untuk cari footage di Pexels]
            """
            response = model.generate_content(prompt)
            
            # Memecah respon Gemini untuk diambil Teks dan Keyword-nya
            try:
                vo = response.text.split("VOICEOVER:")[1].split("KEYWORD:")[0].strip()
                kw = response.text.split("KEYWORD:")[1].strip()
                
                # Simpan ke memori aplikasi
                st.session_state.voiceover_text = vo
                st.session_state.pexels_keyword = kw
                st.session_state.step = 2
                st.success("Naskah dan konsep visual berhasil dibuat!")
            except Exception as e:
                st.error("Gagal memproses format naskah dari AI. Silakan klik generate lagi.")

# --- 4. BAGIAN 2: PREVIEW NASKAH & RENDERING ---
if st.session_state.step >= 2:
    st.info(f"**Narasi (TTS):** {st.session_state.voiceover_text}\n\n**Video Pencarian (Pexels):** {st.session_state.pexels_keyword}")

    st.header("⚙️ 2. Proses Render Video")
    if st.button("🚀 Mulai Render Otomatis"):
        if not pexels_key:
            st.error("API Key Pexels belum diisi, Kak!")
        else:
            with st.spinner(f"Mencari video Pexels dengan kata kunci '{st.session_state.pexels_keyword}'..."):
                vid_path = get_pexels_video(st.session_state.pexels_keyword, pexels_key)
            
            if vid_path:
                with st.spinner("Melakukan dubbing suara AI (Edge-TTS)..."):
                    aud_path = create_voiceover(st.session_state.voiceover_text)
                
                with st.spinner("Menggabungkan Video, Audio & Subtitle... (Ini butuh beberapa detik)"):
                    final_path = assemble_video(vid_path, aud_path, st.session_state.voiceover_text)
                    
                    if final_path:
                        st.session_state.final_video_path = final_path
                        st.session_state.step = 3
                        st.success("Render Selesai!")
                    else:
                        st.error("Gagal saat proses perakitan video.")
            else:
                st.error("Video tidak ditemukan di Pexels. Coba ngobrol dengan AI di bawah untuk ganti keyword.")

# --- 5. BAGIAN 3: VIEWPORT PREVIEW & AI EDITOR CHAT ---
if st.session_state.step == 3 and st.session_state.final_video_path:
    st.markdown("---")
    st.header("📱 3. Viewport Preview & AI Assistant")
    
    # Membagi layar jadi 2 kolom: Kiri (Video), Kanan (Chat)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.video(st.session_state.final_video_path)
        if st.button("📤 Share to TikTok (Simulasi API)"):
            st.success("Berhasil didorong ke akun TikTok Kak Donny!")
            
    with col2:
        st.subheader("💬 Ngobrol dengan AI Editor")
        st.caption("Minta revisi visual atau teks di sini (contoh: 'Gem, ganti videonya jadi mobil sport').")
        
        # Tampilkan riwayat chat
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # Input chat dari Kak Donny
        if user_input := st.chat_input("Tulis revisi di sini..."):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
            
            with st.chat_message("assistant"):
                with st.spinner("Menganalisa perintah Kakak..."):
                    genai.configure(api_key=gemini_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    # AI diberi "Konteks" tentang video saat ini agar dia paham apa yang sedang diedit
                    prompt = f"""
                    Kamu adalah asisten editor video.
                    Saat ini user memiliki naskah: "{st.session_state.voiceover_text}"
                    Dan visual video dicari menggunakan keyword: "{st.session_state.pexels_keyword}"
                    
                    User meminta revisi: "{user_input}"
                    
                    Jika user minta ubah visual, ganti keywordnya. Jika minta ubah teks, ganti naskahnya.
                    Berikan output dengan format persis ini:
                    UPDATE_VOICEOVER: [teks narasi (baru/lama)]
                    UPDATE_KEYWORD: [keyword pexels bahasa inggris (baru/lama)]
                    PESAN: [Respon ramah ke user bahwa kamu sudah memperbaruinya]
                    """
                    
                    response = model.generate_content(prompt)
                    try:
                        pesan = response.text.split("PESAN:")[1].strip()
                        new_vo = response.text.split("UPDATE_VOICEOVER:")[1].split("UPDATE_KEYWORD:")[0].strip()
                        new_kw = response.text.split("UPDATE_KEYWORD:")[1].split("PESAN:")[0].strip()
                        
                        st.markdown(pesan)
                        st.session_state.chat_history.append({"role": "assistant", "content": pesan})
                        
                        # Jika ada perubahan parameter, update session_state dan refresh layar
                        if new_vo != st.session_state.voiceover_text or new_kw != st.session_state.pexels_keyword:
                            st.session_state.voiceover_text = new_vo
                            st.session_state.pexels_keyword = new_kw
                            st.info("🔄 Parameter naskah/visual telah diperbarui! Silakan klik 'Mulai Render Otomatis' lagi untuk menerapkan perubahan.")
                            st.session_state.step = 2 # Mundurkan step agar tombol render muncul
                            st.rerun() # Refresh Streamlit seketika
                            
                    except Exception as e:
                        st.markdown("Maaf Kak, format revisinya kurang jelas. Boleh diperjelas lagi?")
