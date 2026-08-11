import streamlit as st
import google.generativeai as genai
import os
from render_engine import get_pexels_video, create_voiceover, assemble_video

# ================== CONFIG ==================
st.set_page_config(page_title="AI TikTok Studio", layout="wide")
st.title("🎬 AI-Powered TikTok Content Studio")
st.markdown("Otomatiskan pembuatan konten dari teks ke video hanya dengan satu klik.")

# Inisialisasi session state
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
if "bgm_description" not in st.session_state:
    st.session_state.bgm_description = ""

# ================== SIDEBAR ==================
gemini_key = st.secrets.get("GEMINI_API_KEY", "")
pexels_key = st.secrets.get("PEXELS_API_KEY", "")

with st.sidebar:
    st.header("🔑 API Keys")
    if not gemini_key:
        gemini_key = st.text_input("Gemini API Key", type="password")
    else:
        st.success("✅ Gemini Key terdeteksi")
    if not pexels_key:
        pexels_key = st.text_input("Pexels API Key", type="password")
    else:
        st.success("✅ Pexels Key terdeteksi")

# ================== GENERATE NASKAH ==================
st.header("📝 1. Tentukan Topik")
topic = st.text_input("Masukkan ide konten (contoh: hadist tentang shalawat)")

if st.button("✨ Generate Naskah & Visual Plan"):
    if not gemini_key:
        st.error("Masukkan Gemini API Key di sidebar!")
    elif not topic:
        st.warning("Topik harus diisi!")
    else:
        with st.spinner("AI meracik naskah..."):
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-3.6-flash')

            prompt = f"""
            Kamu adalah scriptwriter & creative director profesional untuk konten edukasi islami TikTok (@ruangteduh.id88).
            Buatkan naskah video lengkap beserta konsep audio-visual dengan TARGET DURASI PRESISI 60 Sampai 70 detik tentang topik: {topic}.

            Gunakan gaya bahasa puitis, syahdu, penuh empati, dan menyentuh batin. Tempo pembacaan dirancang tenang dan perlahan.
            Panjang teks VOICEOVER WAJIB berkisar antara 130 hingga 160 kata agar durasinya pas 60-70 detik saat dibacakan.

            Persyaratan Multi-Scene, Audio & Tipografi Estetik:
            1. Buatkan 3 KEYWORD Pexels berbeda yang relevan, tenang, dan estetik untuk tiap scene.
            2. Buatkan instruksi AUDIO BGM (Musik Latar) instrumen syahdu/relaksasi yang menyentuh hati tanpa vokal untuk melengkapi narasi.
            3. Buatkan 3 BAGIAN TEKS LAYAR (OVERLAY) yang tampil bergantian mengikuti 3 poin isi naskah dengan karakter kuat dan presisi:
               - MAKSIMAL 3-5 KATA PER BARIS (singkat, padat, melipat estetik di tengah layar).
               - Sertakan judul poin utama dan dalil/nomor haditsnya secara terstruktur.
               - Gunakan tanda bintang (*) di sekitar kata kunci utama yang ingin diberi warna highlight menonjol (contoh: *10 Limpahan Rahmat*).

            Berikan format jawaban PERSIS seperti ini (tanpa awalan/akhiran lain):
            VOICEOVER: [Teks narasi lengkap bahasa Indonesia 130-160 kata yang dibaca penuh penjiwaan]
            KEYWORDS: [Keyword 1] | [Keyword 2] | [Keyword 3]
            AUDIO_BGM: [Deskripsi kata kunci musik instrumen syahdu]
            OVERLAY_1: [Frasa ringkas max 4 kata Poin 1 + Tag *Highlight*] / [Nomor Hadits]
            OVERLAY_2: [Frasa ringkas max 4 kata Poin 2 + Tag *Highlight*] / [Nomor Hadits]
            OVERLAY_3: [Frasa ringkas max 4 kata Poin 3 + Tag *Highlight*] / [Nomor Hadits]
            """

            response = model.generate_content(prompt)
            raw_text = response.text

            try:
                vo = raw_text.split("VOICEOVER:")[1].split("KEYWORDS:")[0].strip()
                kw_str = raw_text.split("KEYWORDS:")[1].split("AUDIO_BGM:")[0].strip()
                bgm = raw_text.split("AUDIO_BGM:")[1].split("OVERLAY_1:")[0].strip()
                ov1 = raw_text.split("OVERLAY_1:")[1].split("OVERLAY_2:")[0].strip()
                ov2 = raw_text.split("OVERLAY_2:")[1].split("OVERLAY_3:")[0].strip()
                ov3 = raw_text.split("OVERLAY_3:")[1].strip()

                keywords = [k.strip() for k in kw_str.split("|")]
                segments = [ov1, ov2, ov3]

                st.session_state.voiceover_text = vo
                st.session_state.keywords_list = keywords
                st.session_state.text_segments = segments
                st.session_state.bgm_description = bgm
                st.session_state.step = 2

                st.success("Naskah berhasil dibuat!")
                st.info(f"**Narasi:** {vo[:200]}...\n\n**Visual:** {keywords}\n\n**BGM:** {bgm}\n\n**Overlay:**\n1. {ov1}\n2. {ov2}\n3. {ov3}")

            except Exception as e:
                st.error(f"Gagal parsing naskah: {e}")

# ================== RENDER VIDEO ==================
if st.session_state.step >= 2:
    st.header("⚙️ 2. Render Video")
    if st.button("🚀 Mulai Render Otomatis"):
        if not pexels_key:
            st.error("Pexels API Key belum diisi!")
        else:
            v_paths = []
            for idx, kw in enumerate(st.session_state.keywords_list):
                with st.spinner(f"Mencari video {idx+1}: {kw}"):
                    p = get_pexels_video(kw, pexels_key, output_filename=f"temp_video_{idx}.mp4")
                    v_paths.append(p)

            # Tetap lanjut meskipun ada video yang None (akan di-handle di assemble_video)
            with st.spinner("Membuat narasi suara..."):
                aud_path = create_voiceover(st.session_state.voiceover_text, rate="-5%")

            with st.spinner("Merakit video (highlight, subtitle, BGM)..."):
                final_path = assemble_video(
                    video_paths=v_paths,
                    audio_path=aud_path,
                    text_segments=st.session_state.text_segments,
                    bgm_description=st.session_state.bgm_description,
                    full_narration=st.session_state.voiceover_text  # <- untuk subtitle
                )

                if final_path:
                    st.session_state.final_video_path = final_path
                    st.session_state.step = 3
                    st.success("Video selesai!")
                else:
                    st.error("Render gagal. Cek log untuk detail error.")

# ================== PREVIEW ==================
if st.session_state.step == 3 and st.session_state.final_video_path:
    st.header("📱 3. Preview")
    st.video(st.session_state.final_video_path)
    if st.button("📤 Share ke TikTok (Simulasi)"):
        st.success("Berhasil dikirim ke TikTok!")
