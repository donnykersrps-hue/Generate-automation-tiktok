import streamlit as st
import google.generativeai as genai
import os
import time
import json
import subprocess
from render_engine import get_pexels_video, create_voiceover, assemble_video

# ================== KONFIGURASI HALAMAN ==================
st.set_page_config(page_title="AI TikTok Studio", layout="wide")
st.title("🎬 AI-Powered TikTok Content Studio")
st.markdown("Otomatiskan pembuatan konten dari teks ke video hanya dengan satu klik.")

# Inisialisasi Session State
if "step" not in st.session_state:
    st.session_state.step = 1
if "voiceover_text" not in st.session_state:
    st.session_state.voiceover_text = ""
if "keywords_list" not in st.session_state:
    st.session_state.keywords_list = []
if "text_segments" not in st.session_state:
    st.session_state.text_segments = []
if "bgm_description" not in st.session_state:
    st.session_state.bgm_description = ""
if "final_video_path" not in st.session_state:
    st.session_state.final_video_path = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "render_status" not in st.session_state:
    st.session_state.render_status = None

# ================== SIDEBAR API KEY ==================
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

# ================== BAGIAN 1: GENERATE NASKAH ==================
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
            KEYWORDS: [Keyword 1 untuk Poin 1] | [Keyword 2 untuk Poin 2] | [Keyword 3 untuk Poin 3]
            AUDIO_BGM: [Deskripsi kata kunci musik instrumen syahdu, contoh: peaceful acoustic piano emotional violin ambient sound]
            OVERLAY_1: [Frasa ringkas max 4 kata Poin 1 + Tag *Highlight*] / [Nomor Hadits]
            OVERLAY_2: [Frasa ringkas max 4 kata Poin 2 + Tag *Highlight*] / [Nomor Hadits]
            OVERLAY_3: [Frasa ringkas max 4 kata Poin 3 + Tag *Highlight*] / [Nomor Hadits]
            """

            response = model.generate_content(prompt)

            try:
                raw_text = response.text

                # Parsing VOICEOVER
                vo = raw_text.split("VOICEOVER:")[1].split("KEYWORDS:")[0].strip()

                # Parsing KEYWORDS
                kw_str = raw_text.split("KEYWORDS:")[1].split("AUDIO_BGM:")[0].strip()
                keywords = [k.strip() for k in kw_str.split("|")]

                # Parsing AUDIO_BGM
                bgm_desc = raw_text.split("AUDIO_BGM:")[1].split("OVERLAY_1:")[0].strip()

                # Parsing OVERLAY
                ov1_raw = raw_text.split("OVERLAY_1:")[1].split("OVERLAY_2:")[0].strip()
                ov2_raw = raw_text.split("OVERLAY_2:")[1].split("OVERLAY_3:")[0].strip()
                ov3_raw = raw_text.split("OVERLAY_3:")[1].strip()

                # Format overlay: "Frasa / Nomor Hadits" -> simpan sebagai tuple (frasa, hadits)
                def parse_overlay(raw):
                    parts = raw.split("/")
                    if len(parts) >= 2:
                        return parts[0].strip(), parts[1].strip()
                    else:
                        return raw.strip(), ""

                ov1, hadits1 = parse_overlay(ov1_raw)
                ov2, hadits2 = parse_overlay(ov2_raw)
                ov3, hadits3 = parse_overlay(ov3_raw)

                # Simpan ke session state
                st.session_state.voiceover_text = vo
                st.session_state.keywords_list = keywords
                st.session_state.text_segments = [ov1, ov2, ov3]  # hanya frasa
                st.session_state.hadits_list = [hadits1, hadits2, hadits3]  # simpan nomor hadits untuk ditampilkan jika perlu
                st.session_state.bgm_description = bgm_desc
                st.session_state.step = 2

                st.success("Naskah Multi-Scene berhasil diracik!")
                st.info(f"**BGM yang disarankan:** {bgm_desc}")

            except Exception as e:
                st.error(f"Gagal memproses format naskah dari AI. Error: {e}")
                st.text(raw_text)  # tampilkan raw untuk debugging

# ================== BAGIAN 2: PREVIEW & RENDER ==================
if st.session_state.step >= 2:
    st.info(f"**Narasi (TTS):** {st.session_state.voiceover_text}\n\n"
            f"**Visual 3 Scene:** {st.session_state.keywords_list}\n\n"
            f"**Teks Bergantian:**\n1. {st.session_state.text_segments[0]}\n2. {st.session_state.text_segments[1]}\n3. {st.session_state.text_segments[2]}")

    st.header("⚙️ 2. Proses Render Video")

    # Tombol Render
    if st.button("🚀 Mulai Render Otomatis"):
        if not pexels_key:
            st.error("API Key Pexels belum diisi, Kak!")
        else:
            # Reset status render
            st.session_state.render_status = None
            st.session_state.final_video_path = ""

            # Tampilkan progress placeholder
            status_placeholder = st.empty()

            # Siapkan data untuk render
            voiceover = st.session_state.voiceover_text
            keywords = st.session_state.keywords_list
            segments = st.session_state.text_segments
            bgm_desc = st.session_state.bgm_description

            # 1. Unduh video Pexels (proses blocking, tapi kita tetap pakai spinner)
            with st.spinner("Mengunduh video dari Pexels..."):
                v_paths = []
                for idx, kw in enumerate(keywords):
                    p = get_pexels_video(kw, pexels_key, output_filename=f"temp_video_{idx}.mp4")
                    v_paths.append(p)
                if not any(v_paths):
                    st.error("Gagal mengunduh video Pexels.")
                    st.stop()

            # 2. Generate TTS
            with st.spinner("Membuat narasi suara..."):
                aud_path = create_voiceover(voiceover)

            # 3. Panggil render video (sekarang blocking, nanti akan kita ubah ke background process)
            # Tapi karena kita belum ubah ke subprocess, kita jalankan langsung dulu.
            # Nanti setelah perubahan ke subprocess, bagian ini akan diganti.
            with st.spinner("Menggabungkan video, audio, & subtitle..."):
                final_path = assemble_video(
                    video_paths=v_paths,
                    audio_path=aud_path,
                    text_segments=segments,
                    bgm_description=bgm_desc,  # parameter baru
                    output_path="final_tiktok.mp4"
                )

                if final_path:
                    st.session_state.final_video_path = final_path
                    st.session_state.step = 3
                    st.success("Render selesai! Silakan lihat preview di bawah.")
                else:
                    st.error("Render gagal. Cek log untuk detail error.")

    # ================== BAGIAN 3: PREVIEW VIDEO ==================
    if st.session_state.step == 3 and st.session_state.final_video_path:
        st.markdown("---")
        st.header("📱 3. Viewport Preview & AI Assistant")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.video(st.session_state.final_video_path)
            if st.button("📤 Share to TikTok (Simulasi API)"):
                st.success("Berhasil didorong ke akun TikTok!")

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
