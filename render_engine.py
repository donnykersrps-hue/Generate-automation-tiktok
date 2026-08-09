import os
import requests
import asyncio
import edge_tts
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, 
    CompositeAudioClip, concatenate_videoclips
)

# ================== SET FFMPEG UNTUK CLOUD ==================
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"

# ================== WRAPPER FUNCTIONS ==================

def safe_subclip(clip, start, end):
    try:
        return clip.subclipped(start, end)
    except AttributeError:
        try:
            return clip.subclip(start, end)
        except AttributeError:
            return clip.with_start(start).with_duration(end - start)

def safe_resize(clip, newsize=None, height=None, width=None):
    if newsize is None:
        if height is not None and width is None:
            aspect = clip.w / clip.h
            width = int(height * aspect)
            newsize = (width, height)
        elif width is not None and height is None:
            aspect = clip.w / clip.h
            height = int(width / aspect)
            newsize = (width, height)
        else:
            raise ValueError("Harus menentukan newsize atau height/width")
    try:
        return clip.resized(newsize)
    except AttributeError:
        return clip.resize(newsize)

def safe_crop(clip, x1=None, y1=None, x2=None, y2=None, x_center=None, y_center=None, width=None, height=None):
    try:
        if all(v is not None for v in [x1, y1, x2, y2]):
            return clip.cropped(x1, y1, x2, y2)
        elif x_center is not None and y_center is not None and width is not None and height is not None:
            return clip.cropped(x_center=x_center, y_center=y_center, width=width, height=height)
        else:
            raise ValueError("Parameter crop tidak lengkap")
    except AttributeError:
        if all(v is not None for v in [x1, y1, x2, y2]):
            return clip.crop(x1, y1, x2, y2)
        elif x_center is not None and y_center is not None and width is not None and height is not None:
            return clip.crop(x_center=x_center, y_center=y_center, width=width, height=height)
        else:
            raise ValueError("Parameter crop tidak lengkap")

def safe_set_duration(clip, duration):
    try:
        return clip.with_duration(duration)
    except AttributeError:
        return clip.set_duration(duration)

def safe_set_audio(clip, audio_clip):
    try:
        return clip.with_audio(audio_clip)
    except AttributeError:
        return clip.set_audio(audio_clip)

def safe_write_videofile(clip, *args, **kwargs):
    kwargs.pop("verbose", None)
    kwargs.pop("logger", None)
    return clip.write_videofile(*args, **kwargs)

