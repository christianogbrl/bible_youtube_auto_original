# scraper_versiculo.py
import asyncio
import json
import logging
import os
import random
import subprocess
from pathlib import Path
from typing import Union, Dict, List, Optional

from playwright.async_api import async_playwright, Browser, Page, BrowserContext, Playwright

# ============================================================
# 1️⃣ LOGGING E CONFIGURAÇÃO DE CAMINHOS
# ============================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class Paths:
    """
    Centraliza todos os caminhos do projeto.
    Todos os arquivos padrão são resolvidos dentro da pasta raiz do projeto.
    """
    BASE_DIR = Path(__file__).resolve().parent.parent
    CONFIG_FILE = BASE_DIR / "utils" / "config.json"
    DEFAULT_BOOKS_FILE = BASE_DIR / "utils" / "bible_books.json"
    
    SCRAPER_DIR = Path(__file__).resolve().parent
    DEFAULT_OUTPUT_FILE = SCRAPER_DIR / "scraper_versiculo_gerado.json"

    @classmethod
    def resolve_config(cls, custom_path: Union[str, Path, None] = None) -> Path:
        """Retorna o caminho absoluto do config.json."""
        path = Path(custom_path) if custom_path else cls.CONFIG_FILE
        path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {path}")
        return path

    @classmethod
    def resolve_books_file(cls, config: Dict) -> Path:
        """Retorna o caminho absoluto do arquivo de livros da Bíblia."""
        file_path = Path(config.get("scraper_books_file", cls.DEFAULT_BOOKS_FILE))
        if not file_path.is_absolute():
            file_path = cls.BASE_DIR / file_path
        return file_path.resolve()

    @classmethod
    def resolve_output_file(cls, config: Dict) -> Path:
        """Retorna o caminho absoluto do arquivo de saída."""
        file_path = Path(config.get("scraper_output_file", cls.DEFAULT_OUTPUT_FILE))
        if not file_path.is_absolute():
            file_path = cls.BASE_DIR / file_path
        return file_path.resolve()


# ============================================================
# 2️⃣ FUNÇÕES DE COMPORTAMENTO HUMANO
# ============================================================

async def random_delay(min_sec: float = 1.5, max_sec: float = 3.5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))


def get_random_user_agent() -> str:
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/122.0.0.0 Mobile Safari/604.1",
        "Mozilla/5.0 (Linux; Android 12; moto g(60)) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.105 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; rv:123.0) Gecko/20100101 Firefox/123.0"
    ]
    return random.choice(user_agents)


async def random_mouse_movement(page: Page):
    viewport = page.viewport_size or {"width": 1280, "height": 720}
    x = random.randint(0, viewport["width"])
    y = random.randint(0, viewport["height"])
    try:
        await page.mouse.move(x, y, steps=random.randint(5, 25))
    except Exception:
        # não falha por movimentos
        pass


async def scroll_randomly(page: Page):
    for _ in range(random.randint(1, 3)):
        scroll_distance = random.randint(50, 400)
        direction = random.choice([1, -1])
        try:
            # usar evaluate para rolar via JS caso mouse.wheel não funcione corretamente
            await page.evaluate(
                """([dy]) => { window.scrollBy({ top: dy, left: 0, behavior: 'smooth' }); }""",
                [direction * scroll_distance]
            )
        except Exception:
            pass
        await asyncio.sleep(random.uniform(0.3, 0.8))


async def random_mouse_click(page: Page):
    viewport = page.viewport_size or {"width": 1280, "height": 720}
    x = random.randint(100, max(100, viewport["width"] - 100))
    y = random.randint(100, max(100, viewport["height"] - 100))
    try:
        await page.mouse.move(x, y, steps=random.randint(3, 10))
        await asyncio.sleep(random.uniform(0.2, 0.5))
        await page.mouse.click(x, y)
    except Exception:
        pass


async def pause_like_reading():
    await asyncio.sleep(random.uniform(1.0, 3.5))


