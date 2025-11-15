# audio_fundo_cortar.py
from pydub import AudioSegment
from mutagen.mp3 import MP3
from pathlib import Path
from datetime import datetime
import random
import json
import subprocess

# ==============================
# CONFIGURAÇÕES DE PASTAS
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_NARRATION = BASE_DIR / "media_audios_narracao"
PASTA_BACKGROUND = BASE_DIR / "media_audios_fundo_cortar"
PASTA_SAIDA = BASE_DIR / "media_audios_fundo"

BASE_DIR_LINKS = Path(__file__).resolve().parent
JSON_VIDEOS = BASE_DIR_LINKS / "videos_links.json"  # arquivo com links

# Porcentagem de margem para evitar corte muito próximo do final
MARGEM_FINAL = 0.05  # 5%

# ==============================
# FUNÇÃO: SOMAR DURAÇÃO DAS NARRAÇÕES
# ==============================
def somar_duracao_audios(pasta: Path) -> float:
    total_segundos = 0
    for arquivo in pasta.glob("*.mp3"):
        audio = MP3(arquivo)
        duracao = audio.info.length
        total_segundos += duracao
    return total_segundos

# ==============================
# FUNÇÃO: OBTER PREFIXO INCREMENTAL
# ==============================
def proximo_prefixo(pasta: Path) -> str:
    pasta.mkdir(exist_ok=True)
    existentes = [f.stem for f in pasta.glob("*.mp3")]
    numeros = [int(nome[:2]) for nome in existentes if nome[:2].isdigit()]
    proximo = max(numeros, default=0) + 1
    return f"{proximo:02d}_"

# ==============================
# FUNÇÃO: REGISTRAR LOG
# ==============================
def registrar_log(pasta_saida: Path, nome_arquivo: str, arquivo_bg: Path, duracao_total: float, duracao_bg: float, inicio: float, fim: float):
    log_path = pasta_saida / "log_cortes.txt"
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tempo_restante = duracao_bg - fim
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(
            f"[{agora}] Arquivo: {nome_arquivo}\n"
            f"  • Background: {arquivo_bg.name}\n"
            f"  • Duração total original do background: {duracao_bg:.2f}s\n"
            f"  • Duração usada: {duracao_total:.2f}s\n"
            f"  • Corte: início {inicio:.2f}s → fim {fim:.2f}s\n"
            f"  • Tempo restante do background: {tempo_restante:.2f}s\n"
            f"{'-'*60}\n"
        )
    print(f"📝 Log registrado em: {log_path}")

# ==============================
# FUNÇÃO: BAIXAR MP3 ALEATÓRIO DO YOUTUBE
# ==============================
def baixar_mp3_aleatorio(pasta: Path, json_file: Path) -> Path:
    if not json_file.exists():
        raise FileNotFoundError(f"{json_file} não encontrado.")
    
    with open(json_file, "r", encoding="utf-8") as f:
        videos = json.load(f)
    
    if not videos:
        raise ValueError("Arquivo JSON está vazio.")
    
    video_url = random.choice(videos)
    pasta.mkdir(exist_ok=True)
    
    print(f"🎬 Baixando vídeo aleatório: {video_url}")

    # Define nome temporário para download
    nome_temporario = pasta / "bg_temp.mp3"

    # Comando yt-dlp para baixar apenas áudio em mp3
    comando = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "-o", str(nome_temporario),
        video_url
    ]
    
    subprocess.run(comando, check=True)
    print(f"✅ Download concluído: {nome_temporario}")
    return nome_temporario

# ==============================
# FUNÇÃO: CORTAR ÁUDIO DE BACKGROUND
# ==============================
def cortar_audio_background(pasta_background: Path, duracao_total: float):
    arquivos_bg = list(pasta_background.glob("*.mp3"))
    if not arquivos_bg:
        # Se não houver arquivo local, baixar do YouTube
        arquivo_bg = baixar_mp3_aleatorio(pasta_background, JSON_VIDEOS)
    else:
        # Escolher aleatoriamente um arquivo local
        arquivo_bg = random.choice(arquivos_bg)
    
    print(f"🎧 Arquivo background selecionado: {arquivo_bg.name}")
    print(f"⏱️ Duração desejada: {duracao_total:.2f} segundos")

    # Carrega o áudio
    audio_bg = AudioSegment.from_mp3(arquivo_bg)
    duracao_bg = len(audio_bg) / 1000  # segundos

    if duracao_bg < duracao_total:
        raise ValueError("O áudio de background é menor que a soma das narrações!")

    # Define ponto inicial aleatório seguro
    max_inicio = duracao_bg - duracao_total - (duracao_bg * MARGEM_FINAL)
    if max_inicio < 0:
        max_inicio = 0

    inicio_aleatorio = random.uniform(0, max_inicio)
    fim = inicio_aleatorio + duracao_total

    print(f"🎲 Início aleatório: {inicio_aleatorio:.2f}s / Fim: {fim:.2f}s")

    # Corta o trecho
    audio_cortado = audio_bg[int(inicio_aleatorio * 1000):int(fim * 1000)]

    # Gera nome de arquivo com prefixo incremental
    prefixo = proximo_prefixo(PASTA_SAIDA)
    nome_saida = f"{prefixo}audio_fundo_cortado.mp3"
    caminho_saida = PASTA_SAIDA / nome_saida

    # Exporta o arquivo cortado
    audio_cortado.export(caminho_saida, format="mp3")
    print(f"✅ Áudio cortado salvo em: {caminho_saida}")

    # Registra log detalhado
    registrar_log(PASTA_SAIDA, nome_saida, arquivo_bg, duracao_total, duracao_bg, inicio_aleatorio, fim)

# ==============================
# EXECUÇÃO PRINCIPAL
# ==============================
def main_audio_fundo_cortar():
    print("🎙️ Somando duração dos áudios da pasta 'media_audios_narracao'...")
    duracao_total = somar_duracao_audios(PASTA_NARRATION)

    minutos = int(duracao_total // 60)
    segundos = int(duracao_total % 60)
    print(f"📏 Duração total das narrações: {minutos}min {segundos}s")

    cortar_audio_background(PASTA_BACKGROUND, duracao_total)

if __name__ == "__main__":
    main_audio_fundo_cortar()
