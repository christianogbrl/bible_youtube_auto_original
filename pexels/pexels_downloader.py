# pexels_downloader.py
import random
from pathlib import Path
import os
import json
import requests
from datetime import datetime
from mutagen.mp3 import MP3  # ✅ para ler duração de arquivos mp3

# -------------------------------
# Caminhos e carregamento da configuração
# -------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "utils" / "config.json"

if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"❌ Arquivo de configuração não encontrado em: {CONFIG_PATH}")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

PEXELS_API_KEY = config.get("pexels_api_key")
QUERIES = config.get("pexels_query", "")
if isinstance(QUERIES, str):
    QUERIES = [QUERIES]

ORIENTATION = config.get("pexels_orientation")
PEOPLE = config.get("pexels_people")
YEAR = config.get("pexels_year")
DURATION = config.get("pexels_duration", {})
FRAMERATE = config.get("pexels_framerate", {})
RESOLUTION = config.get("pexels_resolution")
DATE_FILTER = config.get("pexels_date")
ORDER_BY = config.get("pexels_order_by")
ALLOW_OVERFLOW = config.get("pexels_allow_overflow", False)
PER_PAGE = config.get("pexels_per_page", 10)
SAVE_PATH = BASE_DIR / config.get("pexels_save_path", "videos")
LOG_FILE = SAVE_PATH / "download_log.txt"

os.makedirs(SAVE_PATH, exist_ok=True)

# -------------------------------
# Limpa log e cria cabeçalho
# -------------------------------
with open(LOG_FILE, "w", encoding="utf-8") as logf:
    logf.write(f"Log de download iniciado em {datetime.now()}\n\n")
    logf.write(f"{'ID':<10} | {'Termo':<20} | {'Duração(s)':<10} | {'Acum(s)':<10} | {'Resolução':<10} | {'FPS':<5} | {'Arquivo'}\n")
    logf.write("-" * 120 + "\n")

# -------------------------------
# 🗣️ Listar MP3 e somar duração total
# -------------------------------
def listar_media_audios_narracao():
    folder = BASE_DIR / "media_audios_narracao"
    if not folder.exists():
        print(f"⚠️ Pasta não encontrada: {folder}")
        return [], 0.0

    mp3_files = list(folder.glob("*.mp3"))
    if not mp3_files:
        print("⚠️ Nenhum arquivo MP3 encontrado em media_audios_narracao.")
        return [], 0.0

    total_duration = 0.0
    print("\n🎧 Áudios encontrados:\n")
    print(f"{'Arquivo':<40} | {'Duração (s)':>12}")
    print("-" * 60)

    audio_info = []
    for mp3_path in mp3_files:
        try:
            audio = MP3(mp3_path)
            duration = audio.info.length
            total_duration += duration
            print(f"{mp3_path.name:<40} | {duration:>10.2f}")
            audio_info.append((mp3_path.name, duration))
        except Exception as e:
            print(f"❌ Erro ao ler {mp3_path.name}: {e}")

    print("-" * 60)
    print(f"🕒 Duração total dos áudios: {total_duration:.2f}s ({total_duration/60:.2f} min)\n")
    return audio_info, total_duration

# -------------------------------
# Buscar vídeos na API Pexels
# -------------------------------
def search_videos(query):
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": PER_PAGE}

    if ORIENTATION:
        params["orientation"] = ORIENTATION
    if PEOPLE:
        params["people"] = PEOPLE
    if ORDER_BY:
        params["order_by"] = ORDER_BY

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Erro ao buscar vídeos: {response.text}")
    return response.json().get("videos", [])

# -------------------------------
# Escolher o melhor arquivo disponível
# -------------------------------
def pick_best_file(video_files):
    best = None
    best_score = -1
    for f in video_files:
        width = f.get("width", 0)
        height = f.get("height", 0)
        fps = f.get("fps", 0) or 0
        score = (width * height) + fps
        if score > best_score:
            best = f
            best_score = score
    return best

# -------------------------------
# Aplicar filtros e organizar vídeos por duração
# -------------------------------
def apply_filters(videos):
    filtered = []
    for v in videos:
        duration = v.get("duration", 0)
        video_files = v.get("video_files", [])
        if not video_files:
            continue

        best_file = pick_best_file(video_files)

        # Filtro de duração por vídeo
        if DURATION:
            if duration < DURATION.get("min", 0) or duration > DURATION.get("max", 9999):
                continue

        # Filtro de resolução
        if RESOLUTION:
            w, h = best_file.get("width", 0), best_file.get("height", 0)
            if RESOLUTION == "hd" and (w < 1280 or h < 720):
                continue
            if RESOLUTION == "fullhd" and (w < 1920 or h < 1080):
                continue
            if RESOLUTION == "4k" and (w < 3840 or h < 2160):
                continue

        # Filtro de framerate
        fps = best_file.get("fps", 0) or 0
        if FRAMERATE:
            if fps < FRAMERATE.get("min", 0) or fps > FRAMERATE.get("max", 1000):
                continue

        filtered.append((v, best_file))

    # Ordenar por duração decrescente para baixar vídeos longos primeiro
    filtered.sort(key=lambda x: x[0].get("duration", 0), reverse=True)
    return filtered

