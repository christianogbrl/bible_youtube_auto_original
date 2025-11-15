# capcut_editor.py
from capcut_browser import launch_capcut, save_storage_state
from pathlib import Path
import datetime
import time
import re
import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# =====================================================
# ⚙️ CONFIGURAÇÕES GERAIS
# =====================================================
EDITOR_URL = (
    "https://www.capcut.com/editor?"
    "from_page=work_space&start_tab=video&enter_from=create_project"
    "&tab=all&__action_from=Christiano&workspaceId=7533642151549386813&scenario=custom"
)
BASE_DIR = Path(__file__).resolve().parent.parent
media_videos_PATH = BASE_DIR / "media_videos_downloads"
media_audios_narracao_PATH = BASE_DIR / "media_audios_narracao"
media_audios_fundo_PATH = BASE_DIR / "media_audios_fundo"

DEFAULT_TIMEOUT = 60000

DEBUG = True
CAPCUT_DIR = Path(__file__).resolve().parent 
LOG_DIR = CAPCUT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


# =====================================================
# 🪵 LOGGING CENTRALIZADO
# =====================================================
def log(msg: str, level: str = "INFO"):
    icons = {
        "INFO": "ℹ️",
        "WARN": "⚠️",
        "ERR": "❌",
        "OK": "✅",
        "DBG": "🐞"
    }
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    icon = icons.get(level, "")
    line = f"[{time_str}] {icon} {level:<5} | {msg}"

    # Log em arquivo
    log_file = LOG_DIR / f"{date_str}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    # Log no terminal
    if level != "DBG" or DEBUG:
        print(line)


# =====================================================
# ⏱️ CONVERSÃO DE TEMPO
# =====================================================
def time_str_to_seconds(time_str: str) -> float:
    parts = [p for p in time_str.split(":") if p]
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


# =====================================================
# 🚀 ABRIR EDITOR CAPCUT (mantém aberto)
# =====================================================
def open_capcut_editor(headless: bool = False, wait_time: int = 10):
    """
    Inicializa o CapCut Editor no navegador, mantendo a instância aberta.
    """
    log("Iniciando CapCut Editor...", "INFO")

    # launch_capcut já cria o Playwright internamente
    try:
        p, browser, context, page = launch_capcut(headless=headless)
    except Exception as e:
        log(f"Falha ao iniciar navegador: {e}", "ERR")
        raise

    try:
        log(f"Acessando editor: {EDITOR_URL}")
        page.goto(EDITOR_URL, timeout=120000)
        page.wait_for_load_state("networkidle", timeout=120000)
        log(f"Página carregada, aguardando {wait_time}s...")
        time.sleep(wait_time)
        save_storage_state(context)
        log("Editor pronto para uso!", "OK")
        return p, browser, context, page
    except Exception as e:
        log(f"Erro ao abrir o editor: {e}", "ERR")
        raise
    finally:
        log("Finalizando inicialização do CapCut (fase segura).", "DBG")


# =====================================================
# 🧹 FECHAR OVERLAYS E POPUPS
# =====================================================
def close_overlays(page):
    log("Verificando overlays antes de continuar...", "DBG")
    try:
        while True:
            masks = page.query_selector_all(".lv-modal-mask")
            if not masks:
                break
            for mask in masks:
                mask.evaluate("el => el.remove()")
                log("Overlay .lv-modal-mask removido.", "DBG")
            time.sleep(0.3)

        buttons = page.query_selector_all("button:has-text('OK'), button:has-text('Got it'), button:has-text('Fechar')")
        for btn in buttons:
            btn.click()
            log("Fechando popup interativo.", "DBG")
            time.sleep(0.5)

        log("✅ Overlays fechados.", "OK")
    except Exception as e:
        log(f"Erro ao fechar overlays: {e}", "ERR")


