import streamlit as st
import google.generativeai as genai
import json
import re
import os
from render_engine import get_pexels_video, create_voiceover, assemble_video

# ================== CONFIGURASI UTAMA ==================
st.set_page_config(page_title="AI TikTok Studio - Multi-Slide Engine", layout="wide")
st.title("🎬 AI-Powered TikTok Content Studio (Multi-Slide Edition)")
st.markdown("Otomatiskan pembuatan konten TikTok berstruktur slide presisi dari naskah JSON AI.")

# Inisialisasi session state
if "step" not in st.session_state:
    st.session_state.step = 1
if "script_json" not in st.session_state:
    st.session_state.script_json = None
if "final_video_path" not in st.session_state:
    st.session_state.final_video_path = ""

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

# Helper function untuk membersihkan JSON
def clean_json_response(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    return text.strip()

# ================== STEP 1: GENERATE & REVISI NASKAH ==================
st.header("📝 1. Tentukan Topik & Naskah Multi-Slide AI")
topic = st.text_input("Masukkan ide konten (contoh: Doa sehabis Sholat Magrib dan Subuh)")

if st.button("✨ Generate Naskah Multi-Slide"):
    if not gemini_key:
        st.error("Masukkan Gemini API Key di sidebar!")
    elif not topic:
        st.warning("Topik harus diisi!")
    else:
        with st.spinner("Gemini 3.6 Flash meracik skrip JSON Multi-Slide..."):
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-3.6-flash')

            prompt = f"""
            Kamu adalah Scriptwriter & Creative Director profesional untuk konten edukasi TikTok bertaraf tinggi.
            Buatkan naskah terstruktur multi-slide dengan TARGET TOTAL DURASI 60-70 DETIK tentang topik: {topic}.

            Persyaratan Pembuatan JSON:
            1. Buatkan 3 hingga 5 SLIDE berurutan (Hook -> Poin 1 -> Poin 2 -> Outro).
            2. Setiap slide WAJIB memiliki elemen teks terpisah agar tidak kaku:
               - title: Judul singkat slide (misal: "Pertama", "Kedua", atau "BACA SEHABIS SHOLAT")
               - main_text: Isi pesan utama / terjemahan / hook utama
               - highlight: Teks Arab/Latin/Frasa Kunci yang ingin ditonjolkan
               - source: Sumber dalil / HR / keterangan tambahan (opsional)
               - vo_script: Naskah kalimat lengkap yang dibaca voiceover khusus untuk slide ini (durasi pas)
               - bg_keyword: 2-3 kata kunci Pexels visual bahasa Inggris (estetik & relevan)
               - text_color: Kode hex warna teks utama (misal: "#FFFF00" untuk kuning, "#00FFFF" untuk cyan)

            SANGAT PENTING: Berikan jawaban HANYA dalam format JSON valid tanpa teks pengantar atau markdown block tambahan!

            Format JSON Wajib:
            {{
              "bgm_description": "Melodi piano solo syahdu dan lembut",
              "slides": [
                {{
                  "slide_id": 1,
                  "title": "BACA SEHABIS SHOLAT MAGRIB DAN SUBUH",
                  "main_text": "Maka Akan Terhindar Dari Api Neraka",
                  "highlight": "Sebanyak 7 Kali",
                  "source": "",
                  "vo_script": "Baca ini sehabis sholat magrib dan subuh sebanyak tujuh kali, maka akan terhindar dari api neraka.",
                  "bg_keyword": "galaxy space earth cinematic",
                  "text_color": "#FFFF00"
                }}
              ]
            }}
            """

            try:
                response = model.generate_content(prompt)
                clean_str = clean_json_response(response.text)
                data = json.loads(clean_str)

                st.session_state.script_json = data
                st.session_state.step = 2
                st.rerun()

            except Exception as e:
                st.error(f"Gagal memproses JSON dari Gemini 3.6 Flash: {e}")

# --- PANEL DISPLAY & REVISI REALTIME ---
if st.session_state.script_json:
    data = st.session_state.script_json
    st.subheader("📋 Rancangan Slide & Naskah Visual AI (Format JSON):")
    st.caption(f"🎵 **Deskripsi BGM:** {data.get('bgm_description', '-')}")

    for slide in data.get("slides", []):
        with st.expander(f"📌 Slide {slide.get('slide_id')}: {slide.get('title')}", expanded=True):
            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.markdown(f"**🗣️ VO Script:** {slide.get('vo_script')}")
                st.markdown(f"**📝 Main Text:** {slide.get('main_text')}")
                st.markdown(f"**✨ Highlight:** {slide.get('highlight')}")
                if slide.get('source'):
                    st.markdown(f"**📚 Source:** {slide.get('source')}")
            with col_b:
                st.markdown(f"**🎬 Keyword Visual:** `{slide.get('bg_keyword')}`")
                st.markdown(f"**🎨 Warna Teks:** `{slide.get('text_color')}`")

    st.markdown("---")
    st.subheader("💡 Revisi Naskah Realtime")
    revision_instruction = st.text_input("Instruksi revisi (contoh: 'Ubah warna slide 1 jadi cyan' atau 'Perpanjang narasi slide 2')")

    if st.button("🔄 Terapkan Revisi Naskah AI"):
        if not revision_instruction:
            st.warning("Masukkan instruksi revisi terlebih dahulu!")
        else:
            with st.spinner("Gemini 3.6 Flash memperbarui skrip JSON..."):
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-3.6-flash')

                revision_prompt = f"""
                Berikut adalah struktur JSON naskah saat ini:
                {json.dumps(st.session_state.script_json, indent=2)}

                LAKUKAN REVISI berdasarkan instruksi berikut:
                "{revision_instruction}"

                Kembalikan HANYA format JSON valid yang sudah diperbarui tanpa markdown atau pengantar!
                """

                try:
                    resp = model.generate_content(revision_prompt)
                    clean_str = clean_json_response(resp.text)
                    updated_data = json.loads(clean_str)

                    st.session_state.script_json = updated_data
                    st.success("JSON Naskah berhasil direvisi secara realtime!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Gagal memproses revisi JSON: {e}")

# ================== STEP 2: RENDER VIDEO ==================
if st.session_state.step >= 2 and st.session_state.script_json:
    st.header("⚙️ 2. Render Video Multi-Slide")
    st.caption("Klik tombol di bawah jika susunan slide di atas sudah sesuai.")

    if st.button("🚀 Mulai Render Otomatis"):
        if not pexels_key:
            st.error("Pexels API Key belum diisi!")
        else:
            slides_data = st.session_state.script_json.get("slides", [])
            
            with st.spinner("Merakit video Multi-Slide Presisi (Audio-Visual Multi-Scene Sync)..."):
                final_path = assemble_video(
                    slides_data=slides_data, # Mengirim list slide langsung
                    pexels_key=pexels_key,
                    bgm_description=st.session_state.script_json.get("bgm_description", "")
                )

                if final_path:
                    st.session_state.final_video_path = final_path
                    st.session_state.step = 3
                    st.rerun()
                else:
                    st.error("Render gagal. Silakan periksa log server.")

# ================== STEP 3: PREVIEW ==================
if st.session_state.step == 3 and st.session_state.final_video_path:
    st.header("📱 3. Preview Video Result")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.video(st.session_state.final_video_path)
        if st.button("📤 Share ke TikTok (Simulasi)", use_container_width=True):
            st.success("Berhasil dikirim ke TikTok!")
