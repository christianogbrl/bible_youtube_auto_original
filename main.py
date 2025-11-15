# main.py
# Importa o main principal dos módulos
from scraper.scraper_versiculo import main_scraper_versiculo
from gemini.gemini_narracao_prompt import main_gemini_narracao_prompt
from gemini.gemini_seo_youtube_prompt import main_gemini_seo_youtube_prompt
from elevenlabs.eleven_tts_narracao import main_eleven_tts_narracao
from utils.audio_fundo_cortar import main_audio_fundo_cortar
from pexels.pexels_downloader import main_pexels_downloader
from capcut.capcut_files_uploader import main_capcut_files_uploader
from capcut.capcut_editor import main_capcut_editor
from chromakey.chromakey_overlay_video_base import main_chromakey_overlay_video_base
from youtube.youtube_uploader import main_youtube_uploader

# ==========================================================
# 🔹 EXECUTAR DIRETAMENTE
# ==========================================================
if __name__ == "__main__":
    main_scraper_versiculo()
    main_gemini_narracao_prompt()
    main_gemini_seo_youtube_prompt()
    main_eleven_tts_narracao()
    main_audio_fundo_cortar()
    main_pexels_downloader()
    main_capcut_files_uploader()
    main_capcut_editor()
    main_chromakey_overlay_video_base()
    main_youtube_uploader()


