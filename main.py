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
if "keywords_list" not in st.session_state:
    st.session_state.keywords_list = []
if "text_segments" not in st.session_state:
    st.session_state.text_segments = []
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
        with st.spinner("Meminta AI meracik naskah syahdu & 3 scene visual..."):
            genai.configure(api_key=gemini_key)
            # Menggunakan model 'gemini-1.5-flash' yang stabil
            model = genai.GenerativeModel('gemini-3.6-flash')
            
            prompt = f"""
            Kamu adalah scriptwriter konten edukasi islami bertema ketenangan jiwa untuk TikTok (@ruangteduh.id88).
            Buatkan naskah video dengan TARGET DURASI PRESISI 60 Sampai 70 detik tentang topik: {topic}.

            Gunakan gaya bahasa puitis, syahdu, penuh empati, dan menyentuh batin.
            Panjang teks VOICEOVER WAJIB berkisar antara 130 hingga 160 kata agar durasinya pas 60-70 detik.

            Persyaratan Multi-Scene:
            Buatkan 3 KEYWORD Pexels berbeda dan 3 BAGIAN TEKS LAYAR yang akan tampil bergantian mengikuti 3 poin isi naskah.

            Berikan format jawaban PERSIS seperti ini (tanpa awalan/akhiran lain):
            VOICEOVER: [Teks narasi lengkap bahasa Indonesia 130-160 kata]
            KEYWORDS: [Keyword 1 untuk Poin 1] | [Keyword 2 untuk Poin 2] | [Keyword 3 untuk Poin 3]
            OVERLAY_1: [Teks singkat max 4 kata untuk Poin 1 + Nomor Hadits]
            OVERLAY_2: [Teks singkat max 4 kata untuk Poin 2 + Nomor Hadits]
            OVERLAY_3: [Teks singkat max 4 kata untuk Poin 3 + Nomor Hadits]
            """
            response = model.generate_content(prompt)
            
            try:
                raw_text = response.text
                vo = raw_text.split("VOICEOVER:")[1].split("KEYWORDS:")[0].strip()
                kw_str = raw_text.split("KEYWORDS:")[1].split("OVERLAY_1:")[0].strip()
                ov1 = raw_text.split("OVERLAY_1:")[1].split("OVERLAY_2:")[0].strip()
                ov2 = raw_text.split("OVERLAY_2:")[1].split("OVERLAY_3:")[0].strip()
                ov3 = raw_text.split("OVERLAY_3:")[1].strip()
                
                keywords = [k.strip() for k in kw_str.split("|")]
                segments = [ov1, ov2, ov3]
                
                st.session_state.voiceover_text = vo
                st.session_state.keywords_list = keywords
                st.session_state.text_segments = segments
                st.session_state.step = 2
                st.success("Naskah Multi-Scene berhasil diracik!")
            except Exception as e:
                st.error("Gagal memproses format naskah dari AI. Silakan klik generate lagi.")

# --- 4. BAGIAN 2: PREVIEW NASKAH & RENDERING ---
if st.session_state.step >= 2:
    st.info(f"**Narasi (TTS):** {st.session_state.voiceover_text}\n\n**Visual 3 Scene:** {st.session_state.keywords_list}\n\n**Teks Bergantian:**\n1. {st.session_state.text_segments[0]}\n2. {st.session_state.text_segments[1]}\n3. {st.session_state.text_segments[2]}")

    st.header("⚙️ 2. Proses Render Video")
    if st.button("🚀 Mulai Render Otomatis"):
        if not pexels_key:
            st.error("API Key Pexels belum diisi, Kak!")
        else:
            v_paths = []
            for idx, kw in enumerate(st.session_state.keywords_list):
                with st.spinner(f"Mencari video Pexels Scene {idx+1} ({kw})..."):
                    p = get_pexels_video(kw, pexels_key, output_filename=f"temp_video_{idx}.mp4")
                    v_paths.append(p)
            
            if any(v_paths):
                with st.spinner("Melakukan dubbing suara AI (Edge-TTS)..."):
                    aud_path = create_voiceover(st.session_state.voiceover_text)
                
                with st.spinner("Menggabungkan 3 Video, Audio, Subtitle Bergantian & Backsound Syahdu..."):
                    final_path = assemble_video(
                        v_paths, 
                        aud_path, 
                        st.session_state.text_segments
                    )
                    
                    if final_path:
                        st.session_state.final_video_path = final_path
                        st.session_state.step = 3
                        st.success("Render Multi-Scene Selesai!")
                    else:
                        st.error("Gagal saat proses perakitan video.")
            else:
                st.error("Gagal mengunduh video Pexels.")

# --- 5. BAGIAN 3: VIEWPORT PREVIEW & AI ASSISTANT ---
if st.session_state.step == 3 and st.session_state.final_video_path:
    st.markdown("---")
    st.header("📱 3. Viewport Preview & AI Assistant")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.video(st.session_state.final_video_path)
        if st.button("📤 Share to TikTok (Simulasi API)"):
            st.success("Berhasil didorong ke akun TikTok Kak Donny!")
            
    with col2:
        st.subheader("💬 Ngobrol dengan AI Editor")
        st.caption("Minta revisi visual atau teks di sini.")
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        if user_input := st.chat_input("Tulis revisi di sini..."):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
            
            with st.chat_message("assistant"):
                st.markdown("Fitur revisi AI sedang disesuaikan dengan skema multi-scene. Silakan klik 'Generate Naskah & Visual Plan' jika ingin mengubah topik baru.")