# =====================================================
# 📂 LISTAR ARQUIVOS POR EXTENSÃO (ordem decrescente robusta)
# =====================================================
def list_media_files(folder_path: Path, extension: str):
    if not extension.startswith("."):
        extension = "." + extension

    files = [f.stem for f in folder_path.glob(f"*{extension}") if f.is_file()]

    def extract_number(name: str):
        match = re.match(r"(\d+)_", name)
        if match:
            return int(match.group(1))
        return float('-inf')  # arquivos sem número ficam no final

    # Ordena pelo número inicial decrescente
    files_sorted = sorted(files, key=extract_number, reverse=True)

    log(f"{len(files_sorted)} arquivos encontrados em {folder_path} ({extension})", "INFO")
    return files_sorted

# =====================================================
# 🖱️ FUNÇÃO ROBUSTA DE EXPORTAÇÃO + DOWNLOAD
# =====================================================

# Pasta final para os vídeos
VIDEO_FINAL_PATH = Path(__file__).resolve().parent.parent / "video_final_youtube"
VIDEO_FINAL_PATH.mkdir(exist_ok=True, parents=True)

def export_video_to_final_folder(page, max_retries: int = 3):
    """
    Automatiza exportação e download do CapCut, salvando sempre com
    nome customizado: video_final_youtube_YYYYMMDD_HHMMSS.mp4
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    custom_filename = f"video_final_youtube_{timestamp}.mp4"
    file_path = VIDEO_FINAL_PATH / custom_filename

    for attempt in range(1, max_retries + 1):
        log(f"🔄 Tentativa {attempt} de exportação do vídeo", "INFO")
        try:
            # 1️⃣ Botão Export
            try:
                page.wait_for_selector("#export-video-btn", timeout=15000)
                page.query_selector("#export-video-btn").click()
                log("✅ Botão Export clicado.", "OK")
            except Exception as e:
                log(f"⚠️ Falha ao clicar no botão Export: {e}", "WARN")
                continue

            time.sleep(1)

            # 2️⃣ Botão Download do menu
            try:
                page.wait_for_selector(".button-QK_D5I", timeout=15000)
                page.query_selector(".button-QK_D5I").click()
                log("✅ Botão Download do menu clicado.", "OK")
            except Exception as e:
                log(f"⚠️ Falha ao clicar no botão Download do menu: {e}", "WARN")
                continue

            time.sleep(1)

            # 3️⃣ Botão Confirm Export
            try:
                page.wait_for_selector("#export-confirm-button", timeout=15000)
                page.query_selector("#export-confirm-button").click()
                log("✅ Botão Confirm Export clicado.", "OK")
            except Exception as e:
                log(f"⚠️ Falha ao clicar no botão Confirm Export: {e}", "WARN")
                continue

            # 4️⃣ Aguardar renderização
            try:
                log("ℹ️ Aguardando renderização do vídeo...", "INFO")
                start_time = time.time()
                timeout_render = 900  # 15 minutos
                poll_interval = 2
                while time.time() - start_time < timeout_render:
                    percent_int_el = page.query_selector(".lv-statistic-value-int")
                    percent_decimal_el = page.query_selector(".lv-statistic-value-decimal")
                    if percent_int_el and percent_decimal_el:
                        try:
                            int_part = int(percent_int_el.inner_text().strip())
                            decimal_text = percent_decimal_el.inner_text().replace("%", "").strip()
                            decimal_part = float(decimal_text) if decimal_text else 0.0
                            total_percent = int_part + decimal_part
                            log(f"Renderizando vídeo: {total_percent:.1f}%", "DBG")
                            if total_percent >= 100:
                                log("✅ Renderização concluída!", "OK")
                                break
                        except Exception:
                            pass
                    time.sleep(poll_interval)
                else:
                    log("⚠️ Timeout durante renderização do vídeo.", "WARN")
                    continue
            except Exception as e:
                log(f"❌ Erro durante a renderização: {e}", "ERR")
                continue

            # 5️⃣ Botão final de Download
            try:
                page.wait_for_selector(".downloadButton", timeout=15000)
                download_btn = page.query_selector(".downloadButton")

                try:
                    # Download automático via Playwright
                    with page.expect_download() as download_info:
                        download_btn.click()

                    download = download_info.value
                    download.save_as(str(file_path))
                    log(f"✅ Vídeo exportado e salvo em: {file_path}", "OK")
                    return str(file_path)

                except Exception as e:
                    log(f"⚠️ Falha no download automático: {e}. Tentando fallback via link direto...", "WARN")

                    # Fallback via link direto
                    link_el = download_btn.query_selector("a")
                    if link_el:
                        video_url = link_el.get_attribute("href")
                        if video_url:
                            import requests
                            r = requests.get(video_url, stream=True)
                            with open(file_path, "wb") as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            log(f"✅ Vídeo baixado via link direto em: {file_path}", "OK")
                            return str(file_path)
                        else:
                            log("⚠️ Link do vídeo não encontrado no elemento <a>.", "WARN")
                    else:
                        log("⚠️ Elemento <a> para fallback não encontrado.", "WARN")
                    continue

            except Exception as e:
                log(f"⚠️ Falha ao clicar no botão final de download: {e}", "WARN")
                continue

        except Exception as e:
            log(f"❌ Erro inesperado na tentativa {attempt}: {e}", "ERR")

        log(f"⏳ Aguardando 3s antes de nova tentativa...", "INFO")
        time.sleep(3)

    log("❌ Todas as tentativas de exportação falharam.", "ERR")
    return None


# =====================================================
# 🔍 FUNÇÃO PARA SCROLL NO VIEWPORT DO CARD
# =====================================================

CARD_SELECTOR = ".containter-gWXoeD"
DEFAULT_TIMEOUT = 30000

def scroll_card_container(card, max_attempts=10):
    """
    Rola somente o container do card para cima, baixo, esquerda e direita.
    """
    try:
        parent = card.evaluate_handle("el => el.closest('.containter-gWXoeD').parentElement")
        attempts = 0
        while attempts < max_attempts:
            box = card.bounding_box()
            if box and box["x"] >= 0 and box["y"] >= 0:
                return True
            parent.evaluate("el => el.scrollBy(0, 100)")
            parent.evaluate("el => el.scrollBy(100, 0)")
            parent.evaluate("el => el.scrollBy(-100, 0)")
            parent.evaluate("el => el.scrollBy(0, -100)")
            attempts += 1
            time.sleep(0.2)
        return False
    except Exception:
        return False


# =====================================================
# 🔍 FUNÇÃO ÚNICA PARA ACHAR CARD PELO NOME (AJUSTADA COM SCROLL)
# =====================================================
def find_card_by_name(page, file_name: str):
    try:
        page.wait_for_selector(CARD_SELECTOR, timeout=DEFAULT_TIMEOUT)
        cards = page.query_selector_all(CARD_SELECTOR)
        file_name_lower = file_name.lower().strip()

        for card in cards:
            label = card.query_selector(".card-item-label-POvntE")
            if not label:
                continue
            label_text = (label.inner_text() or "").strip().lower()
            if file_name_lower in label_text or label_text in file_name_lower:
                scroll_card_container(card)
                try:
                    card.scroll_into_view_if_needed(timeout=3000)
                    card.wait_for_element_state("visible", timeout=3000)
                    log(f"✅ Card encontrado: {label_text}", "INFO")
                    return card
                except Exception as e:
                    log(f"Erro ao preparar card '{label_text}' para interação: {e}", "WARN")
                    continue
        log(f"Card não encontrado para o nome '{file_name}'", "WARN")
    except PlaywrightTimeoutError:
        log(f"⏱ Timeout ao procurar cards na página.", "WARN")
    except Exception as e:
        log(f"❌ Erro inesperado ao procurar card '{file_name}': {e}", "ERR")
    return None


# =====================================================
# ⏱️ PEGAR DURAÇÃO DO CARD (COM SCROLL)
# =====================================================
def get_card_duration(page, file_name: str):
    card = find_card_by_name(page, file_name)
    if not card:
        return {"file": file_name, "duration_sec": 0}
    scroll_card_container(card)
    try:
        units = card.query_selector_all(".badge-duration-dYEO3g .unit-rYitVh")
        duration_str = "".join([u.inner_text().strip() for u in units])
        duration_sec = time_str_to_seconds(duration_str)
        log(f"{file_name}: duração = {duration_str} ({duration_sec}s)", "OK")
        return {"file": file_name, "duration_sec": duration_sec}
    except Exception as e:
        log(f"Erro ao obter duração de {file_name}: {e}", "WARN")
        return {"file": file_name, "duration_sec": 0}


# =====================================================
# 🖱️ CLICAR NO CARD (SE NÃO ADICIONADO) — COM SCROLL
# =====================================================
CARD_SELECTOR = ".containter-gWXoeD"
ADDED_BADGE_SELECTOR = ".badge-added-ztq24Q"
LABEL_SELECTOR = ".card-item-label-POvntE"

def click_card_if_not_added(page, file_name: str):
    try:
        page.wait_for_selector(CARD_SELECTOR, timeout=DEFAULT_TIMEOUT)
        cards = page.query_selector_all(CARD_SELECTOR)
        file_name_lower = file_name.lower().strip()

        target_card = None
        for card in cards:
            label = card.query_selector(LABEL_SELECTOR)
            if not label:
                continue
            label_text = (label.inner_text() or "").strip().lower()
            if file_name_lower in label_text or label_text in file_name_lower:
                target_card = card
                break

        if not target_card:
            log(f"⚠️ Card '{file_name}' não encontrado.", "WARN")
            return False

        if target_card.query_selector(ADDED_BADGE_SELECTOR):
            log(f"✅ Card '{file_name}' já foi adicionado.", "OK")
            return True

        scroll_card_container(target_card)
        target_card.scroll_into_view_if_needed(timeout=30000)
        target_card.wait_for_element_state("visible", timeout=30000)

        log(f"ℹ️ Clicando em '{file_name}'...", "INFO")
        target_card.click()

        try:
            page.wait_for_selector(f".containter-gWXoeD:has(.badge-added-ztq24Q) >> text={file_name}", timeout=15000)
            log(f"✅ '{file_name}' adicionado com sucesso!", "OK")
            return True
        except PlaywrightTimeoutError:
            log(f"⚠️ Badge 'Added' não apareceu para '{file_name}'.", "WARN")
            return False

    except PlaywrightTimeoutError:
        log(f"⏱ Timeout ao procurar cards para '{file_name}'.", "WARN")
        return False
    except Exception as e:
        log(f"❌ Erro ao clicar no card '{file_name}': {e}", "ERR")
        return False


# =====================================================
# 🖱️ ARRASTAR CARD PARA COORDENADAS (COM SCROLL)
# =====================================================
CARD_SELECTOR = ".containter-gWXoeD"
LABEL_SELECTOR = ".card-item-label-POvntE"
ADDED_BADGE_SELECTOR = ".badge-added-ztq24Q"
DEFAULT_TIMEOUT = 30000

def drag_card_to_coordinates(page, file_name: str, x: float, y: float, first_in_loop: bool = False):
    try:
        page.wait_for_selector(LABEL_SELECTOR, timeout=DEFAULT_TIMEOUT)
        labels = page.query_selector_all(LABEL_SELECTOR)
        file_name_lower = file_name.lower().strip()

        target_idx = None
        for i, label in enumerate(labels):
            label_text = (label.inner_text() or "").strip().lower()
            if file_name_lower in label_text or label_text in file_name_lower:
                target_idx = i
                break

        if target_idx is None:
            log(f"⚠️ Card '{file_name}' não encontrado.", "WARN")
            return False

        if not first_in_loop and target_idx < len(labels) - 1:
            prev_label = labels[target_idx + 1]  # invertido: ordem decrescente
            prev_name = (prev_label.inner_text() or "").strip()
            log(f"⏳ Aguardando badge 'Added' no card anterior ('{prev_name}')...", "DBG")

            badge_ok = False
            start_time = time.time()
            while time.time() - start_time < 30:
                prev_card = prev_label.evaluate_handle("el => el.closest('.containter-gWXoeD')")
                if prev_card.query_selector(ADDED_BADGE_SELECTOR):
                    badge_ok = True
                    break
                time.sleep(0.5)

            if not badge_ok:
                log(f"⚠️ Card anterior ('{prev_name}') ainda sem badge — prosseguindo mesmo assim.", "WARN")
            else:
                log(f"✅ Card anterior ('{prev_name}') confirmado com badge 'Added'.", "DBG")
        else:
            log(f"🐞 Primeiro card '{file_name}', arrastando direto.", "DBG")

        label = labels[target_idx]
        card = label.evaluate_handle("el => el.closest('.containter-gWXoeD')")

        scroll_card_container(card)
        card.scroll_into_view_if_needed(timeout=30000)
        card.wait_for_element_state("visible", timeout=30000)

        box = card.bounding_box()
        if not box:
            log(f"⚠️ Sem coordenadas do card '{file_name}'", "WARN")
            return False

        start_x = box["x"] + box["width"] / 2
        start_y = box["y"] + box["height"] / 2

        page.mouse.move(start_x, start_y)
        page.mouse.down()
        page.mouse.move(x, y, steps=15)
        page.mouse.up()

        log(f"✅ Card '{file_name}' arrastado para ({x:.0f},{y:.0f})", "OK")
        return True

    except PlaywrightTimeoutError:
        log(f"⚠️ Timeout ao tentar arrastar o card '{file_name}'", "WARN")
        return False
    except Exception as e:
        log(f"❌ Erro ao arrastar '{file_name}': {e}", "ERR")
        return False

# =====================================================
# 🖱️ MOVER PAINEL TIMELINE POR COORDENADAS
# =====================================================
def drag_panel_timeline(page, start_x: float, start_y: float, end_x: float, end_y: float, steps: int = 15):
    try:
        page.mouse.move(start_x, start_y)
        page.mouse.down()
        page.mouse.move(end_x, end_y, steps=steps)
        page.mouse.up()
        log(f"Painel da timeline arrastado: ({start_x},{start_y}) -> ({end_x},{end_y})", "OK")
        return True
    except Exception as e:
        log(f"Erro ao arrastar painel da timeline: {e}", "ERR")
        return False


# =====================================================
# 🔇 BOTÃO DE MUTE (CLICA EM TODOS)
# =====================================================
def click_mute_button(page):
    try:
        buttons = page.query_selector_all("button.lv-btn.lv-btn-text.lv-btn-size-mini.lv-btn-shape-square")
        if not buttons:
            log("Botão de mute não encontrado.", "WARN")
            return False
        for btn in buttons:
            try:
                btn.click()
                log("Botão de mute clicado.", "OK")
            except Exception:
                pass
        return True
    except Exception as e:
        log(f"Erro ao clicar no botão de mute: {e}", "ERR")
        return False


# =====================================================
# ▶️ EXECUÇÃO PRINCIPAL
# =====================================================
def main_capcut_editor():
    p, browser, context, page = open_capcut_editor(headless=False)
    try:
        close_overlays(page)
        drag_panel_timeline(page, start_x=843, start_y=492, end_x=804, end_y=247)

        for name in list_media_files(media_audios_fundo_PATH, ".mp3"):
            close_overlays(page)
            click_card_if_not_added(page, name)

        files_narration = list_media_files(media_audios_narracao_PATH, ".mp3")
        for idx, name in enumerate(files_narration):
            close_overlays(page)
            drag_card_to_coordinates(page, name, x=466, y=587, first_in_loop=(idx==0))

        files_videos = list_media_files(media_videos_PATH, ".mp4")
        for idx, name in enumerate(files_videos):
            close_overlays(page)
            drag_card_to_coordinates(page, name, x=468, y=539, first_in_loop=(idx==0))

        # Clicar no botão de mute
        click_mute_button(page)

        # Exporta e salva o video final
        close_overlays(page)
        final_video_path = export_video_to_final_folder(page)
        if final_video_path:
            log(f"Vídeo final salvo em: {final_video_path}", "OK")
        else:
            log("Falha ao exportar o vídeo após várias tentativas.", "ERR")

        log("✅ Script finalizado. O navegador permanece aberto para inspeção manual.", "OK")
        input("Pressione Enter para encerrar manualmente o navegador...")

    finally:
        log("Encerrando contexto (final).", "DBG")
