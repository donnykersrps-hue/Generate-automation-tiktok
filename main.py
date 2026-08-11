import streamlit as st
import google.generativeai as genai
import os
from render_engine import get_pexels_video, create_voiceover, assemble_video

# ================== CONFIGURASI UTAMA ==================
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

# ================== SIDEBAR (API KEYS) ==================
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

# ================== STEP 1: GENERATE & REVISI NASKAH ==================
st.header("📝 1. Tentukan Topik & Naskah AI")
topic = st.text_input("Masukkan ide konten (contoh: hadist tentang shalawat)")

if st.button("✨ Generate Naskah awal"):
    if not gemini_key:
        st.error("Masukkan Gemini API Key di sidebar!")
    elif not topic:
        st.warning("Topik harus diisi!")
    else:
        with st.spinner("AI Gemini Flash meracik naskah & rancangan visual..."):
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-3.6-flash')

            prompt = f"""
            Kamu adalah scriptwriter & creative director profesional untuk konten edukasi islami TikTok (@ruangteduh.id88).
            Buatkan naskah video lengkap beserta konsep audio-visual dengan TARGET DURASI PRESISI 60 Sampai 70 detik tentang topik: {topic}.

            Gunakan gaya bahasa puitis, syahdu, penuh empati, dan menyentuh batin.
            Panjang teks VOICEOVER WAJIB berkisar antara 130 hingga 160 kata.

            Persyaratan Multi-Scene & Overlay:
            1. Buatkan 3 KEYWORD Pexels berbeda yang relevan dan estetik.
            2. Buatkan instruksi AUDIO BGM instrumen syahdu.
            3. Buatkan 3 BAGIAN TEKS LAYAR (OVERLAY) singkat (3-5 kata per baris) + sebutkan nomor hadits/dalilnya.
               Gunakan tanda bintang (*) untuk penanda kata kunci utama.

            Berikan format jawaban PERSIS seperti ini:
            VOICEOVER: [Teks narasi 130-160 kata]
            KEYWORDS: [Keyword 1] | [Keyword 2] | [Keyword 3]
            AUDIO_BGM: [Deskripsi BGM]
            OVERLAY_1: [Frasa ringkas Poin 1 + Tag *Highlight*] / [Nomor Hadits]
            OVERLAY_2: [Frasa ringkas Poin 2 + Tag *Highlight*] / [Nomor Hadits]
            OVERLAY_3: [Frasa ringkas Poin 3 + Tag *Highlight*] / [Nomor Hadits]
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

                st.session_state.voiceover_text = vo
                st.session_state.keywords_list = [k.strip() for k in kw_str.split("|")]
                st.session_state.text_segments = [ov1, ov2, ov3]
                st.session_state.bgm_description = bgm
                st.session_state.step = 2
                st.rerun()

            except Exception as e:
                st.error(f"Gagal parsing naskah: {e}")

# --- PANEL DISPLAY & REVISI REALTIME (TANPA RENDER) ---
if st.session_state.voiceover_text:
    st.subheader("📋 Hasil Rancangan Naskah & Visual AI Saat Ini:")
    st.info(
        f"**🗣️ Narasi Voiceover ({len(st.session_state.voiceover_text.split())} kata):**\n{st.session_state.voiceover_text}\n\n"
        f"**🎬 Keywords Visual Pexels:** {st.session_state.keywords_list}\n\n"
        f"**🎵 BGM:** {st.session_state.bgm_description}\n\n"
        f"**📌 Header / Overlay Teks Emas:**\n1. {st.session_state.text_segments[0]}\n2. {st.session_state.text_segments[1]}\n3. {st.session_state.text_segments[2]}"
    )

    st.markdown("---")
    st.subheader("💡 Revisi Naskah Realtime (Instan Tanpa Render Video)")
    revision_instruction = st.text_input("Masukkan instruksi revisi untuk Gemini Flash (contoh: 'Ganti nada jadi lebih bersemangat' atau 'Perpendek naskah')")

    if st.button("🔄 Terapkan Revisi Naskah AI"):
        if not revision_instruction:
            st.warning("Masukkan instruksi revisinya terlebih dahulu!")
        else:
            with st.spinner("Gemini Flash meracik ulang naskah secara realtime..."):
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-3.6-flash')

                revision_prompt = f"""
                Berikut adalah naskah & rancangan visual TikTok saat ini:
                VOICEOVER: {st.session_state.voiceover_text}
                KEYWORDS: {' | '.join(st.session_state.keywords_list)}
                AUDIO_BGM: {st.session_state.bgm_description}
                OVERLAY_1: {st.session_state.text_segments[0]}
                OVERLAY_2: {st.session_state.text_segments[1]}
                OVERLAY_3: {st.session_state.text_segments[2]}

                LAKUKAN REVISI berdasarkan instruksi user berikut:
                "{revision_instruction}"

                Tetap pertahankan format jawaban PERSIS seperti ini:
                VOICEOVER: [Teks narasi revisi 130-160 kata]
                KEYWORDS: [Keyword 1] | [Keyword 2] | [Keyword 3]
                AUDIO_BGM: [Deskripsi BGM]
                OVERLAY_1: [Frasa ringkas Poin 1 + Tag *Highlight*] / [Nomor Hadits]
                OVERLAY_2: [Frasa ringkas Poin 2 + Tag *Highlight*] / [Nomor Hadits]
                OVERLAY_3: [Frasa ringkas Poin 3 + Tag *Highlight*] / [Nomor Hadits]
                """

                resp = model.generate_content(revision_prompt)
                raw_text = resp.text

                try:
                    vo = raw_text.split("VOICEOVER:")[1].split("KEYWORDS:")[0].strip()
                    kw_str = raw_text.split("KEYWORDS:")[1].split("AUDIO_BGM:")[0].strip()
                    bgm = raw_text.split("AUDIO_BGM:")[1].split("OVERLAY_1:")[0].strip()
                    ov1 = raw_text.split("OVERLAY_1:")[1].split("OVERLAY_2:")[0].strip()
                    ov2 = raw_text.split("OVERLAY_2:")[1].split("OVERLAY_3:")[0].strip()
                    ov3 = raw_text.split("OVERLAY_3:")[1].strip()

                    st.session_state.voiceover_text = vo
                    st.session_state.keywords_list = [k.strip() for k in kw_str.split("|")]
                    st.session_state.text_segments = [ov1, ov2, ov3]
                    st.session_state.bgm_description = bgm

                    st.success("Naskah berhasil direvisi secara realtime!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Gagal memproses revisi: {e}")

# ================== STEP 2: RENDER VIDEO ==================
if st.session_state.step >= 2:
    st.header("⚙️ 2. Render Video")
    st.caption("Klik tombol di bawah HANYA JIKA naskah di atas sudah 100% pas.")
    if st.button("🚀 Mulai Render Otomatis"):
        if not pexels_key:
            st.error("Pexels API Key belum diisi!")
        else:
            v_paths = []
            for idx, kw in enumerate(st.session_state.keywords_list):
                with st.spinner(f"Mencari video {idx+1}: {kw}"):
                    p = get_pexels_video(kw, pexels_key, output_filename=f"temp_video_{idx}.mp4")
                    v_paths.append(p)

            with st.spinner("Membuat narasi suara AI..."):
                aud_path = create_voiceover(st.session_state.voiceover_text, rate="-5%")

            with st.spinner("Merakit video (Header Emas, Subtitle Cream & BGM 30%)..."):
                final_path = assemble_video(
                    video_paths=v_paths,
                    audio_path=aud_path,
                    text_segments=st.session_state.text_segments,
                    bgm_description=st.session_state.bgm_description,
                    full_narration=st.session_state.voiceover_text
                )

                if final_path:
                    st.session_state.final_video_path = final_path
                    st.session_state.step = 3
                    st.rerun()
                else:
                    st.error("Render gagal. Silakan periksa log server.")

# ================== STEP 3: PREVIEW (VIEWPORT HP RAMPING) ==================
if st.session_state.step == 3 and st.session_state.final_video_path:
    st.header("📱 3. Preview")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.video(st.session_state.final_video_path)
        if st.button("📤 Share ke TikTok (Simulasi)", use_container_width=True):
            st.success("Berhasil dikirim ke TikTok!")