# ================== 1. FETCH MULTI-VIDEO PEXELS ==================
def get_pexels_video(keyword, api_key, output_filename="temp_video.mp4"):
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=1&orientation=portrait"
    headers = {"Authorization": api_key}
    try:
        response = requests.get(url, headers=headers).json()
        videos = response.get("videos", [])
        if not videos:
            print(f"Video Pexels untuk '{keyword}' tidak ditemukan!")
            return None
        video_files = videos[0].get("video_files", [])
        if not video_files:
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
def create_text_image(text, size=(1080, 1920), font_size=52, color='white', stroke_color='black', stroke_width=6):
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
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()
    
    wrapped_lines = []
    for paragraph in text.split('\n'):
        if paragraph.strip():
            wrapped_lines.extend(textwrap.wrap(paragraph, width=24))
    
    line_heights = []
    for line in wrapped_lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            height = bbox[3] - bbox[1]
        except AttributeError:
            _, height = draw.textsize(line, font=font)
        line_heights.append(height)
    
    total_height = sum(line_heights) + (len(wrapped_lines) - 1) * 20
    y_start = (size[1] - total_height) // 2
    y = y_start
    
    for idx, line in enumerate(wrapped_lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
        except AttributeError:
            text_width, _ = draw.textsize(line, font=font)
        
        x = (size[0] - text_width) // 2
        
        # Outline tebal agar teks sangat jelas di atas latar video apa pun
        if stroke_width > 0:
            for dx in range(-stroke_width, stroke_width+1):
                for dy in range(-stroke_width, stroke_width+1):
                    if dx != 0 or dy != 0:
                        draw.text((x+dx, y+dy), line, font=font, fill=stroke_color)
        
        draw.text((x, y), line, font=font, fill=color)
        y += line_heights[idx] + 20
        
    return img

# ================== 4. RENDER VIDEO DINAMIS & BACKSOUND ==================
def assemble_video(video_paths, audio_path, text_segments, bgm_url=None, output_path="final_tiktok.mp4", resolution=(1080, 1920)):
    """
    video_paths: List 3 path video Pexels
    text_segments: List 3 teks overlay bergantian sesuai scene
    """
    if not audio_path or not os.path.exists(audio_path):
        print("File audio narasi tidak ditemukan!")
        return None

    try:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        num_scenes = len(video_paths)
        scene_duration = total_duration / num_scenes

        prepared_clips = []
        for idx, vpath in enumerate(video_paths):
            if vpath and os.path.exists(vpath):
                clip = VideoFileClip(vpath)
                if clip.duration < scene_duration:
                    repetitions = int(scene_duration / clip.duration) + 1
                    clip = concatenate_videoclips([clip] * repetitions)
                clip = safe_subclip(clip, 0, scene_duration)
            else:
                # Fallback jika salah satu video gagal download
                clip = VideoFileClip(video_paths[0])
                clip = safe_subclip(clip, 0, scene_duration)

            clip = safe_resize(clip, height=resolution[1])
            if clip.w > resolution[0]:
                clip = safe_crop(clip, x_center=clip.w/2, y_center=clip.h/2, width=resolution[0], height=resolution[1])

            # Buat Teks Overlay khusus untuk scene ini
            current_text = text_segments[idx] if idx < len(text_segments) else ""
            if current_text.strip():
                txt_img = create_text_image(current_text, size=resolution)
                txt_clip = ImageClip(np.array(txt_img))
                txt_clip = safe_set_duration(txt_clip, scene_duration)
                composite_scene = CompositeVideoClip([clip, txt_clip])
            else:
                composite_scene = clip

            prepared_clips.append(composite_scene)

        # Gabungkan semua scene video bergantian
        final_video = concatenate_videoclips(prepared_clips)

        # Penanganan Musik Latar (Backsound Instrument Bebas Copyright)
        try:
            # Mengunduh audio instrumen santai/syahdu
            bgm_path = "temp_bgm.mp3"
            if not os.path.exists(bgm_path):
                sample_bgm_url = "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"
                bgm_bytes = requests.get(sample_bgm_url, timeout=10).content
                with open(bgm_path, "wb") as f:
                    f.write(bgm_bytes)

            bgm_clip = AudioFileClip(bgm_path)
            if bgm_clip.duration < total_duration:
                reps = int(total_duration / bgm_clip.duration) + 1
                bgm_clip = concatenate_videoclips([bgm_clip] * reps)
            bgm_clip = safe_subclip(bgm_clip, 0, total_duration)
            
            # Turunkan volume BGM ke 15% agar narasi utama terdengar sangat jelas
            try:
                bgm_clip = bgm_clip.volumex(0.15)
            except AttributeError:
                bgm_clip = bgm_clip.multiply_volume(0.15)

            final_audio = CompositeAudioClip([audio_clip, bgm_clip])
        except Exception as e:
            print(f"BGM Warning: {e}. Menggunakan narasi audio saja.")
            final_audio = audio_clip

        final_clip = safe_set_audio(final_video, final_audio)

        safe_write_videofile(
            final_clip,
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
            ffmpeg_params=["-crf", "23"]
        )

        audio_clip.close()
        final_clip.close()
        return output_path

    except Exception as e:
        print(f"Error rendering video: {e}")
        import traceback
        traceback.print_exc()
        return None
