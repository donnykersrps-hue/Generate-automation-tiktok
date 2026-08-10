import requests

def get_bgm_from_tunetank(description, output_filename="temp_bgm.mp3"):
    """
    Mencari dan mendownload BGM dari Tunetank berdasarkan deskripsi.
    """
    try:
        # Gunakan endpoint pencarian Tunetank (contoh, bisa disesuaikan)
        # Kita akan menggunakan query dari description
        url = "https://api.tunetank.com/api/v1/tracks"
        params = {
            "query": description,
            "limit": 1,
            "type": "music"
        }
        # Karena Tunetank tidak butuh API key, kita bisa langsung GET
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            tracks = data.get("data", [])
            if tracks and len(tracks) > 0:
                preview_url = tracks[0].get("preview_url")
                if preview_url:
                    audio_data = requests.get(preview_url).content
                    with open(output_filename, "wb") as f:
                        f.write(audio_data)
                    print(f"BGM berhasil diunduh dari Tunetank: {output_filename}")
                    return output_filename
        # Jika gagal, fallback ke default
        print("Gagal mendapatkan BGM dari Tunetank, menggunakan default.")
        return download_default_bgm(output_filename)
    except Exception as e:
        print(f"Error get BGM: {e}")
        return download_default_bgm(output_filename)

def download_default_bgm(output_filename="temp_bgm.mp3"):
    """
    Fallback: download BGM default dari Pixabay.
    """
    try:
        sample_bgm_url = "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3"
        bgm_bytes = requests.get(sample_bgm_url, timeout=10).content
        with open(output_filename, "wb") as f:
            f.write(bgm_bytes)
        print("BGM default diunduh dari Pixabay.")
        return output_filename
    except Exception as e:
        print(f"Gagal download default BGM: {e}")
        return None
