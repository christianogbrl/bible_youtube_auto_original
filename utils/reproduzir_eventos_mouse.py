import time
from pathlib import Path
from capcut_browser import launch_capcut, save_storage_state

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
EVENTOS_PATH = Path(__file__).resolve().parent.parent / "eventos.txt"

EDITOR_URL = (
    "https://www.capcut.com/editor?"
    "from_page=work_space&start_tab=video&enter_from=create_project"
    "&tab=all&__action_from=Christiano&workspaceId=7533642151549386813&scenario=custom"
)

def reproduzir_eventos():
    if not EVENTOS_PATH.exists():
        print("❌ Nenhum arquivo 'eventos.txt' encontrado.")
        return

    eventos = EVENTOS_PATH.read_text(encoding="utf-8").splitlines()
    if not eventos:
        print("⚠️ Arquivo de eventos está vazio.")
        return

    p, browser, context, page = launch_capcut(headless=False)
    page.set_viewport_size({"width": WINDOW_WIDTH, "height": WINDOW_HEIGHT})
    page.goto(EDITOR_URL, timeout=120000)
    print("🌐 Editor do CapCut aberto — reproduzindo eventos...\n")

    time.sleep(5)

    for linha in eventos:
        linha = linha.strip()
        if not linha:
            continue

        if linha.startswith("CLICK:"):
            _, coords = linha.split(":")
            x, y = map(int, coords.split(","))
            print(f"🖱️ Clique em ({x}, {y})")
            page.mouse.click(x, y)
            time.sleep(0.3)

        elif linha.startswith("DRAG:"):
            partes = linha.replace("DRAG:", "").split("->")
            start = list(map(int, partes[0].strip().split(",")))
            end = list(map(int, partes[1].strip().split(",")))
            print(f"🖱️ Arrastando de ({start[0]},{start[1]}) até ({end[0]},{end[1]})")

            page.mouse.move(start[0], start[1])
            page.mouse.down()
            page.mouse.move(end[0], end[1], steps=15)
            page.mouse.up()
            time.sleep(0.4)

    print("\n✅ Reproduzido com sucesso.")
    save_storage_state(context)
    browser.close()
    p.stop()


if __name__ == "__main__":
    reproduzir_eventos()