async def simulate_human_behavior(page: Page):
    await random_delay()
    behaviors = [
        lambda: random_mouse_movement(page),
        lambda: scroll_randomly(page),
        lambda: random_mouse_click(page),
        lambda: pause_like_reading()
    ]
    selected_behaviors = random.sample(behaviors, k=random.randint(1, min(3, len(behaviors))))
    for behavior in selected_behaviors:
        try:
            await behavior()
        except Exception:
            pass
    if random.random() < 0.5:
        await asyncio.sleep(random.uniform(0.2, 0.6))


# ============================================================
# 3️⃣ BROWSER CONTROLLER (REFATORADO PARA CONTEXTOS CORRETOS)
# ============================================================

class BrowserController:
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start_browser(self, headless: bool = True):
        """Inicializa o Playwright e abre o browser (com contexto para aplicar user-agent)."""
        # Tentativa de garantir que o Chromium esteja instalado (não obrigatório)
        try:
            cache_path = "/opt/render/.cache/ms-playwright"
            if not os.path.exists(cache_path):
                logging.info("Playwright provavelmente não está instalado no ambiente. Tentando instalar o Chromium com 'playwright install chromium'...")
                # não usar check=True para evitar exceções que parem a execução sem tratamento
                subprocess.run(["playwright", "install", "chromium"], check=False)
        except Exception as e:
            logging.debug(f"Ignorando erro ao tentar instalar o Playwright via subprocess: {e}")

        # Inicia Playwright
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=headless)
            await self._create_new_page()
            logging.info("Browser iniciado com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao iniciar Playwright/browser: {e}")
            # tenta cleanup parcial
            await self.close_browser()
            raise

    async def _create_new_page(self):
        """Cria um novo contexto + página com User-Agent aleatório."""
        # fechar página/contexto atual se existir
        try:
            if self.page and not self.page.is_closed():
                await self.page.close()
        except Exception:
            pass

        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass

        # Cria novo contexto com user agent
        ua = get_random_user_agent()
        # podemos configurar viewport se necessário; deixando default por enquanto
        self.context = await self.browser.new_context(user_agent=ua)
        self.page = await self.context.new_page()
        logging.debug("Novo contexto/página criado. User-Agent aplicado.")

    async def restart_page(self):
        """Recria a página (novo contexto também)."""
        await self._create_new_page()

    async def close_browser(self):
        """Fecha página, contexto, browser e Playwright."""
        try:
            if self.page and not self.page.is_closed():
                await self.page.close()
        except Exception:
            pass

        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass

        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass

        logging.info("Browser e Playwright finalizados.")


    async def goto(self, url: str, timeout: int = 30000):
        """Navega até uma URL e simula comportamento humano."""
        if not self.page:
            raise RuntimeError("Página não iniciada.")
        try:
            await self.page.goto(url, timeout=timeout)
            # aguardar carregamento mínimo do body
            try:
                await self.page.wait_for_selector("body", timeout=5000)
            except Exception:
                pass
            await simulate_human_behavior(self.page)
            logging.info(f"Navegou para {url}")
        except Exception as e:
            logging.error(f"Falha ao acessar URL {url}: {e}")
            raise


# ============================================================
# 4️⃣ SCRAPER PRINCIPAL
# ============================================================

SELECTORS = {
    "chapter_container": "div[class^='ChapterContent_reader__']",
    "verse_number": "span[class^='ChapterContent_label__']",
    "verse_text": "span[class^='ChapterContent_content__']"
}


