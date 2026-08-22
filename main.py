import streamlit as st
import json
import os
from render_engine import get_pexels_video, create_voiceover, assemble_video

# ================== 1. PAGE CONFIG & CUSTOM CSS ==================
st.set_page_config(
    page_title="AI TikTok Studio - Warm Aesthetic Edition",
    page_icon="🕌",
    layout="wide"
)

# Custom CSS Theme Warm White & Neon Interactive Buttons
css_code = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .stApp {
        background: linear-gradient(180deg, #F8F9FA 0%, #F1F3F6 100%);
        color: #2D3748;
    }

    h1, h2, h3 {
        color: #1A202C !important;
        font-weight: 800 !important;
    }

    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0;
    }

    div.stButton > button {
        background: linear-gradient(135deg, #00FF9D 0%, #00E5FF 100%) !important;
        color: #0F172A !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 12px 28px !important;
        box-shadow: 0 4px 15px rgba(0, 255, 157, 0.4) !important;
        transition: all 0.3s ease-in-out !important;
        width: 100%;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 25px rgba(0, 255, 157, 0.8), 0 0 35px rgba(0, 229, 255, 0.6) !important;
        color: #000000 !important;
    }

    .stTextInput input, .stTextArea textarea {
        background-color: #FFFFFF !important;
        color: #1A202C !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
    }
</style>
"""

st.markdown(css_code, unsafe_allow_html=True)

# ================== 2. SIDEBAR API KEYS ==================
with st.sidebar:
    st.title("🔑 API Configuration")
    gemini_key = st.text_input("Gemini API Key", value=os.getenv("GEMINI_API_KEY", ""), type="password")
    pexels_key = st.text_input("Pexels API Key", value=os.getenv("PEXELS_API_KEY", ""), type="password")
    st.info("Aplikasi menggunakan tema **Warm Pure Aesthetic** dengan aksen **Neon Interactive Buttons**.")

# ================== 3. MAIN HEADER ==================
st.title("🎬 AI TikTok Content Studio")
st.caption("Otomatisasi pembuatan video multi-slide TikTok dengan arsitektur visual presisi & suara AI.")

# Initialize Session State Data
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

# ================== 4. STEP 1: NASKAH MULTI-SLIDE ==================
st.header("📝 1. Tentukan Topik & Naskah Multi-Slide AI")
topic_input = st.text_input("Masukkan ide konten", value="Doa sehabis Sholat Magrib dan Subuh")

if st.button("✨ Generate Naskah Multi-Slide"):
    st.toast("Naskah berhasil di-generate secara otomatis!", icon="✨")

# Display Slides Preview
st.subheader("📋 Rancangan Slide & Naskah Visual AI:")
for slide in st.session_state.slides_data:
    with st.expander(f"📌 Slide {slide['slide_id']}: {slide['title']}"):
        st.write(f"**🗣️ VO Script:** {slide['vo_script']}")
        st.write(f"**📝 Main Text:** {slide['main_text']}")
        st.write(f"**✨ Highlight:** {slide['highlight']}")
        st.write(f"**📚 Source:** {slide['source']}")
        st.write(f"**🎬 Keyword Visual:** `{slide['bg_keyword']}`")

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

# ================== 6. STEP 3: PREVIEW RESULT ==================
if "rendered_video" in st.session_state and os.path.exists(st.session_state.rendered_video):
    st.header("📱 3. Preview Video Result")
    st.video(st.session_state.rendered_video)
