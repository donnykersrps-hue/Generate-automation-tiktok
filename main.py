import streamlit as st
import json
import os
import google.generativeai as genai
from render_engine import get_pexels_video, create_voiceover, assemble_video

# ================== 1. PAGE CONFIG & CUSTOM CSS (MIDNIGHT SYAHDU) ==================
st.set_page_config(
    page_title="AI TikTok Studio - Midnight Syahdu Edition",
    page_icon="🌙",
    layout="wide"
)

# Custom CSS Dark Theme Midnight Syahdu & Neon Interactive Glows
css_code = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Background Utama App Dark Midnight */
    .stApp {
        background: linear-gradient(180deg, #0B0F19 0%, #111827 100%);
        color: #F8FAFC;
    }

    /* Text Header Color Adjustments */
    h1, h2, h3, h4, h5, h6, label {
        color: #F8FAFC !important;
        font-weight: 800 !important;
    }

    /* Sidebar Dark Styling */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid #1E293B;
    }

    /* Card Box / Expander Glassmorphism Base Styling */
    div[data-testid="stExpander"], div.stMarkdownContainer > div {
        background-color: #1E293B !important;
        border-radius: 14px;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        color: #F8FAFC !important;
        transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    /* Interaksi Full-Body Neon Ungu saat Dropdown (Expander) Disentuh Kursor */
    div[data-testid="stExpander"]:hover {
        background: linear-gradient(135deg, #2E1065 0%, #1E1B4B 100%) !important;
        border-color: #C084FC !important;
        box-shadow: 0 0 25px rgba(192, 132, 252, 0.65), inset 0 0 15px rgba(168, 85, 247, 0.3) !important;
        transform: translateY(-2px);
    }

    /* Memastikan Bagian Dalam Expander (Header & Body Content) Ikut Berubah Warna */
    div[data-testid="stExpander"]:hover * {
        color: #F3E8FF !important;
    }

    /* Tombol Interaksi Neon Glowing */
    div.stButton > button {
        background: linear-gradient(135deg, #00FF9D 0%, #00E5FF 100%) !important;
        color: #020617 !important;
        font-weight: 800 !important;
        font-size: 16px !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 12px 28px !important;
        box-shadow: 0 0 15px rgba(0, 255, 157, 0.4) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        width: 100%;
    }

    /* Hover State Interaksi Neon Terang Nyala di Atas Mode Gelap */
    div.stButton > button:hover {
        transform: translateY(-2px) scale(1.01);
        box-shadow: 0 0 30px rgba(0, 255, 157, 0.9), 0 0 45px rgba(0, 229, 255, 0.7) !important;
        color: #000000 !important;
    }

    /* Active Click State */
    div.stButton > button:active {
        transform: translateY(1px);
        box-shadow: 0 0 12px rgba(0, 255, 157, 0.9) !important;
    }

    /* Text Input & Text Area Dark Theme Styling */
    .stTextInput input, .stTextArea textarea {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #00E5FF !important;
        box-shadow: 0 0 12px rgba(0, 229, 255, 0.5) !important;
    }
</style>
"""

st.markdown(css_code, unsafe_allow_html=True)

# ================== 2. SIDEBAR API KEYS ==================
with st.sidebar:
    st.title("🔑 API Configuration")
    gemini_key = st.text_input("Gemini API Key", value=os.getenv("GEMINI_API_KEY", ""), type="password")
    pexels_key = st.text_input("Pexels API Key", value=os.getenv("PEXELS_API_KEY", ""), type="password")
    st.info("Aplikasi menggunakan tema **Midnight Syahdu Aesthetic** dengan aksen **Neon Interactive Glow**.")

# ================== 3. MAIN HEADER ==================
st.title("🎬 AI TikTok Content Studio")
st.caption("Otomatisasi pembuatan video multi-slide TikTok dengan arsitektur visual presisi & suara AI.")

# Initialize Session State Data Default
if "slides_data" not in st.session_state:
    st.session_state.slides_data = [
        {
            "slide_id": 1,
            "title": "RAJA DARI SEGALA ISTIGHFAR",
            "vo_script": "Tahukah kamu ada satu doa istighfar yang dijuluki sebagai Sayyidul Istighfar atau Rajanya Istighfar? Barangsiapa membacanya dengan yakin, lalu meninggal di hari itu, Rasulullah menjamin ia termasuk penghuni surga.",
            "main_text": "Doa Pengampun Dosa Paling Utama dalam Islam",
            "highlight": "Jaminan Masuk Surga",
            "source": "HR. Bukhari No. 6306",
            "bg_keyword": "cinematic mosque sunset aesthetic",
            "text_color": "#FFD700"
        },
        {
            "slide_id": 2,
            "title": "BACAAN SAYYIDUL ISTIGHFAR",
            "vo_script": "Bacaannya diawali dengan: Allahumma anta robbii laa ilaaha illaa anta, kholaqtanii wa anaa 'abduka. Doa ini berisi pengakuan tulus bahwa Allah adalah Tuhan pencipta kita, dan kita mengakui seluruh dosa serta nikmat-Nya.",
            "main_text": "Pengakuan Tulus atas Dosa & Nikmat Allah",
            "highlight": "Allahumma Anta Rabbi Laa Ilaha Illa Anta...",
            "source": "Lafadz Doa Utama",
            "bg_keyword": "calm starry night sky aesthetic",
            "text_color": "#00FFFF"
        },
        {
            "slide_id": 3,
            "title": "KEUTAMAAN LUAR BIASA",
            "vo_script": "Keutamaannya sangat luar biasa. Jika dibaca di pagi hari dengan penuh keyakinan lalu meninggal sebelum petang, atau dibaca petang hari lalu meninggal sebelum Subuh, Allah jamin dirinya menjadi penghuni surga.",
            "main_text": "Dibaca Pagi Hari & Petang Hari",
            "highlight": "Meninggal Hari Itu = Ahli Surga",
            "source": "Sahih Bukhari",
            "bg_keyword": "peaceful clouds rays light cinematic",
            "text_color": "#00FF7F"
        },
        {
            "slide_id": 4,
            "title": "AMALKAN RUTIN SHUBUH & MAGHRIB",
            "vo_script": "Mulai hari ini, amalkan doa ini setiap selesai sholat Subuh dan Maghrib. Simpan video ini agar tidak lupa, dan bagikan ke orang-orang tersayang agar menjadi pahala jariyah yang terus mengalir.",
            "main_text": "Simpan & Bagikan Doa Ini",
            "highlight": "Jadikan Amalan Harian",
            "source": "Pahala Jariyah",
            "bg_keyword": "person praying peaceful sunset silhouette",
            "text_color": "#FFFFFF"
        }
    ]

# ================== 4. STEP 1: NASKAH MULTI-SLIDE GEMINI AI ==================
st.header("📝 1. Tentukan Topik & Naskah Multi-Slide AI")
topic_input = st.text_input("Masukkan ide konten", value="Tata cara Sholat Dhuha")

if st.button("✨ Generate Naskah Multi-Slide"):
    if not gemini_key:
        st.error("Harap masukkan Gemini API Key di sidebar terlebih dahulu!")
    else:
        with st.spinner("🤖 Gemini AI sedang meracik naskah & konsep visual multi-slide..."):
            try:
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel("gemini-3.6-flash")
                
                prompt = f"""
                Kamu adalah pakar influencer TikTok profesional. Buatkan naskah video multi-slide TikTok berjumlah 4 slide tentang topik: "{topic_input}".
                
                Kembalikan persis dalam format JSON murni Array of Objects tanpa format markdown ```json ``` dengan skema kunci:
                [
                  {{
                    "slide_id": 1,
                    "title": "JUDUL SLIDE 1 (2-4 KATA KAPITAL)",
                    "vo_script": "Naskah narasi vokal yang menarik dan berbobot (2-3 kalimat)",
                    "main_text": "Teks utama penjelasan singkat ringkas",
                    "highlight": "Frasa kunci paling mencolok",
                    "source": "Sumber riwayat/dalil/sumber informasi",
                    "bg_keyword": "kata kunci visual pexels bahasa inggris misal: cinematic mosque sunset aesthetic",
                    "text_color": "#FFD700"
                  }}
                ]
                """
                
                response = model.generate_content(prompt)
                raw_text = response.text.replace("```json", "").replace("```", "").strip()
                generated_json = json.loads(raw_text)
                
                st.session_state.slides_data = generated_json
                st.toast("🎉 Naskah berhasil dibuat oleh Gemini AI!", icon="✨")
            except Exception as e:
                st.error(f"Gagal meng-generate naskah: {e}")

# Display Slides Preview
st.subheader("📋 Rancangan Slide & Naskah Visual AI:")
for slide in st.session_state.slides_data:
    with st.expander(f"📌 Slide {slide.get('slide_id', 1)}: {slide.get('title', '')}"):
        st.write(f"**🗣️ VO Script:** {slide.get('vo_script', '')}")
        st.write(f"**📝 Main Text:** {slide.get('main_text', '')}")
        st.write(f"**✨ Highlight:** {slide.get('highlight', '')}")
        st.write(f"**📚 Source:** {slide.get('source', '')}")
        st.write(f"**🎬 Keyword Visual:** `{slide.get('bg_keyword', '')}`")

# ================== 5. STEP 2: RENDER VIDEO ==================
st.header("⚙️ 2. Render Video Multi-Slide")
st.write("Klik tombol di bawah untuk mulai membuat video otomatis.")

if st.button("🚀 Mulai Render Otomatis"):
    if not pexels_key:
        st.error("Harap masukkan Pexels API Key di sidebar terlebih dahulu!")
    else:
        with st.spinner("⏳ Sedang merekam suara AI, mengunduh background visual, dan menyusun subtitle karaoke..."):
            final_video_path = assemble_video(
                slides_data=st.session_state.slides_data,
                pexels_key=pexels_key,
                output_path="final_tiktok.mp4"
            )
            
            if final_video_path and os.path.exists(final_video_path):
                st.session_state.rendered_video = final_video_path
                st.success("🎉 Video Multi-Slide Berhasil Dirender Sempurna!")
            else:
                st.error("Gagal melakukan render video. Silakan periksa log aplikasi.")

# ================== 6. STEP 3: PREVIEW RESULT (30% COMPACT VIEWPORT) ==================
if "rendered_video" in st.session_state and os.path.exists(st.session_state.rendered_video):
    st.header("📱 3. Preview Video Result")
    col_left, col_video, col_right = st.columns([1.1, 1, 1.1])
    with col_video:
        st.video(st.session_state.rendered_video)
