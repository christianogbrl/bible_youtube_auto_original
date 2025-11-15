from playwright.sync_api import sync_playwright

def save_login_state():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=50,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1280, "height": 720}
        )

        page = context.new_page()
        print("➡️ Acessando o CapCut com navegador 'camuflado'...")
        page.goto("https://www.capcut.com/editor", timeout=60000)

        print("⚠️ Faça login manualmente no navegador que abriu.")
        print("Quando estiver logado e ver o editor, pressione Enter aqui no terminal.")
        input()

        # Salvar cookies e storage
        context.storage_state(path="capcut_login.json")
        print("✅ Login salvo no arquivo capcut_login.json")

        browser.close()

if __name__ == "__main__":
    save_login_state()
