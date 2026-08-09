import os
import requests
import asyncio
import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips

# ================== SET FFMPEG UNTUK CLOUD ==================
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"

# ================== FUNGSI SUBKLIP AMAN (UNTUK VERSI MOVIEPY) ==================
def safe_subclip(clip, start, end):
    """Memotong clip dengan aman, mendukung moviepy 1.x dan 2.x."""
    try:
        return clip.subclip(start, end)
    except AttributeError:
        if hasattr(clip, 'subclipped'):
            return clip.subclipped(start, end)
        else:
            # Fallback manual: buat clip baru dengan durasi
            return clip.with_start(start).with_duration(end - start)

# ================== FUNGSI LOOP MANUAL ==================
def repeat_clip(clip, target_duration):
    if clip.duration >= target_duration:
        return safe_subclip(clip, 0, target_duration)
    repetitions = int(target_duration / clip.duration) + 1
    clips = [clip] * repetitions
    return safe_subclip(concatenate_videoclips(clips), 0, target_duration)

# ================== 1. FETCH VIDEO PEXELS ==================
def get_pexels_video(keyword, api_key, output_filename="temp_video.mp4"):
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
    
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
    ]
    font = None
    for path in font_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, font_size)
                break
            except:
                continue
    if font is None:
        font = ImageFont.load_default()
    
    lines = text.split('\n')
    line_heights = []
    max_width = 0
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
        except AttributeError:
            width, height = draw.textsize(line, font=font)
        max_width = max(max_width, width)
        line_heights.append(height)
    
    total_height = sum(line_heights) + (len(lines) - 1) * 5
    y_start = (size[1] - total_height) // 2
    y = y_start
    for idx, line in enumerate(lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
        except AttributeError:
            text_width, _ = draw.textsize(line, font=font)
        x = (size[0] - text_width) // 2
        if stroke_width > 0:
            for dx in range(-stroke_width, stroke_width+1):
                for dy in range(-stroke_width, stroke_width+1):
                    if dx != 0 or dy != 0:
                        draw.text((x+dx, y+dy), line, font=font, fill=stroke_color)
        draw.text((x, y), line, font=font, fill=color)
        y += line_heights[idx] + 5
    return img

# ================== 4. RENDER VIDEO UTAMA (DENGAN VALIDASI FILE) ==================
def assemble_video(video_path, audio_path, text_overlay, output_path="final_tiktok.mp4", resolution=(1080, 1920)):
    # ===== VALIDASI AWAL: PASTIKAN FILE VIDEO & AUDIO ADA =====
    if not os.path.exists(video_path):
        print(f"File video tidak ditemukan: {video_path}")
        return None
    if not os.path.exists(audio_path):
        print(f"File audio tidak ditemukan: {audio_path}")
        return None
    
    # Cek ukuran file (minimal 1 KB) agar tidak kosong
    if os.path.getsize(video_path) < 1024:
        print(f"File video terlalu kecil (mungkin corrupt): {video_path}")
        return None
    if os.path.getsize(audio_path) < 1024:
        print(f"File audio terlalu kecil (mungkin corrupt): {audio_path}")
        return None

    try:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        video_clip = VideoFileClip(video_path)
        audio_clip = AudioFileClip(audio_path)

        # Sesuaikan durasi video dengan audio
        if video_clip.duration < audio_clip.duration:
            video_clip = repeat_clip(video_clip, audio_clip.duration)
        else:
            video_clip = safe_subclip(video_clip, 0, audio_clip.duration)

        # Resize dan crop
        video_clip = video_clip.resize(height=resolution[1])
        if video_clip.w > resolution[0]:
            x_center = video_clip.w // 2
            video_clip = video_clip.crop(x_center - resolution[0]//2, 0, x_center + resolution[0]//2, resolution[1])

        # Buat teks overlay
        text_img = create_text_image(text_overlay, size=resolution)
        text_clip = ImageClip(np.array(text_img), transparent=True, ismask=False)
        text_clip = text_clip.set_duration(video_clip.duration)

        # Gabungkan
        final_clip = CompositeVideoClip([video_clip, text_clip]).set_audio(audio_clip)
        final_clip.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
            ffmpeg_params=["-crf", "23"],
            verbose=False,
            logger=None
        )

        video_clip.close()
        audio_clip.close()
        final_clip.close()
        return output_path

    except Exception as e:
        print(f"Error rendering video: {e}")
        import traceback
        traceback.print_exc()
        return None
