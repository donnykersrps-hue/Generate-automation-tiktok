import os
import requests
import asyncio
import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips

# ================== SET ENVIRONMENT UNTUK FFMPEG (Cloud) ==================
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"

# ================== FUNGSI LOOP MANUAL (TANPA IMPORT) ==================
def loop_video(clip, duration):
    """Mengulang clip hingga mencapai durasi tertentu."""
    if clip.duration >= duration:
        return clip.subclip(0, duration)
    # Hitung berapa kali pengulangan
    n = int(duration / clip.duration) + 1
    clips = [clip] * n
    return concatenate_videoclips(clips).subclip(0, duration)

# ================== 1. FETCH VIDEO DARI PEXELS ==================
def get_pexels_video(keyword, api_key, output_filename="temp_video.mp4"):
    """
    Mencari dan mengunduh video vertikal (portrait) dari Pexels.
    Mengembalikan path file video atau None jika gagal.
    """
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=1&orientation=portrait"
    headers = {"Authorization": api_key}
    
    try:
        response = requests.get(url, headers=headers).json()
        
        videos = response.get("videos", [])
        if not videos:
            print("Video Pexels tidak ditemukan!")
            return None
        
        video_files = videos[0].get("video_files", [])
        if not video_files:
            print("Tidak ada file video dalam respons Pexels!")
            return None
        
        # Pilih video dengan lebar >= 720, jika ada; jika tidak, ambil yang pertama
        video_url = next(
            (v["link"] for v in video_files if v.get("width", 0) >= 720),
            video_files[0]["link"]
        )
        
        video_data = requests.get(video_url).content
        with open(output_filename, "wb") as f:
            f.write(video_data)
        
        return output_filename
    
    except Exception as e:
        print(f"Error Pexels: {e}")
        return None

# ================== 2. TEXT-TO-SPEECH (Edge-TTS) ==================
async def generate_tts(text, output_filename="temp_audio.mp3"):
    voice = "id-ID-ArdiNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_filename)

def create_voiceover(text, output_filename="temp_audio.mp3"):
    asyncio.run(generate_tts(text, output_filename))
    return output_filename

# ================== 3. RENDER TEKS KE GAMBAR (PIL) ==================
def create_text_image(text, size=(1080, 1920), font_size=65, color='white', stroke_color='black', stroke_width=4):
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Coba muat font, fallback ke default
    try:
        font = ImageFont.truetype("Arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    lines = text.split('\n')
    line_heights = []
    max_width = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        max_width = max(max_width, width)
        line_heights.append(height)
    
    total_height = sum(line_heights) + (len(lines) - 1) * 5
    y_start = (size[1] - total_height) // 2
    
    y = y_start
    for idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (size[0] - text_width) // 2
        
        # Outline (stroke)
        if stroke_width > 0:
            for dx in range(-stroke_width, stroke_width+1):
                for dy in range(-stroke_width, stroke_width+1):
                    if dx != 0 or dy != 0:
                        draw.text((x+dx, y+dy), line, font=font, fill=stroke_color)
        # Teks utama
        draw.text((x, y), line, font=font, fill=color)
        y += line_heights[idx] + 5
    
    return img

# ================== 4. RENDER VIDEO UTAMA ==================
def assemble_video(video_path, audio_path, text_overlay, output_path="final_tiktok.mp4", resolution=(1080, 1920)):
    try:
        video_clip = VideoFileClip(video_path)
        audio_clip = AudioFileClip(audio_path)
        
        # Sesuaikan durasi video dengan audio menggunakan fungsi loop manual
        if video_clip.duration < audio_clip.duration:
            video_clip = loop_video(video_clip, audio_clip.duration)
        else:
            video_clip = video_clip.subclip(0, audio_clip.duration)
        
        # Resize dan crop ke resolusi yang diinginkan
        video_clip = video_clip.resize(height=resolution[1])
        if video_clip.w > resolution[0]:
            x_center = video_clip.w // 2
            video_clip = video_clip.crop(x_center - resolution[0]//2, 0, x_center + resolution[0]//2, resolution[1])
        
        # Buat teks overlay
        text_img = create_text_image(text_overlay, size=resolution, font_size=65, color='white', stroke_color='black', stroke_width=4)
        text_clip = ImageClip(np.array(text_img), transparent=True, ismask=False)
        text_clip = text_clip.set_duration(video_clip.duration)
        
        # Gabungkan video dan teks
        final_clip = CompositeVideoClip([video_clip, text_clip]).set_audio(audio_clip)
        final_clip.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=4,
            ffmpeg_params=["-crf", "23"]
        )
        
        # Tutup clip untuk membebaskan memory
        video_clip.close()
        audio_clip.close()
        final_clip.close()
        return output_path
    except Exception as e:
        print(f"Error rendering video: {e}")
        return None
