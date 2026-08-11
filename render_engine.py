import os
import requests
import asyncio
import edge_tts
import textwrap
import numpy as np
import logging
import re
import traceback
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip,
    CompositeAudioClip, concatenate_videoclips
)

# ================== KONFIGURASI ==================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"

# ================== WRAPPER FUNGSI MOVIEPY ==================
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
        if height and not width:
            aspect = clip.w / clip.h
            width = int(height * aspect)
            newsize = (width, height)
        elif width and not height:
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

# ================== 1. PEXELS ==================
def get_pexels_video(keyword, api_key, output_filename="temp_video.mp4"):
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=1&orientation=portrait"
    headers = {"Authorization": api_key}
    try:
        logging.info(f"Mengunduh Pexels: {keyword}")
        response = requests.get(url, headers=headers, timeout=15).json()
        videos = response.get("videos", [])
        if not videos:
            logging.warning(f"Keyword '{keyword}' tidak ditemukan")
            return None
        video_files = videos[0].get("video_files", [])
        if not video_files:
            return None
        video_url = next((v["link"] for v in video_files if v.get("width", 0) >= 720), video_files[0]["link"])
        video_data = requests.get(video_url, timeout=20).content
        with open(output_filename, "wb") as f:
            f.write(video_data)
        logging.info(f"Berhasil unduh {output_filename} ({len(video_data)//1024} KB)")
        return output_filename
    except Exception as e:
        logging.error(f"Error Pexels: {e}")
        return None

# ================== 2. TTS ==================
async def generate_tts(text, output_filename="temp_audio.mp3", rate="-5%"):
    voice = "id-ID-ArdiNeural"
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_filename)

def create_voiceover(text, output_filename="temp_audio.mp3", rate="-5%"):
    logging.info(f"Generate TTS dengan rate {rate}...")
    asyncio.run(generate_tts(text, output_filename, rate))
    logging.info(f"TTS selesai: {output_filename}")
    return output_filename

