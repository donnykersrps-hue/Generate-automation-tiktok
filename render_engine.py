import os
import requests
import asyncio
import edge_tts
import logging
import subprocess
import re
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
)
from moviepy.video.VideoClip import ColorClip

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ================== 1. PEXELS API ==================
def get_pexels_video(keyword, api_key, output_filename="temp_video.mp4"):
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page=1&orientation=portrait"
    headers = {
        "Authorization": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15).json()
        videos = response.get("videos", [])
        if not videos:
            return None
        video_files = videos[0].get("video_files", [])
        if not video_files:
            return None
        video_url = next((v["link"] for v in video_files if v.get("width", 0) >= 720), video_files[0]["link"])
        video_data = requests.get(video_url, headers=headers, timeout=20).content
        with open(output_filename, "wb") as f:
            f.write(video_data)
        return output_filename
    except Exception as e:
        logging.error(f"Error Pexels: {e}")
        return None

# ================== 2. EDGE TTS ==================
async def generate_tts(text, output_filename="temp_audio.mp3", rate="-5%"):
    voice = "id-ID-ArdiNeural"
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_filename)

def create_voiceover(text, output_filename="temp_audio.mp3", rate="-5%"):
    asyncio.run(generate_tts(text, output_filename, rate))
    return output_filename

# ================== 3. HIGHLIGHT TEXT (untuk overlay) ==================
def create_highlighted_text_image(text, size=(1080, 1920), font_size=52,
                                  base_color='white', highlight_color='#FFD700',
                                  stroke_color='black', stroke_width=6):
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

    # Parsing highlight *...*
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
            if stroke_width > 0:
                for dx in range(-stroke_width, stroke_width+1):
                    for dy in range(-stroke_width, stroke_width+1):
                        if dx != 0 or dy != 0:
                            draw.text((x+dx, y+dy), word, font=font, fill=stroke_color)
            draw.text((x, y), word, font=font, fill=color)
            x += w + font_size // 3
        y += line_height

    return img

# ================== 4. BUAT VIDEO OVERLAY (tanpa audio) ==================
def create_overlay_video(video_paths, text_segments, total_duration, resolution=(1080, 1920)):
    valid_vpath = next((p for p in video_paths if p and os.path.exists(p)), None)
    num_scenes = len(text_segments) if text_segments else 3
    scene_duration = total_duration / max(num_scenes, 1)

    prepared_clips = []
    for idx in range(num_scenes):
        if valid_vpath:
            clip = VideoFileClip(valid_vpath)
            if clip.duration < scene_duration:
                reps = int(scene_duration / clip.duration) + 1
                clip = concatenate_videoclips([clip] * reps)
            clip = clip.subclipped(0, scene_duration)
        else:
            clip = ColorClip(size=resolution, color=(20, 20, 30), duration=scene_duration)

        # Resize & crop ke portrait
        clip = clip.resized(height=resolution[1])
        if clip.w > resolution[0]:
            clip = clip.cropped(x_center=clip.w/2, y_center=clip.h/2,
                                width=resolution[0], height=resolution[1])

        # Overlay highlight
        text = text_segments[idx] if idx < len(text_segments) else ""
        if text.strip():
            img = create_highlighted_text_image(text, size=resolution)
            txt_clip = ImageClip(np.array(img)).with_duration(scene_duration)
            composite = CompositeVideoClip([clip, txt_clip])
        else:
            composite = clip

        prepared_clips.append(composite)

    final_video = concatenate_videoclips(prepared_clips)
    return final_video

# ================== 5. SUBTITLE ASS ==================
def create_ass_subtitle_file(text, total_duration, output_ass="subtitles.ass"):
    words = text.split()
    if not words:
        return None

    frasa = []
    i = 0
    while i < len(words):
        num = min(4, len(words) - i)
        frasa.append(' '.join(words[i:i+num]))
        i += num

    durasi_per_frasa = total_duration / max(len(frasa), 1)

    ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokSub,DejaVu Sans,52,&H00FFFFFF,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,2,50,50,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def format_ass_time(seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"

    for idx, f_text in enumerate(frasa):
        t_start = format_ass_time(idx * durasi_per_frasa)
        t_end = format_ass_time((idx + 1) * durasi_per_frasa)
        clean_text = f_text.replace("{", "").replace("}", "")
        ass_content += f"Dialogue: 0,{t_start},{t_end},TikTokSub,,0,0,0,,{clean_text}\n"

    with open(output_ass, "w", encoding="utf-8") as f:
        f.write(ass_content)

    return output_ass

# ================== 6. DURASI AUDIO (FFPROBE) ==================
def get_audio_duration(audio_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except:
        return 60.0

# ================== 7. ASSEMBLE VIDEO UTAMA ==================
def assemble_video(video_paths, audio_path, text_segments, bgm_description=None,
                   full_narration="", output_path="final_tiktok.mp4", resolution=(1080, 1920)):
    if not audio_path or not os.path.exists(audio_path):
        logging.error("Audio narasi tidak ditemukan")
        return None

    try:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        total_duration = get_audio_duration(audio_path)
        logging.info(f"Durasi audio: {total_duration:.2f} detik")

        # --- Buat video overlay highlight (MoviePy) ---
        logging.info("Membuat video overlay highlight...")
        temp_overlay = "temp_video_overlay.mp4"
        overlay_clip = create_overlay_video(video_paths, text_segments, total_duration, resolution)
        overlay_clip.write_videofile(temp_overlay, fps=24, codec="libx264", preset="ultrafast",
                                     verbose=False, logger=None)
        overlay_clip.close()

        # --- Buat subtitle ASS ---
        ass_file = os.path.abspath("subtitles.ass")
        if full_narration and full_narration.strip():
            create_ass_subtitle_file(full_narration, total_duration, ass_file)

        # --- Download BGM ---
        bgm_path = os.path.abspath("temp_bgm.mp3")
        bgm_url = "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        if not os.path.exists(bgm_path) or os.path.getsize(bgm_path) < 1000:
            try:
                resp = requests.get(bgm_url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    with open(bgm_path, "wb") as f:
                        f.write(resp.content)
                logging.info("BGM berhasil diunduh")
            except Exception as e:
                logging.warning(f"BGM download gagal: {e}")

        has_bgm = os.path.exists(bgm_path) and os.path.getsize(bgm_path) > 1000

        # --- Jalankan FFmpeg untuk subtitle + audio ---
        safe_ass = ass_file.replace(":", "\\:").replace("'", "'\\''")
        cmd = ["ffmpeg", "-y", "-i", temp_overlay, "-i", audio_path]

        if has_bgm:
            cmd += ["-i", bgm_path]
            filter_complex = (
                f"[0:v]subtitles='{safe_ass}':force_style='Fontsize=52,Outline=4'[vout];"
                f"[2:a]volume=0.15[bgm];[1:a][bgm]amix=inputs=2:duration=first[aout]"
            )
            cmd += ["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]"]
        else:
            cmd += [
                "-vf", f"subtitles='{safe_ass}':force_style='Fontsize=52,Outline=4'",
                "-map", "0:v", "-map", "1:a"
            ]

        cmd += [
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-t", str(total_duration),
            output_path
        ]

        logging.info("Menjalankan FFmpeg untuk subtitle dan BGM...")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0 and os.path.exists(output_path):
            # Bersihkan file sementara
            for f in [temp_overlay, ass_file, bgm_path]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass
            logging.info(f"Video berhasil: {output_path}")
            return output_path
        else:
            logging.error(f"FFmpeg error: {result.stderr}")
            return None

    except Exception as e:
        logging.error(f"Render exception: {e}")
        return None