# -------------------------------
# Baixar vídeos sem repetir
# -------------------------------
def download_videos_until_total(filtered_videos_per_query, total_target):
    downloaded_duration = 0
    downloaded_videos_set = set()
    videos_baixados = 0
    videos_ignorados = 0

    while downloaded_duration < total_target:
        made_progress = False

        # Calcula quanto tempo ainda falta
        remaining_time = total_target - downloaded_duration

        for i, videos in enumerate(filtered_videos_per_query):
            if not videos:
                continue

            # Filtra vídeos ainda não baixados desta query
            remaining_videos = [v for v in videos if v[0]['id'] not in downloaded_videos_set]
            if not remaining_videos:
                continue

            # Escolhe o vídeo que mais se aproxima do tempo restante
            # Prioriza vídeos que não ultrapassem remaining_time se overflow não permitido
            candidate = None
            min_diff = float('inf')
            for v, file in remaining_videos:
                dur = v.get("duration", 0)
                diff = abs(remaining_time - dur)  # diferença do tempo restante
                if not ALLOW_OVERFLOW and dur > remaining_time:
                    continue  # ignora vídeos que ultrapassam o limite
                if diff < min_diff:
                    candidate = (v, file)
                    min_diff = diff

            if not candidate:
                # Nenhum vídeo adequado nesta query
                continue

            v, file = candidate
            video_id = v.get("id")
            duration = v.get("duration", 0)
            width = file.get("width", 0)
            height = file.get("height", 0)
            fps = file.get("fps", 0) or 0

            import re
            safe_query = re.sub(r"[^a-zA-Z0-9_-]", "_", QUERIES[i])
            filename = SAVE_PATH / f"{str(videos_baixados+1).zfill(2)}_{safe_query}_pexels_{video_id}.mp4"

            # Download do vídeo
            print(f"⬇️ [{str(videos_baixados+1).zfill(2)}_] Baixando vídeo {video_id} ({duration}s) da busca '{QUERIES[i]}'...")
            with requests.get(file.get("link"), stream=True) as r:
                with open(filename, "wb") as fhandle:
                    for chunk in r.iter_content(chunk_size=8192):
                        fhandle.write(chunk)

            # Atualiza variáveis de controle
            downloaded_videos_set.add(video_id)
            downloaded_duration += duration
            videos_baixados += 1
            made_progress = True

            log_entry = f"{video_id:<10} | {QUERIES[i]:<20} | {duration:<10} | {downloaded_duration:<10} | {width}x{height:<10} | {fps:<5} | {filename}"
            print("✅", log_entry)
            with open(LOG_FILE, "a", encoding="utf-8") as logf:
                logf.write(log_entry + "\n")

            if downloaded_duration >= total_target and not ALLOW_OVERFLOW:
                break

        if not made_progress:
            print("⚠️ Todas as queries foram esgotadas antes de atingir a duração total.")
            break

    # -------------------------------
    # Resumo final
    # -------------------------------
    print("\n📊 RESUMO FINAL")
    print("-" * 60)
    print(f"🎧 Duração total dos áudios: {total_target:.2f}s ({total_target/60:.2f} min)")
    print(f"🎞️ Duração total dos vídeos baixados: {downloaded_duration:.2f}s ({downloaded_duration/60:.2f} min)")
    print(f"📹 Total de vídeos baixados: {videos_baixados}")
    print(f"🚫 Vídeos ignorados por repetição ou limite: {videos_ignorados}")
    print("-" * 60)
    if downloaded_duration >= total_target:
        print("✅ Duração total atingida (com tolerância de overflow)")
    else:
        print("⚠️ Duração total NÃO atingida")
    print("-" * 60)

# -------------------------------
# Execução principal
# -------------------------------
def main_pexels_downloader():
    # 1️⃣ Calcular total de duração dos áudios
    _, total_audio_duration = listar_media_audios_narracao()

    # 2️⃣ Buscar vídeos de todas as queries e aplicar filtros
    all_filtered_videos = []
    for query in QUERIES:
        print(f"\n🔍 Buscando vídeos para o termo: {query}")
        videos = search_videos(query)
        print(f"Encontrados {len(videos)} vídeos")
        filtered = apply_filters(videos)
        print(f"{len(filtered)} vídeos após filtros")
        all_filtered_videos.append(filtered)

    # 3️⃣ Baixar vídeos até atingir a duração total dos áudios
    download_videos_until_total(all_filtered_videos, total_audio_duration)

    print(f"\n📄 Log completo salvo em: {LOG_FILE}")