class RandomVerseScraper:
    def __init__(self, config_path: Union[str, Path] = None):
        # Caminhos centralizados via Paths
        self.config_path = Paths.resolve_config(config_path)

        # Carrega configuração
        with open(self.config_path, "r", encoding="utf-8") as f:
            full_config = json.load(f)
        # manter apenas chaves que começam com scraper_ (como no original)
        self.config = {k: v for k, v in full_config.items() if k.startswith("scraper_")}

        # Configurações básicas
        self.base_url = self.config.get("scraper_base_url", "https://www.bibliaonline.com.br")
        self.translation = self.config.get("scraper_translation", "NVI")
        self.max_retries = int(self.config.get("scraper_max_verse_retries", 3))
        self.headless = bool(self.config.get("scraper_headless", True))

        # Caminhos resolvidos via Paths
        self.books_file = Paths.resolve_books_file(self.config)
        self.output_path = Paths.resolve_output_file(self.config)

        # Controlador de navegador
        self.browser = BrowserController()

        logging.info(f"Caminho do config.json: {self.config_path}")
        logging.info(f"Caminho do bible_books.json: {self.books_file}")
        logging.info(f"Caminho do arquivo de saída: {self.output_path}")

    def _load_books(self) -> List[Dict]:
        if not self.books_file.exists():
            raise FileNotFoundError(f"Arquivo de livros não encontrado: {self.books_file}")
        with open(self.books_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _choose_random_reference(self, books: List[Dict]):
        book = random.choice(books)
        chapter = random.randint(1, max(1, int(book.get("chapters", 1))))
        return book, chapter

    async def start(self):
        """Executa o processo completo de scraping."""
        try:
            logging.info("Iniciando scraper de versículo aleatório...")
            await self.browser.start_browser(headless=self.headless)
            books = self._load_books()
            verse_data = await self.scrape_random_verse(books)
            await self.save_to_json(verse_data)
            logging.info("Scraping concluído com sucesso.")
        except Exception as e:
            logging.error(f"Erro durante scraping: {e}")
            raise
        finally:
            await self.browser.close_browser()

    async def scrape_random_verse(self, books: List[Dict]) -> Dict:
        """Acessa um capítulo e seleciona um versículo aleatório."""
        book, chapter = self._choose_random_reference(books)
        url = f"{self.base_url}/{book['book_id']}.{chapter}.{self.translation}"
        logging.info(f"Acessando URL: {url}")

        # tentativa com retries simples para navegar
        retry = 0
        while True:
            try:
                await self.browser.goto(url)
                break
            except Exception as e:
                retry += 1
                logging.warning(f"Tentativa {retry} falhou ao acessar {url}: {e}")
                if retry >= max(1, self.max_retries):
                    raise RuntimeError(f"Não foi possível acessar {url} após {retry} tentativas.")
                await asyncio.sleep(1 + retry * 0.5)

        # aguarda seletor do capítulo
        try:
            await self.browser.page.wait_for_selector(SELECTORS["chapter_container"], timeout=10000)
        except Exception:
            logging.warning("Seletor de container do capítulo não encontrado com timeout. Tentando continuar...")

        container = await self.browser.page.query_selector(SELECTORS["chapter_container"])
        if not container:
            raise RuntimeError("Nenhum conteúdo encontrado na página.")

        spans = await container.query_selector_all("span")
        verses: List[tuple] = []
        last_num: Optional[int] = None

        for span in spans:
            class_name = await span.get_attribute("class") or ""
            text = (await span.inner_text()).strip()
            if "ChapterContent_label__" in class_name and text.isdigit():
                last_num = int(text)
            elif "ChapterContent_content__" in class_name and text:
                if last_num is not None:
                    verses.append((last_num, text))
                    last_num = None
                elif verses:
                    prev_num, prev_text = verses[-1]
                    verses[-1] = (prev_num, f"{prev_text} {text}")

        if not verses:
            raise RuntimeError("Nenhum versículo encontrado no capítulo.")

        chosen_verse = random.choice(verses)
        logging.info(f"Versículo sorteado: {book.get('name', book.get('book_id'))} {chapter}:{chosen_verse[0]}")

        return {
            "book_id": book["book_id"],
            "book_name": book.get("name", ""),
            "chapter": chapter,
            "verse": chosen_verse[0],
            "text": chosen_verse[1],
            "translation": self.translation,
            "url": url,
        }

    async def save_to_json(self, data: Dict):
        # garante diretório existente
        out_dir = self.output_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logging.info(f"Versículo salvo em: {self.output_path}")


# ============================================================
# 5️⃣ EXECUÇÃO PRINCIPAL
# ============================================================

def main_scraper_versiculo():
    try:
        logging.info("==== Iniciando execução do scraper ====")
        # se quiser passar um config personalizado, ajuste abaixo:
        asyncio.run(RandomVerseScraper().start())
        logging.info("==== Execução finalizada com sucesso ====")
    except KeyboardInterrupt:
        logging.warning("Execução interrompida pelo usuário.")
    except Exception as e:
        logging.error(f"Erro crítico durante a execução: {e}")
