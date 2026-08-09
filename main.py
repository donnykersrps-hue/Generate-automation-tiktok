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
if "overlay_text" not in st.session_state:
    st.session_state.overlay_text = ""
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
        with st.spinner("Meminta AI meracik naskah syahdu 60-70 detik..."):
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-3.6-flash')
            
            prompt = f"""
            Kamu adalah scriptwriter konten edukasi islami bertema ketenangan jiwa untuk TikTok (@ruangteduh.id88).
            Buatkan naskah video dengan TARGET DURASI PRESISI 60 Sampai 70 detik tentang topik: {topic}.

            Gunakan gaya bahasa puitis, syahdu, penuh empati, dan menyentuh batin. Tempo pembacaan dirancang tenang dan perlahan.
            Panjang teks VOICEOVER WAJIB berkisar antara 130 hingga 160 kata agar durasinya pas 60-70 detik saat diucapkan.

            Persyaratan Struktur Konten:
            1. HOOK (00:00 - 00:08): Kalimat pembuka yang menghentikan scroll penonton.
            2. ISI KONTEN (3 POIN):
               - Poin Pertama + Cantumkan Dalil/Hadits Sahihnya.
               - Poin Kedua + Cantumkan Dalil/Hadits Sahihnya.
               - Poin Ketiga + Cantumkan Dalil/Hadits Sahihnya.
            3. PENUTUP / CTA (00:50 - 00:70): Pesan hangat penenang hati dan ajakan bertindak (save/amalkan).

            Berikan format jawaban PERSIS seperti ini (tanpa awalan/akhiran lain):
            VOICEOVER: [Teks narasi lengkap bahasa Indonesia 130-160 kata yang dibaca penuh penjiwaan, sertakan bacaan nomor haditsnya secara lisan]
            KEYWORD: [1-2 kata kunci bahasa Inggris yang relevan untuk Pexels, contoh: galaxy earth, green nature, peaceful rain]
            OVERLAY_TEXT: [Kumpulan frasa pendek MAKSIMAL 3-5 KATA PER BARIS dipisah tanda garis miring (/), buat melipat rapat dan estetik di tengah layar]
            """
            response = model.generate_content(prompt)
            
            # Memecah respon Gemini dengan aman untuk VOICEOVER, KEYWORD, dan OVERLAY_TEXT
            try:
                raw_text = response.text
                vo = raw_text.split("VOICEOVER:")[1].split("KEYWORD:")[0].strip()
                kw = raw_text.split("KEYWORD:")[1].split("OVERLAY_TEXT:")[0].strip()
                overlay = raw_text.split("OVERLAY_TEXT:")[1].strip()
                
                # Ubah tanda garis miring (/) di OVERLAY_TEXT menjadi baris baru
                formatted_overlay = overlay.replace(" / ", "\n").replace("/", "\n")
                
                # Simpan ke memori aplikasi
                st.session_state.voiceover_text = vo
                st.session_state.pexels_keyword = kw
                st.session_state.overlay_text = formatted_overlay
                st.session_state.step = 2
                st.success("Naskah dan konsep visual berhasil dibuat!")
            except Exception as e:
                st.error("Gagal memproses format naskah dari AI. Silakan klik generate lagi.")

# --- 4. BAGIAN 2: PREVIEW NASKAH & RENDERING ---
if st.session_state.step >= 2:
    st.info(f"**Narasi (TTS):** {st.session_state.voiceover_text}\n\n**Video Pencarian (Pexels):** {st.session_state.pexels_keyword}\n\n**Teks Layar (Overlay):**\n{st.session_state.overlay_text}")

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
                
                with st.spinner("Menggabungkan Video, Audio & Subtitle Estetik..."):
                    # Gunakan overlay_text untuk tampilan teks layar melipat
                    text_to_render = st.session_state.overlay_text if st.session_state.overlay_text else st.session_state.voiceover_text
                    final_path = assemble_video(vid_path, aud_path, text_to_render)
                    
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
                with st.spinner("Menganalisa perintah Kakak..."):
                    genai.configure(api_key=gemini_key)
                    model = genai.GenerativeModel('gemini-3.6-flash')
                    
                    prompt = f"""
                    Kamu adalah asisten editor video.
                    Saat ini user memiliki naskah narasi: "{st.session_state.voiceover_text}"
                    Visual video dicari menggunakan keyword: "{st.session_state.pexels_keyword}"
                    Teks layar: "{st.session_state.overlay_text}"
                    
                    User meminta revisi: "{user_input}"
                    
                    Berikan output dengan format persis ini:
                    UPDATE_VOICEOVER: [teks narasi (baru/lama)]
                    UPDATE_KEYWORD: [keyword pexels bahasa inggris (baru/lama)]
                    UPDATE_OVERLAY: [teks layar pendek dipisah tanda garis miring (/) (baru/lama)]
                    PESAN: [Respon ramah ke user bahwa kamu sudah memperbaruinya]
                    """
                    
                    response = model.generate_content(prompt)
                    try:
                        pesan = response.text.split("PESAN:")[1].strip()
                        new_vo = response.text.split("UPDATE_VOICEOVER:")[1].split("UPDATE_KEYWORD:")[0].strip()
                        new_kw = response.text.split("UPDATE_KEYWORD:")[1].split("UPDATE_OVERLAY:")[0].strip()
                        new_ov = response.text.split("UPDATE_OVERLAY:")[1].split("PESAN:")[0].strip()
                        
                        st.markdown(pesan)
                        st.session_state.chat_history.append({"role": "assistant", "content": pesan})
                        
                        if new_vo != st.session_state.voiceover_text or new_kw != st.session_state.pexels_keyword or new_ov != st.session_state.overlay_text:
                            st.session_state.voiceover_text = new_vo
                            st.session_state.pexels_keyword = new_kw
                            st.session_state.overlay_text = new_ov.replace(" / ", "\n").replace("/", "\n")
                            st.info("🔄 Parameter naskah/visual telah diperbarui! Silakan klik 'Mulai Render Otomatis' lagi.")
                            st.session_state.step = 2
                            st.rerun()
                            
                    except Exception as e:
                        st.markdown("Maaf Kak, format revisinya kurang jelas. Boleh diperjelas lagi?")
