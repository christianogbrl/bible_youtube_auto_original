# capcut_files_uploader.py
from pathlib import Path
from datetime import datetime
from capcut_browser import launch_capcut, save_storage_state
import time

UPLOAD_URL = "https://www.capcut.com/my-cloud/7533642151549386813?enter_from=page_header&tab=all"
BASE_DIR = Path(__file__).resolve().parent.parent
media_videos_PATH = BASE_DIR / "media_videos_downloads"
media_audios_fundo_PATH = BASE_DIR / "media_audios_fundo"
media_audios_narracao_PATH = BASE_DIR / "media_audios_narracao"

DEBUG = True
CAPCUT_DIR = Path(__file__).resolve().parent 
LOG_DIR = CAPCUT_DIR / "logs"
log_file = LOG_DIR / "capcut_upload_log.txt"
LOG_DIR.mkdir(exist_ok=True)

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def close_overlays(page):
    """Fecha modais, pop-ups e overlays que possam bloquear cliques."""
    closed_any = False
    try:
        modals = page.query_selector_all("div.lv-modal-wrapper, div[role='dialog'], div[aria-modal='true']")
        if modals:
            log(f"⚠️ Detectado(s) {len(modals)} modal(is) na tela. Tentando fechar...")
            for modal in modals:
                try:
                    close_btns = modal.query_selector_all("button, .lv-btn, svg")
                    for btn in close_btns:
                        text = (btn.inner_text() or "").lower()
                        if any(k in text for k in ["close", "ok", "got it", "entendi", "fechar"]):
                            btn.click(force=True)
                            closed_any = True
                            log(f"✅ Modal fechado com botão '{text}'.")
                            time.sleep(0.5)
                            break
                    # Se não achou botão, tenta forçar fechamento via JS
                    page.evaluate("el => el.remove()", modal)
                except Exception:
                    pass

        # Detecta e remove banners/tutoriais/flutuantes
        banners = page.query_selector_all("div[class*='banner'], div[class*='toast'], div[class*='tutorial']")
        for banner in banners:
            try:
                page.evaluate("el => el.remove()", banner)
                closed_any = True
                log("✅ Banner/tutorial removido da página.")
            except Exception:
                pass

    except Exception as e:
        log(f"⚠️ Erro ao tentar fechar overlays: {e}")

    if closed_any:
        time.sleep(1)
    return closed_any


def open_capcut_page(page, url=UPLOAD_URL, timeout=60000):
    log(f"🌐 Abrindo página CapCut: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except:
        log("⚠️ Timeout em networkidle, seguindo mesmo assim...")

    close_overlays(page)
    log("📄 Página carregada com sucesso.")


def wait_for_file_in_grid(page, filename, timeout=60):
    close_overlays(page)
    end_time = time.time() + timeout
    while time.time() < end_time:
        items = page.query_selector_all("div.Description_content_title-VvEBZJ")
        if any(filename in i.inner_text() for i in items):
            log(f"✅ '{filename}' detectado na grid.")
            return True
        close_overlays(page)
        time.sleep(1)
    log(f"⚠️ '{filename}' não apareceu na grid dentro do timeout.")
    return False


def upload_files_via_input(page, files):
    close_overlays(page)
    try:
        page.once("filechooser", lambda fc: fc.set_files(files))
        upload_media_btn = page.wait_for_selector("button:has-text('Upload media')", timeout=10000)
        close_overlays(page)
        upload_media_btn.click()
        log("✅ Botão 'Upload media' clicado, dropdown aberto.")

        upload_file_item = page.wait_for_selector("div[role='menuitem']:has-text('Upload file')", timeout=10000)
        close_overlays(page)
        upload_file_item.click()
        log("✅ Menu 'Upload file' clicado, filechooser interceptado.")

        return True
    except Exception as e:
        log(f"❌ Erro ao tentar enviar arquivos via input: {e}")
        close_overlays(page)
        return False


def upload_files_from_path(page, context, path: Path, ext: str):
    """Usa uma instância já aberta do navegador para fazer upload de arquivos."""
    open_capcut_page(page)

    files = sorted(f for f in path.glob(f"*{ext}"))
    if not files:
        log(f"⚠️ Nenhum arquivo {ext} encontrado em {path}")
        return

    log(f"📂 {len(files)} arquivos '{ext}' encontrados para upload.")

    if not upload_files_via_input(page, [str(f) for f in files]):
        log(f"❌ Falha ao enviar arquivos {ext}. Encerrando upload desse tipo...")
        return

    for file in files:
        log(f"⏰ Aguardando upload de '{file.name}' na grid...")
        close_overlays(page)
        if wait_for_file_in_grid(page, file.name):
            log(f"✅ Upload concluído de '{file.name}'")
        else:
            log(f"❌ '{file.name}' não apareceu na grid após upload.")

    close_overlays(page)
    log("💾 Salvando storage_state atualizado...")
    save_storage_state(context)
    log("✅ Storage_state salvo com sucesso.")


def main_capcut_files_uploader():
    if log_file.exists():
        log_file.unlink()

    log("🚀 Inicializando navegador Playwright...")
    p, browser, context, page = launch_capcut(headless=False)
    log("✅ Navegador iniciado.")

    try:
        upload_files_from_path(page, context, media_audios_fundo_PATH, ".mp3")
        upload_files_from_path(page, context, media_audios_narracao_PATH, ".mp3")
        upload_files_from_path(page, context, media_videos_PATH, ".mp4")
    finally:
        log("🧹 Fechando navegador...")
        try:
            context.close()
            browser.close()
            p.stop()
            log("✅ Navegador fechado com segurança.")
        except Exception as e:
            log(f"⚠️ Erro ao fechar navegador: {e}")
