import cv2
import numpy as np
import subprocess
from pathlib import Path
from tqdm import tqdm
import shutil

# ======================================================
# ⚙️ CONFIGURAÇÃO DE CAMINHOS
# ======================================================
BASE_DIR = Path(__file__).resolve().parent.parent
VIDEO_DIR = BASE_DIR / "media_video_inscrevase"

INPUT_VIDEO = (VIDEO_DIR / "INSCREVASE.mp4")
TEMP_FRAMES = (VIDEO_DIR / "frames_alpha")
OUTPUT_VIDEO_WEBM = (VIDEO_DIR / "INSCREVASE_sem_fundo.webm")
OUTPUT_VIDEO_MOV = (VIDEO_DIR / "INSCREVASE_sem_fundo.mov")

TEMP_FRAMES.mkdir(exist_ok=True, parents=True)

print(f"🎬 Entrada: {INPUT_VIDEO}")
print(f"📁 Frames temporários: {TEMP_FRAMES}")

# ======================================================
# ⚙️ PATHS DO FFMPEG E FFPROBE
# ======================================================
FFMPEG_PATH = Path("C:/ffmpeg/bin/ffmpeg.exe").resolve()
FFPROBE_PATH = Path("C:/ffmpeg/bin/ffprobe.exe").resolve()

# ======================================================
# 🎨 CONFIGURAÇÃO DO CHROMA KEY (#00B140)
# ======================================================
# RGB(0, 177, 64) → HSV aproximado (H≈72, S≈255, V≈177)
LOWER_GREEN = np.array([60, 100, 50])
UPPER_GREEN = np.array([85, 255, 255])

# ======================================================
# 🧠 ETAPA 1: REMOVER FUNDO VERDE E SALVAR FRAMES RGBA
# ======================================================
cap = cv2.VideoCapture(str(INPUT_VIDEO))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
frame_count = 0

with tqdm(total=total_frames, desc="🧩 Processando frames", ncols=80) as pbar:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(hsv, LOWER_GREEN, UPPER_GREEN)
        mask_inv = cv2.bitwise_not(mask)
        alpha = mask_inv
        rgba = cv2.merge((frame_rgb[:, :, 0], frame_rgb[:, :, 1], frame_rgb[:, :, 2], alpha))

        frame_path = TEMP_FRAMES / f"frame_{frame_count:04d}.png"
        cv2.imwrite(str(frame_path.resolve()), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
        frame_count += 1
        pbar.update(1)

cap.release()
print(f"🖼️ {frame_count} frames processados com transparência.")

# ======================================================
# 🎞️ ETAPA 2: EXPORTAR VÍDEO
# ======================================================

# --- VP9 WebM (CapCut Web) ---
print(f"\n💾 Exportando WebM VP9 (lossless) para CapCut Web...")
ffmpeg_cmd_webm = [
    str(FFMPEG_PATH), "-y",
    "-framerate", "30",
    "-i", str((TEMP_FRAMES / "frame_%04d.png").resolve()),
    "-c:v", "libvpx-vp9",
    "-pix_fmt", "yuva420p",
    "-lossless", "1",
    "-auto-alt-ref", "0",
    str(OUTPUT_VIDEO_WEBM)
]
subprocess.run(ffmpeg_cmd_webm, check=True)

# --- MOV ProRes 4444 (CapCut Desktop) ---
print(f"\n💾 Exportando MOV ProRes 4444 para CapCut Desktop...")
ffmpeg_cmd_mov = [
    str(FFMPEG_PATH), "-y",
    "-framerate", "30",
    "-i", str((TEMP_FRAMES / "frame_%04d.png").resolve()),
    "-c:v", "prores_ks",
    "-profile:v", "4444",
    "-pix_fmt", "yuva444p10le",
    str(OUTPUT_VIDEO_MOV)
]
subprocess.run(ffmpeg_cmd_mov, check=True)

# ======================================================
# 🔍 ETAPA 3: VERIFICAR CANAL ALFA
# ======================================================
def check_alpha(video_path):
    verify_cmd = [
        str(FFPROBE_PATH),
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=pix_fmt",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    result = subprocess.run(verify_cmd, capture_output=True, text=True)
    pix_fmt = result.stdout.strip()
    if "yuva" in pix_fmt:
        print(f"✅ Transparência confirmada em {video_path.name} ({pix_fmt})")
    else:
        print(f"⚠️ Atenção: canal alfa não detectado em {video_path.name} ({pix_fmt})")

check_alpha(OUTPUT_VIDEO_WEBM)
check_alpha(OUTPUT_VIDEO_MOV)

# ======================================================
# 🧹 ETAPA 4: LIMPEZA DE FRAMES TEMPORÁRIOS
# ======================================================
try:
    shutil.rmtree(TEMP_FRAMES)
    print(f"🧹 Frames temporários removidos: {TEMP_FRAMES}")
except Exception as e:
    print(f"⚠️ Não foi possível remover frames temporários: {e}")
