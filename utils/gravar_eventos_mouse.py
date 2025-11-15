import threading
import time
from pathlib import Path
from capcut_browser import launch_capcut, save_storage_state
from pynput import keyboard
from playwright.sync_api import Error as PlaywrightError

# Configurações
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
gravando = False

# Caminho para salvar logs
EVENTOS_PATH = Path(__file__).resolve().parent.parent / "utils" / "eventos.txt"
EVENTOS_PATH.parent.mkdir(parents=True, exist_ok=True)

EDITOR_URL = (
    "https://www.capcut.com/editor?"
    "from_page=work_space&start_tab=video&enter_from=create_project"
    "&tab=all&__action_from=Christiano&workspaceId=7533642151549386813&scenario=custom"
)

# Buffer em memória para eventos que ainda não foram gravados
eventos_buffer = []
buffer_lock = threading.Lock()

def listener_teclado():
    """Escuta teclas Q e W para iniciar/pausar a gravação."""
    global gravando
    def on_press(key):
        global gravando
        try:
            if key.char == 'q' and not gravando:
                gravando = True
                print("▶️ Gravação iniciada.")
            elif key.char == 'w' and gravando:
                gravando = False
                print("⏸️ Gravação pausada.")
        except AttributeError:
            pass

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

def salvar_eventos():
    """Salva eventos do buffer no disco continuamente."""
    while True:
        time.sleep(0.5)
        with buffer_lock:
            if eventos_buffer:
                try:
                    with open(EVENTOS_PATH, "a", encoding="utf-8") as f:
                        for e in eventos_buffer:
                            f.write(f"{e}\n")
                        eventos_buffer.clear()
                except Exception as e:
                    print(f"⚠️ Erro ao salvar evento: {e}")

def gravar_eventos():
    """Abre CapCut e captura cliques/arrastos via Playwright."""
    global gravando

    print("🚀 Iniciando navegador CapCut com cookies...")
    p, browser, context, page = launch_capcut(headless=False)

    page.set_viewport_size({"width": WINDOW_WIDTH, "height": WINDOW_HEIGHT})
    page.goto(EDITOR_URL, timeout=120000)
    print("🌐 Editor do CapCut aberto.")
    print("🖱️ Pressione [Q] para iniciar e [W] para pausar a gravação. CTRL+C para sair.\n")

    # Função Python exposta para receber eventos do JS
    def registrar_evento(evento: str):
        if gravando:
            print(f"[EVENTO] {evento}")  # Mostra no terminal
            with buffer_lock:
                eventos_buffer.append(evento)

    page.expose_function("registrar_evento", registrar_evento)

    # JS injetado para capturar cliques/arrastos + banner
    script = """
    if (!window.__CAPCUT_CAPTURE__) {
        window.__CAPCUT_CAPTURE__ = true;
        let isDragging = false;
        let startX = 0, startY = 0;

        // Cria banner
        const banner = document.createElement('div');
        banner.style.position = 'fixed';
        banner.style.top = '0';
        banner.style.left = '0';
        banner.style.width = '100%';
        banner.style.height = '30px';
        banner.style.backgroundColor = 'red';
        banner.style.color = 'white';
        banner.style.fontWeight = 'bold';
        banner.style.display = 'flex';
        banner.style.alignItems = 'center';
        banner.style.justifyContent = 'center';
        banner.style.zIndex = '999999';
        banner.innerText = 'PAUSADO';
        document.body.appendChild(banner);

        // Função para atualizar banner
        window.atualizarBanner = function(gravando) {
            if (gravando) {
                banner.style.backgroundColor = 'green';
                banner.innerText = 'GRAVANDO';
            } else {
                banner.style.backgroundColor = 'red';
                banner.innerText = 'PAUSADO';
            }
        };

        document.addEventListener('mousedown', e => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
        });

        document.addEventListener('mouseup', e => {
            if (isDragging) {
                let endX = e.clientX;
                let endY = e.clientY;
                if (Math.abs(startX - endX) < 3 && Math.abs(startY - endY) < 3) {
                    window.registrar_evento(`CLICK: ${startX},${startY}`);
                } else {
                    window.registrar_evento(`DRAG: ${startX},${startY} -> ${endX},${endY}`);
                }
            }
            isDragging = false;
        });
    }
    """
    page.evaluate(script)

    try:
        while True:
            # Atualiza banner conforme estado atual
            page.evaluate(f"window.atualizarBanner({str(gravando).lower()})")
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\n🛑 Gravação encerrada pelo usuário.")
    except PlaywrightError as e:
        print(f"❗ Erro Playwright: {e}")
    finally:
        # Garante salvar quaisquer eventos restantes
        with buffer_lock:
            if eventos_buffer:
                try:
                    with open(EVENTOS_PATH, "a", encoding="utf-8") as f:
                        for e in eventos_buffer:
                            f.write(f"{e}\n")
                except Exception as e:
                    print(f"⚠️ Erro ao salvar evento: {e}")

        print(f"📁 Eventos gravados em: {EVENTOS_PATH.resolve()}")
        try:
            save_storage_state(context)
        except PlaywrightError as e:
            print(f"⚠️ Não foi possível salvar storage_state: {e}")
        browser.close()
        p.stop()

if __name__ == "__main__":
    # Thread de teclado
    thread_teclado = threading.Thread(target=listener_teclado, daemon=True)
    thread_teclado.start()

    # Thread para salvar eventos continuamente
    thread_salvar = threading.Thread(target=salvar_eventos, daemon=True)
    thread_salvar.start()

    # Thread principal roda o navegador
    gravar_eventos()