# ================== 3. HIGHLIGHT + OVERLAY (Per Kata) ==================
def create_highlighted_text_image(text, size=(1080, 1920), font_size=52,
                                  base_color='white', highlight_color='#FFD700',
                                  stroke_color='black', stroke_width=6):
    """
    Membuat gambar teks dengan highlight pada kata yang diapit *...*
    Contoh: "Dapatkan *10 Limpahan Rahmat* / HR. An-Nasa'i"
    -> "10 Limpahan Rahmat" berwarna emas, sisanya putih.
    """
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Load font
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

    # Parsing segmen: split berdasarkan *...*
    segments = []
    pattern = r'\*(.*?)\*'
    last_end = 0
    for match in re.finditer(pattern, text):
        if match.start() > last_end:
            segments.append((text[last_end:match.start()], base_color))
        segments.append((match.group(1), highlight_color))
        last_end = match.end()
    if last_end < len(text):
        segments.append((text[last_end:], base_color))
    if not segments:
        segments = [(text, base_color)]

    # Pecah menjadi kata-kata dengan warna
    words_with_colors = []
    for seg_text, seg_color in segments:
        for word in seg_text.split():
            words_with_colors.append((word, seg_color))

    # Bentuk baris (max 24 karakter)
    lines = []
    current_line = []
    current_chars = 0
    for word, color in words_with_colors:
        word_len = len(word)
        if current_chars + word_len + (1 if current_line else 0) <= 24:
            current_line.append((word, color))
            current_chars += word_len + (1 if current_line else 0)
        else:
            lines.append(current_line)
            current_line = [(word, color)]
            current_chars = word_len
    if current_line:
        lines.append(current_line)

    # Ukur teks
    def get_text_size(word, font):
        try:
            bbox = draw.textbbox((0, 0), word, font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            return draw.textsize(word, font=font)

    line_height = font_size + 10
    total_height = len(lines) * line_height
    y_start = (size[1] - total_height) // 2

    y = y_start
    for line in lines:
        total_width = 0
        for word, _ in line:
            w, _ = get_text_size(word, font)
            total_width += w
        total_width += (len(line) - 1) * (font_size // 3)
        x = (size[0] - total_width) // 2

        for word, color in line:
            w, h = get_text_size(word, font)
            # Stroke
            if stroke_width > 0:
                for dx in range(-stroke_width, stroke_width+1):
                    for dy in range(-stroke_width, stroke_width+1):
                        if dx != 0 or dy != 0:
                            draw.text((x+dx, y+dy), word, font=font, fill=stroke_color)
            draw.text((x, y), word, font=font, fill=color)
            x += w + font_size // 3
        y += line_height

    return img

# Fungsi kompatibilitas jika ada yang memanggil create_text_image
def create_text_image(text, size=(1080, 1920)):
    return create_highlighted_text_image(text, size=size)

# ================== 4. SUBTITLE PER FRASA ==================
def generate_subtitle_clips(text, total_duration, resolution=(1080, 1920),
                            font_size=36, color='white', stroke_color='black', stroke_width=3):
    words = text.split()
    if not words:
        return []
    frasa = []
    i = 0
    while i < len(words):
        num = min(5, len(words) - i)
        if num > 3 and len(words) - i > 5:
            num = 4 if i % 2 == 0 else 5
        frasa.append(' '.join(words[i:i+num]))
        i += num

    durasi_per_frasa = total_duration / max(len(frasa), 1)
    clips = []

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

    for idx, frasa_text in enumerate(frasa):
        try:
            img = Image.new('RGBA', resolution, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            try:
                bbox = draw.textbbox((0, 0), frasa_text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            except AttributeError:
                tw, th = draw.textsize(frasa_text, font=font)

            x = (resolution[0] - tw) // 2
            y = resolution[1] - int(resolution[1] * 0.15) - th

            if stroke_width > 0:
                for dx in range(-stroke_width, stroke_width+1):
                    for dy in range(-stroke_width, stroke_width+1):
                        if dx != 0 or dy != 0:
                            draw.text((x+dx, y+dy), frasa_text, font=font, fill=stroke_color)
            draw.text((x, y), frasa_text, font=font, fill=color)

            txt_clip = ImageClip(np.array(img))
            txt_clip = safe_set_duration(txt_clip, durasi_per_frasa)
            txt_clip = txt_clip.set_start(idx * durasi_per_frasa)
            clips.append(txt_clip)
        except Exception as e:
            logging.error(f"Gagal buat subtitle clip ke-{idx}: {e}")

    return clips

# ================== 5. ASSEMBLE VIDEO UTAMA ==================
def assemble_video(video_paths, audio_path, text_segments, bgm_description=None,
                   full_narration="", output_path="final_tiktok.mp4", resolution=(1080, 1920)):
    """
    video_paths: list path video dari Pexels (boleh berisi None)
    audio_path: path file audio narasi
    text_segments: list teks overlay (dengan *...* untuk highlight)
    full_narration: teks narasi lengkap untuk subtitle (opsional)
    """
    if not audio_path or not os.path.exists(audio_path):
        logging.error("Audio narasi tidak ditemukan!")
        return None

    try:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        # Audio narasi
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        logging.info(f"Durasi audio: {total_duration:.2f} detik")

        # ===== PROTEKSI FALLBACK VIDEO =====
        valid_vpaths = [p for p in video_paths if p and os.path.exists(p)]
        num_scenes = len(text_segments) if len(text_segments) > 0 else 3
        scene_duration = total_duration / max(num_scenes, 1)

        prepared_clips = []
        for idx in range(num_scenes):
            vpath = video_paths[idx] if idx < len(video_paths) else None

            # Ambil video yang valid
            if vpath and os.path.exists(vpath):
                clip = VideoFileClip(vpath)
            elif len(valid_vpaths) > 0:
                clip = VideoFileClip(valid_vpaths[0])
            else:
                # Jika semua video gagal, buat background gelap
                from moviepy.video.VideoClip import ColorClip
                clip = ColorClip(size=resolution, color=(20, 20, 30), duration=scene_duration)
                logging.warning(f"Scene {idx+1} menggunakan ColorClip karena tidak ada video valid")

            # Sesuaikan durasi
            if clip.duration < scene_duration:
                reps = int(scene_duration / clip.duration) + 1
                clip = concatenate_videoclips([clip] * reps)
            clip = safe_subclip(clip, 0, scene_duration)

            # Resize & crop ke portrait
            clip = safe_resize(clip, height=resolution[1])
            if clip.w > resolution[0]:
                clip = safe_crop(clip, x_center=clip.w/2, y_center=clip.h/2,
                                 width=resolution[0], height=resolution[1])

            # Overlay dengan highlight
            current_text = text_segments[idx] if idx < len(text_segments) else ""
            if current_text.strip():
                txt_img = create_highlighted_text_image(current_text, size=resolution)
                txt_clip = ImageClip(np.array(txt_img))
                txt_clip = safe_set_duration(txt_clip, scene_duration)
                composite_scene = CompositeVideoClip([clip, txt_clip])
            else:
                composite_scene = clip

            prepared_clips.append(composite_scene)

        # Gabungkan semua scene
        logging.info("Menggabungkan scene video...")
        final_video = concatenate_videoclips(prepared_clips)

        # ===== SUBTITLE (jika ada narasi) =====
        if full_narration and full_narration.strip():
            try:
                logging.info("Membuat subtitle per frasa...")
                subtitle_clips = generate_subtitle_clips(full_narration, total_duration, resolution)
                if subtitle_clips:
                    final_video = CompositeVideoClip([final_video] + subtitle_clips)
                    logging.info(f"{len(subtitle_clips)} subtitle berhasil ditambahkan")
            except Exception as sub_err:
                logging.warning(f"Subtitle gagal: {sub_err}, lanjut tanpa subtitle")

        # ===== BGM =====
        try:
            bgm_path = "temp_bgm.mp3"
            bgm_url = "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"

            if not os.path.exists(bgm_path):
                logging.info("Mengunduh BGM dari Pixabay...")
                bgm_bytes = requests.get(bgm_url, timeout=10).content
                with open(bgm_path, "wb") as f:
                    f.write(bgm_bytes)
                logging.info("BGM berhasil diunduh")

            bgm_clip = AudioFileClip(bgm_path)
            if bgm_clip.duration < total_duration:
                reps = int(total_duration / bgm_clip.duration) + 1
                bgm_clip = concatenate_videoclips([bgm_clip] * reps)
            bgm_clip = safe_subclip(bgm_clip, 0, total_duration)

            try:
                bgm_clip = bgm_clip.volumex(0.15)
            except AttributeError:
                bgm_clip = bgm_clip.multiply_volume(0.15)

            final_audio = CompositeAudioClip([audio_clip, bgm_clip])
            logging.info("BGM berhasil digabung")
        except Exception as e:
            logging.warning(f"BGM warning: {e}, hanya menggunakan narasi")
            final_audio = audio_clip

        final_clip = safe_set_audio(final_video, final_audio)

        # ===== RENDER VIDEO =====
        logging.info("Menyimpan video final...")
        safe_write_videofile(
            final_clip, output_path,
            fps=24, codec="libx264", audio_codec="aac",
            preset="ultrafast", threads=2, ffmpeg_params=["-crf", "23"]
        )

        logging.info(f"Video selesai: {output_path}")

        # Cleanup file sementara
        for f in ["temp_video_0.mp4", "temp_video_1.mp4", "temp_video_2.mp4",
                  "temp_audio.mp3", "temp_bgm.mp3"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

        audio_clip.close()
        final_clip.close()
        return output_path

    except Exception as e:
        logging.error(f"Error rendering: {str(e)}")
        traceback.print_exc()
        return None
