import os
import json
import requests
from tqdm import tqdm
from pathlib import Path

# =========================
# Funções auxiliares
# =========================

def carregar_config(caminho_config="config.json"):
    caminho = Path(__file__).parent.parent / "utils" / caminho_config
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {caminho}")
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)

def validar_api_key(api_key):
    """Testa se a API key é válida usando o endpoint /me/"""
    url = "https://freesound.org/apiv2/me/"
    params = {"token": api_key}
    try:
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            dados = resp.json()
            print(f"✅ API key válida! Usuário: {dados.get('username')}, E-mail: {dados.get('email')}")
            return True
        else:
            print(f"❌ API key inválida ou expirada! Status: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar API key: {e}")
        return False

def buscar_sons_freesound(api_key, termo, por_pagina=5, ordem="downloads_desc"):
    url = "https://freesound.org/apiv2/search/text/"
    params = {
        "query": termo,
        "token": api_key,
        "page_size": por_pagina,
        "sort": ordem
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json().get("results", [])

def baixar_preview(url, destino):
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    tamanho = int(resp.headers.get('content-length', 0))
    with open(destino, 'wb') as f, tqdm(total=tamanho, unit='B', unit_scale=True, desc=os.path.basename(destino)) as barra:
        for chunk in resp.iter_content(1024):
            if chunk:
                f.write(chunk)
                barra.update(len(chunk))

# =========================
# Função principal
# =========================

def main():
    config = carregar_config()

    api_key = config.get("freesound_api_key", "").strip()
    if not api_key:
        print("❌ API key não encontrada no config.json")
        return

    if not validar_api_key(api_key):
        print("❌ Pare a execução e verifique sua API key no Freesound.")
        return

    termos_busca = config.get("freesound_termos_busca", [])
    resultados_por_termo = config.get("freesound_resultados_por_termo", 5)
    ordem = config.get("freesound_ordem", "downloads_desc")

    pasta_destino = Path(__file__).parent.parent / "media_audios_fundo"
    pasta_destino.mkdir(parents=True, exist_ok=True)

    print(f"\n📥 Baixando áudios da Freesound para: {pasta_destino}\n")

    for termo in termos_busca:
        print(f"🔎 Buscando: {termo}")
        try:
            resultados = buscar_sons_freesound(api_key, termo, resultados_por_termo, ordem)
        except Exception as e:
            print(f"❌ Erro ao buscar '{termo}': {e}")
            continue

        if not resultados:
            print(f"⚠️ Nenhum áudio encontrado para '{termo}'.\n")
            continue

        for som in resultados:
            nome_base = som.get("name", f"som_{som.get('id')}")
            nome_arquivo = nome_base.replace(" ", "_").replace(",", "_") + ".mp3"
            destino = pasta_destino / nome_arquivo

            previews = som.get("previews", {})
            preview_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3") or previews.get("preview")

            if not preview_url:
                print(f"⚠️ Não achei preview para {nome_base}, pulando.")
                continue

            if not destino.exists():
                print(f"⬇️  Baixando: {nome_arquivo}")
                try:
                    baixar_preview(preview_url, destino)
                except Exception as e:
                    print(f"⚠️ Erro ao baixar {nome_arquivo}: {e}")
            else:
                print(f"⏩ Já existe: {nome_arquivo}")
        print()

    print("✅ Todos os downloads concluídos!")

if __name__ == "__main__":
    main()
