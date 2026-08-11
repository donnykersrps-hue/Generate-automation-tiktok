import os
import requests
import asyncio
import edge_tts
import textwrap
import logging
import subprocess
import json
import time

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

# ================== 3. GENERATOR SUBTITLE ASS (DINAMIS & ESTETIK) ==================
def create_ass_subtitle_file(text, total_duration, output_ass="subtitles.ass"):
    """
    Membuat file subtitle ASS otomatis dengan styling khusus TikTok:
    - Font Bold Putih + Stroke/Outline Hitam
    - Posisi di area bawah layar (Alignment 2, MarginV 120)
    - Bergantian per frasa (3-4 kata) mengikuti total durasi audio
    """
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

    # Header ASS Style
    ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokSub,DejaVu Sans,54,&H00FFFFFF,&H00000000,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,2,50,50,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def format_time(seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        msecs = int((seconds - int(seconds)) * 100)
        return f"{hrs}:{mins:02d}:{secs:02d}.{msecs:02d}"

    for idx, f_text in enumerate(frasa):
        t_start = format_time(idx * durasi_per_frasa)
        t_end = format_time((idx + 1) * durasi_per_frasa)
        # Escape karakter khusus ASS
        clean_f_text = f_text.replace("{", "").replace("}", "")
        ass_content += f"Dialogue: 0,{t_start},{t_end},TikTokSub,,0,0,0,,{clean_f_text}\n"

    with open(output_ass, "w", encoding="utf-8") as f:
        f.write(ass_content)

    return output_ass

# ================== 4. HELPER DURASI AUDIO (VIA FFPROBE) ==================
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
    except Exception as e:
        logging.error(f"Error get duration: {e}")
        return 60.0

# ================== 5. ASSEMBLE VIDEO (DIRECT FFMPEG SUBPROCESS) ==================
def assemble_video(video_paths, audio_path, text_segments, bgm_description=None,
                   full_narration="", output_path="final_tiktok.mp4", resolution=(1080, 1920)):
    if not audio_path or not os.path.exists(audio_path):
        logging.error("Audio narasi tidak ditemukan!")
        return None

    try:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        total_duration = get_audio_duration(audio_path)
        logging.info(f"Durasi audio narasi: {total_duration:.2f} detik")

        # 1. Siapkan Subtitle ASS
        ass_file = "subtitles.ass"
        if full_narration and full_narration.strip():
            create_ass_subtitle_file(full_narration, total_duration, ass_file)

        # 2. Siapkan BGM
        bgm_path = "temp_bgm.mp3"
        bgm_url = "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        if not os.path.exists(bgm_path) or os.path.getsize(bgm_path) < 1000:
            try:
                resp = requests.get(bgm_url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    with open(bgm_path, "wb") as f:
                        f.write(resp.content)
            except Exception as e:
                logging.warning(f"BGM Download error: {e}")

        has_bgm = os.path.exists(bgm_path) and os.path.getsize(bgm_path) > 1000

        # 3. Ambil Video Pertama yang Valid
        valid_vpath = next((p for p in video_paths if p and os.path.exists(p)), None)

        # 4. RACIK PERINTAH FFMPEG DIRECT
        # Jika video valid ada, gunakan loop video; jika tidak, buat background warna hitam murni
        if valid_vpath:
            input_args = ["-stream_loop", "-1", "-i", valid_vpath]
            video_filter = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles={ass_file}"
        else:
            input_args = ["-f", "lavfi", "-i", "color=c=black:s=1080x1920"]
            video_filter = f"subtitles={ass_file}"

        cmd = ["ffmpeg", "-y"] + input_args + ["-i", audio_path]

        if has_bgm:
            cmd += ["-i", bgm_path]
            # Filter Complex: Gabungkan audio Narasi + BGM (Volume BGM 15%)
            filter_complex = f"[0:v]{video_filter}[vout];[2:a]volume=0.15[bgm];[1:a][bgm]amix=inputs=2:duration=first[aout]"
            cmd += [
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-map", "[aout]"
            ]
        else:
            cmd += [
                "-vf", video_filter,
                "-map", "0:v",
                "-map", "1:a"
            ]

        # Konfigurasi Output FFmpeg
        cmd += [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-t", str(total_duration),
            output_path
        ]

        logging.info("Menjalankan perakitan video via Direct FFmpeg...")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0 and os.path.exists(output_path):
            logging.info("Render video berhasil dengan Direct FFmpeg!")
            return output_path
        else:
            logging.error(f"FFmpeg Error Log: {result.stderr}")
            return None

    except Exception as e:
        logging.error(f"Error rendering: {str(e)}")
        return None
