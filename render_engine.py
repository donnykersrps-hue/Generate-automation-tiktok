import os
import requests
import asyncio
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# 1. Fungsi Fetch Video dari Pexels
def get_pexels_video(keyword, api_key, output_filename="temp_video.mp4"):
    """Mencari dan mengunduh video vertikal (portrait) dari Pexels."""
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=1&orientation=portrait"
    headers = {"Authorization": api_key}
    
    try:
        response = requests.get(url, headers=headers).json()
        if response.get("videos"):
            # Ambil resolusi yang paling cocok untuk TikTok (HD/SD portrait)
            video_files = response["videos"][0]["video_files"]
            video_url = next((v["link"] for v in video_files if v["width"] >= 720), video_files[0]["link"])
            
            # Proses unduh
            video_data = requests.get(video_url).content
            with open(output_filename, "wb") as f:
                f.write(video_data)
            return output_filename
        else:
            return None
    except Exception as e:
        print(f"Error fetching Pexels: {e}")
        return None

# 2. Fungsi Text-to-Speech (Edge-TTS)
async def generate_tts(text, output_filename="temp_audio.mp3"):
    """Mengubah naskah menjadi suara menggunakan AI Voice Edge-TTS."""
    # id-ID-ArdiNeural (Pria) atau id-ID-GadisNeural (Wanita)
    voice = "id-ID-ArdiNeural" 
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_filename)
    return output_filename

def create_voiceover(text, output_filename="temp_audio.mp3"):
    """Fungsi pembungkus agar asyncio bisa jalan mulus di Streamlit."""
    asyncio.run(generate_tts(text, output_filename))
    return output_filename

# 3. Fungsi Perakitan (Rendering) Video Utama
def assemble_video(video_path, audio_path, text_overlay, output_path="final_tiktok.mp4"):
    """Menggabungkan Video Pexels, Suara TTS, dan Teks Subtitle ke dalam format TikTok."""
    try:
        # Load Video dan Audio
        video_clip = VideoFileClip(video_path)
        audio_clip = AudioFileClip(audio_path)
        
        # Potong video agar durasinya sama persis dengan panjang suara narasi
        video_clip = video_clip.subclip(0, audio_clip.duration)
        
        # Pasang audio ke dalam video
        video_clip = video_clip.set_audio(audio_clip)
        
        # Buat Teks Overlay (Subtitle Sederhana di tengah layar)
        # Catatan: Font bisa disesuaikan, kita pakai default standar dulu
        txt_clip = TextClip(text_overlay, fontsize=60, color='white', bg_color='black', 
                            font='Arial-Bold', method='caption', size=(video_clip.w * 0.8, None))
        
        # Posisikan teks di agak bawah (margin bawah) dan durasinya sepanjang video
        txt_clip = txt_clip.set_position(('center', 0.75), relative=True).set_duration(video_clip.duration)
        
        # Gabungkan Video dengan Teks
        final_clip = CompositeVideoClip([video_clip, txt_clip])
        
        # Proses RenderAkhir
        # Preset 'ultrafast' dan threads=4 agar proses render di Streamlit Cloud lebih kencang
        final_clip.write_videofile(
            output_path, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            preset="ultrafast",
            threads=4
        )
        
        # Tutup file untuk membebaskan memory (Penting untuk cloud server)
        video_clip.close()
        audio_clip.close()
        final_clip.close()
        
        return output_path
        
    except Exception as e:
        print(f"Error rendering video: {e}")
        return Nonetre