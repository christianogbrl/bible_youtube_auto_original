# capcut_browser.py
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError

# =====================================================
# ⚙️ CONFIGURAÇÕES
# =====================================================
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

CAPCUT_DIR = Path(__file__).resolve().parent
COOKIES_PATH = CAPCUT_DIR / "capcut_login.json"
STORAGE_STATE_PATH = CAPCUT_DIR / "capcut_storage_state.json"

DEFAULT_URL_FOR_COOKIE = "https://www.capcut.com"


# =====================================================
# 📄 FUNÇÕES DE COOKIES
# =====================================================
def load_cookies_list(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and ("cookies" in data or "origins" in data):
        return None
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "cookies" in data and isinstance(data["cookies"], list):
        return data["cookies"]
    raise ValueError(f"Formato de cookie/storage_state não reconhecido em {path}")


def normalize_cookie_for_playwright(cookie: dict):
    cookie = cookie.copy()
    if "url" not in cookie:
        if "domain" in cookie:
            domain = cookie["domain"].lstrip(".")
            cookie["url"] = f"https://{domain}"
        else:
            cookie["url"] = DEFAULT_URL_FOR_COOKIE
    return cookie


# =====================================================
# 🚀 INICIALIZAR BROWSER CAPCUT
# =====================================================
def launch_capcut(headless: bool = False):
    """
    Inicializa o navegador com cookies ou storage_state já logados e
    retorna (p, browser, context, page) para uso.
    """
    if not COOKIES_PATH.exists():
        raise FileNotFoundError(f"Arquivo de cookies não encontrado em: {COOKIES_PATH}")

    cookies_list = load_cookies_list(COOKIES_PATH)

    p = sync_playwright().start()
    browser = p.chromium.launch(
        headless=headless,
        args=["--start-maximized"],
    )

    context = None

    # ✅ Cria contexto com tamanho fixo
    viewport_settings = {"viewport": {"width": WINDOW_WIDTH, "height": WINDOW_HEIGHT}}

    # Tenta usar storage_state diretamente
    if cookies_list is None:
        try:
            context = browser.new_context(storage_state=str(COOKIES_PATH), **viewport_settings)
            print("Usando arquivo como storage_state do Playwright.")
        except PlaywrightError as e:
            print("Falha ao carregar storage_state diretamente:", e)

    if context is None:
        context = browser.new_context(**viewport_settings)
        if cookies_list:
            normalized = [normalize_cookie_for_playwright(c) for c in cookies_list]
            try:
                context.add_cookies(normalized)
                print(f"{len(normalized)} cookies adicionados ao contexto.")
            except PlaywrightError as e:
                print("Erro ao adicionar cookies:", e)

    page = context.new_page()
    page.set_viewport_size({"width": WINDOW_WIDTH, "height": WINDOW_HEIGHT})
    print(f"Janela configurada para {WINDOW_WIDTH}x{WINDOW_HEIGHT}.")
    return p, browser, context, page


# =====================================================
# 💾 SALVAR STORAGE STATE
# =====================================================
def save_storage_state(context):
    context.storage_state(path=str(STORAGE_STATE_PATH))
    print(f"Storage state atualizado salvo em: {STORAGE_STATE_PATH}")
