import os
import requests
import asyncio
import edge_tts
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ================== 1. PEXELS API ENGINE ==================
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
        logging.error(f"Error Pexels for keyword '{keyword}': {e}")
        return None

# ================== 2. EDGE TTS PER SLIDE ==================
async def generate_tts(text, output_filename="temp_audio.mp3", rate="-5%"):
    voice = "id-ID-ArdiNeural"
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_filename)

def create_voiceover(text, output_filename="temp_audio.mp3", rate="-5%"):
    asyncio.run(generate_tts(text, output_filename, rate))
    return output_filename

# ================== 3. HELPER DURASI MEDIA & WRAP TEKS ==================
def get_media_duration(media_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        media_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except Exception:
        return 5.0

def wrap_text(text, max_chars=28):
    """Mencegah teks terpotong di samping layar HP 1080px"""
    if not text:
        return ""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        if len(' '.join(current_line)) > max_chars:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(' '.join(current_line))
                current_line = []
    if current_line:
        lines.append(' '.join(current_line))
        
    return r"\N".join(lines)

# ================== 4. GENERATOR SUBTITLE ASS PER SLIDE ==================
def create_ass_for_slide(slide_data, duration, output_ass="slide_sub.ass"):
    title = wrap_text(slide_data.get("title", "").upper(), max_chars=25)
    main_text = wrap_text(slide_data.get("main_text", ""), max_chars=32)
    highlight = wrap_text(slide_data.get("highlight", ""), max_chars=28)
    source = slide_data.get("source", "")
    text_color_hex = slide_data.get("text_color", "#FFFF00").replace("#", "")

    # Convert Hex (#RRGGBB) -> ASS Format (&H00BBGGRR&)
    if len(text_color_hex) == 6:
        r, g, b = text_color_hex[0:2], text_color_hex[2:4], text_color_hex[4:6]
        ass_color = f"&H00{b}{g}{r}&"
    else:
        ass_color = "&H0000FFFF&"  # Fallback Cyan

    # Format Waktu ASS Presisi (H:MM:SS.cs)
    hrs = int(duration // 3600)
    mins = int((duration % 3600) // 60)
    secs = int(duration % 60)
    cs = int((duration - int(duration)) * 100)
    time_end = f"{hrs}:{mins:02d}:{secs:02d}.{cs:02d}"

    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HeaderTitle,DejaVu Sans,52,&H0000D7FF&,&H00000000,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,0,5,50,50,1400,1
Style: MainHighlight,DejaVu Sans,48,{ass_color},&H00000000,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,0,5,60,60,1050,1
Style: SubBody,DejaVu Sans,40,&H00FFFFFF&,&H00000000,&H00000000,&H60000000,0,0,0,0,100,100,0,0,1,3,0,5,80,80,720,1
Style: SourceFooter,DejaVu Sans,34,&H0000FFFF&,&H00000000,&H00000000,&H60000000,0,1,0,0,100,100,0,0,1,2,0,5,50,50,450,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 2,0:00:00.00,{time_end},HeaderTitle,,0,0,0,,{title}
Dialogue: 2,0:00:00.00,{time_end},MainHighlight,,0,0,0,,{highlight}
Dialogue: 1,0:00:00.00,{time_end},SubBody,,0,0,0,,{main_text}
"""
    if source:
        ass_content += f"Dialogue: 1,0:00:00.00,{time_end},SourceFooter,,0,0,0,,{source}\n"

    with open(output_ass, "w", encoding="utf-8") as f:
        f.write(ass_content)
    return output_ass

# ================== 5. ASSEMBLE MULTI-SLIDE VIDEO ==================
def assemble_video(slides_data, pexels_key, bgm_description="", output_path="final_tiktok.mp4"):
    if not slides_data:
        logging.error("Tidak ada data slide untuk dirender.")
        return None

    rendered_slide_clips = []
    
    try:
        # Loop Render Per Slide (Frame-Accurate Sync)
        for idx, slide in enumerate(slides_data):
            slide_id = slide.get("slide_id", idx + 1)
            vo_script = slide.get("vo_script", "")
            bg_kw = slide.get("bg_keyword", "cinematic nature")
            
            # A. Generate Voiceover Slide
            slide_audio_path = f"temp_vo_{slide_id}.mp3"
            create_voiceover(vo_script, slide_audio_path)
            slide_duration = get_media_duration(slide_audio_path)
            
            # B. Download Background Video
            slide_raw_video = f"temp_bg_{slide_id}.mp4"
            v_path = get_pexels_video(bg_kw, pexels_key, output_filename=slide_raw_video)
            
            # C. Create Subtitle ASS Slide
            slide_ass_path = f"temp_sub_{slide_id}.ass"
            create_ass_for_slide(slide, slide_duration, slide_ass_path)
            safe_ass = os.path.abspath(slide_ass_path).replace(":", "\\:").replace("'", "'\\''")
            
            # D. Render Single Slide MP4
            slide_out_path = f"slide_rendered_{slide_id}.mp4"
            
            if v_path and os.path.exists(v_path):
                input_bg = ["-stream_loop", "-1", "-i", v_path]
                vf_filter = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles='{safe_ass}'"
            else:
                input_bg = ["-f", "lavfi", "-i", "color=c=black:s=1080x1920"]
                vf_filter = f"subtitles='{safe_ass}'"

            cmd_slide = ["ffmpeg", "-y"] + input_bg + [
                "-i", slide_audio_path,
                "-vf", vf_filter,
                "-map", "0:v", "-map", "1:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-t", str(slide_duration),
                slide_out_path
            ]
            
            subprocess.run(cmd_slide, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if os.path.exists(slide_out_path):
                rendered_slide_clips.append(slide_out_path)

        # E. Concatenate All Rendered Slides
        concat_list_path = "concat_list.txt"
        with open(concat_list_path, "w") as f:
            for clip in rendered_slide_clips:
                f.write(f"file '{os.path.abspath(clip)}'\n")

        temp_concat_video = "temp_concat_no_bgm.mp4"
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            temp_concat_video
        ]
        subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # F. Inject Audio BGM (Volume 25%)
        bgm_path = os.path.abspath("temp_bgm.mp3")
        bgm_url = "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        if not os.path.exists(bgm_path) or os.path.getsize(bgm_path) < 1000:
            try:
                resp = requests.get(bgm_url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    with open(bgm_path, "wb") as f:
                        f.write(resp.content)
            except Exception as e:
                logging.warning(f"BGM download warning: {e}")

        has_bgm = os.path.exists(bgm_path) and os.path.getsize(bgm_path) > 1000

        if has_bgm:
            cmd_final = [
                "ffmpeg", "-y",
                "-i", temp_concat_video,
                "-i", bgm_path,
                "-filter_complex", "[1:a]volume=0.25[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                output_path
            ]
        else:
            cmd_final = [
                "ffmpeg", "-y",
                "-i", temp_concat_video,
                "-c", "copy",
                output_path
            ]

        subprocess.run(cmd_final, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if os.path.exists(output_path):
            logging.info(f"✅ Video Multi-Slide Berhasil Dibuat: {output_path}")
            return output_path
        return None

    except Exception as e:
        logging.error(f"Error pada assemble_video: {e}")
        return None
