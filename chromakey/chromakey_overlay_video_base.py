# chromakey_overlay_video_base.py
import subprocess
from pathlib import Path
import json
import cv2
import numpy as np
from tqdm import tqdm


# ======================================================
# ⚙️ CONFIGURAÇÕES PADRÃO
# ======================================================
FPS = 30
CHROMAKEY_SIMILARITY = 0.3
CHROMAKEY_BLEND = 0.1
OUTPUT_CODEC = "libx264"
CRF = 23
PRESET = "medium"
PIX_FMT = "yuv420p"


# ======================================================
# 🎞️ FUNÇÕES AUXILIARES
# ======================================================
def get_video_info(video_path, ffprobe_path):
    """Retorna duração, largura e altura do vídeo."""
    cmd = [
        str(ffprobe_path),
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "format=duration",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    duration = float(data["format"]["duration"])
    width = int(data["streams"][0]["width"])
    height = int(data["streams"][0]["height"])
    return duration, width, height


def detect_dominant_color(video_path, sample_frames=5):
    """Detecta cor dominante do fundo do overlay."""
    cap = cv2.VideoCapture(str(video_path))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = np.linspace(0, frame_count - 1, min(sample_frames, frame_count), dtype=int)

    colors = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        small = cv2.resize(frame, (100, 100))
        rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        mean_color = np.mean(rgb.reshape(-1, 3), axis=0)
        colors.append(mean_color)
    cap.release()

    if not colors:
        raise RuntimeError("Não foi possível detectar cor dominante.")

    avg_color = np.mean(colors, axis=0)
    return tuple(int(c) for c in avg_color)


def rgb_to_hex(rgb):
    r, g, b = rgb
    return f"0x{r:02X}{g:02X}{b:02X}"


def position_to_xy(pos, base_w, base_h, overlay_w, overlay_h):
    """Converte posição textual para coordenadas do overlay."""
    pos = pos.lower()
    if pos == "center":
        return f"(main_w-overlay_w)/2:(main_h-overlay_h)/2"
    elif pos == "top-left":
        return "0:0"
    elif pos == "top-right":
        return f"(main_w-overlay_w):0"
    elif pos == "bottom-left":
        return f"0:(main_h-overlay_h)"
    elif pos == "bottom-right":
        return f"(main_w-overlay_w):(main_h-overlay_h)"
    return f"(main_w-overlay_w)/2:(main_h-overlay_h)/2"


# ======================================================
# 🎬 FUNÇÃO PRINCIPAL
# ======================================================
def processar_videos(
    video_base,
    overlays,
    output_video,
    ffmpeg_path,
    ffprobe_path
):
    print("🎞️ Obtendo informações do vídeo base...")
    duration_base, base_w, base_h = get_video_info(video_base, ffprobe_path)

    print("🎞️ Construindo filtros para sobreposição (overlay + chromakey)...")
    filter_cmds = []

    for i, overlay in enumerate(overlays, start=1):
        overlay_path = overlay["path"].resolve()
        duration_overlay, overlay_w, overlay_h = get_video_info(overlay_path, ffprobe_path)
        dominant_color = detect_dominant_color(overlay_path)
        hex_color = rgb_to_hex(dominant_color)

        start = overlay.get("start_sec")
        end = overlay.get("end_sec")

        # Percentuais relativos à duração do vídeo base
        if overlay.get("start_pct") is not None:
            start = overlay["start_pct"] * duration_base
        if overlay.get("end_pct") is not None:
            end = overlay["end_pct"] * duration_base
        if end is None:
            end = start + duration_overlay

        # Redimensionamento proporcional
        if overlay.get("scale", True):
            scale_factor = min(base_w / overlay_w, base_h / overlay_h, 1)
            new_w = int(overlay_w * scale_factor)
            new_h = int(overlay_h * scale_factor)
        else:
            new_w, new_h = overlay_w, overlay_h

        xy = position_to_xy(overlay["position"], base_w, base_h, new_w, new_h)

        filter_cmds.append(
            f"[{i}:v]scale={new_w}:{new_h},chromakey={hex_color}:{CHROMAKEY_SIMILARITY}:{CHROMAKEY_BLEND}[ovr{i}];"
            f"[{0 if i == 1 else 'tmp'}][ovr{i}]overlay={xy}:enable='between(t,{start},{end})'[tmp]"
        )

    filter_complex = "".join(filter_cmds)
    if filter_complex.endswith("[tmp]"):
        filter_complex = filter_complex.replace("[tmp]", "")

    # Monta comando final do ffmpeg
    ffmpeg_cmd = [str(ffmpeg_path)]
    for inp in [video_base] + [o["path"].resolve() for o in overlays]:
        ffmpeg_cmd.extend(["-i", str(inp)])
    ffmpeg_cmd.extend([
        "-filter_complex", filter_complex,
        "-c:v", OUTPUT_CODEC,
        "-crf", str(CRF),
        "-preset", PRESET,
        "-pix_fmt", PIX_FMT,
        str(output_video)
    ])

    print("🎬 Executando renderização com ffmpeg...")
    total_frames = int(duration_base * FPS)
    pbar = tqdm(total=total_frames, desc="Processando", ncols=80)

    with subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as proc:
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("frame="):
                try:
                    current_frame = int(line.split("=")[1].split()[0])
                    pbar.n = current_frame
                    pbar.refresh()
                except Exception:
                    pass

    pbar.close()
    print(f"\n✅ Vídeo final salvo: {output_video}")


# ======================================================
# 🧩 MAIN EXECUTION WRAPPER
# ======================================================
def main_chromakey_overlay_video_base():
    print("🔹 Iniciando composição de vídeo com chroma key...")

    base_dir = Path(__file__).resolve().parent.parent
    video_dir = base_dir / "media_video_inscrevase"

    video_base = (video_dir / "meu_video.mp4")
    output_video = (video_dir / "video_final_precomposed.mp4")

    ffmpeg_path = Path("C:/ffmpeg/bin/ffmpeg.exe")
    ffprobe_path = ffmpeg_path.parent / "ffprobe.exe"

    overlays = [
        {
            "path": video_dir / "inscreva_se_chroma.mp4",
            "start_pct": 0.5,
            "end_pct": None,
            "position": "center",
            "scale": True
        },
        {
            "path": video_dir / "banner_cta.mp4",
            "start_sec": 2.0,
            "end_sec": None,
            "position": "top-right",
            "scale": True
        }
    ]

    processar_videos(video_base, overlays, output_video, ffmpeg_path, ffprobe_path)
