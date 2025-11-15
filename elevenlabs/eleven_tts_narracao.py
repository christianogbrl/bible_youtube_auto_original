# eleven_tts_narracao.py
from pathlib import Path
import json
import re
import time
import csv
from elevenlabs import ElevenLabs, VoiceSettings

SECTION_PREFIXES = {
    "INTRODUÇÃO": "1_intro",
    "LEITURA VERSÍCULO": "2_leitura",
    "EXPLICAÇÃO": "3_explicacao",
    "ORAÇÃO": "4_oracao",
    "CONCLUSÃO": "5_conclusao"
}

def load_json(file_path: Path):
    if not file_path.is_file():
        return None
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

def parse_txt_sections(file_path: Path):
    if not file_path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    text = file_path.read_text(encoding="utf-8")
    pattern = r"\d+\.\s*\[(.*?)\]"
    splits = re.split(pattern, text)
    sections = {}
    for i in range(1, len(splits), 2):
        title = splits[i].strip()
        content = splits[i + 1].strip()
        sections[title] = [p.strip() for p in content.split("\n\n") if p.strip()]
    return sections

def get_remaining_credits(client: ElevenLabs):
    try:
        user_info = client.user.get()
        sub = user_info.subscription
        used_chars = sub.character_count
        limit_chars = sub.character_limit
        remaining_chars = limit_chars - used_chars
        used_minutes = getattr(sub, "voice_generation_seconds", 0) / 60
        limit_minutes = getattr(sub, "voice_generation_seconds_limit", 0) / 60
        remaining_minutes = limit_minutes - used_minutes if limit_minutes > 0 else 0
        return remaining_chars, remaining_minutes
    except Exception as e:
        print(f"❌ Erro ao verificar créditos: {e}")
        return 0, 0

def check_credits(keys_file: Path):
    keys_data = load_json(keys_file)
    if not keys_data:
        print("Nenhuma chave válida encontrada no arquivo.")
        return []
    api_keys = keys_data.get("eleven_api_keys", [])
    if not api_keys:
        print("Nenhuma chave ElevenLabs encontrada no arquivo.")
        return []

    clients = []
    print("\n🔎 Créditos disponíveis nas contas ElevenLabs:")
    for key_info in api_keys:
        account = key_info.get("eleven_account")
        api_key = key_info.get("api_key")
        client = ElevenLabs(api_key=api_key)
        remaining_chars, remaining_minutes = get_remaining_credits(client)
        print(f" - Conta {account}: {remaining_chars} caracteres | {remaining_minutes:.2f} min de áudio restantes")
        clients.append({"account": account, "client": client})
    print("-" * 50)
    return clients

def generate_speech_and_mapping(sections, source_label, config, clients, audios_dir: Path, txt_dir: Path, mapping_json_file: Path, mapping_csv_file: Path):
    audios_dir.mkdir(exist_ok=True)
    txt_dir.mkdir(exist_ok=True)
    mapping = []

    file_counter = 1  # Contador global para numerar os arquivos

    for title, paragraphs in sections.items():
        prefix = SECTION_PREFIXES.get(title.upper(), "unknown_section")
        for idx, paragraph in enumerate(paragraphs, 1):
            output_txt_file = None
            output_audio_file = None
            success = False

            for client_info in clients:
                account = client_info["account"]
                client = client_info["client"]

                remaining_chars, _ = get_remaining_credits(client)
                if remaining_chars < len(paragraph):
                    print(f"⚠️ Conta {account} sem créditos suficientes ({remaining_chars} < {len(paragraph)}). Tentando próxima...")
                    continue

                try:
                    voice_settings = VoiceSettings(
                        stability=config.get("eleven_tts_stability", 0.0),
                        similarity_boost=config.get("eleven_tts_similarity_boost", 1.0),
                        style=config.get("eleven_tts_style", 0.0),
                        use_speaker_boost=config.get("eleven_tts_use_speaker_boost", True)
                    )

                    timestamp = int(time.time())
                    # Novo nome com contador sequencial
                    seq_prefix = str(file_counter).zfill(2)
                    output_audio_file = audios_dir / f"{seq_prefix}_{prefix}_parag_{idx}_{timestamp}.mp3"

                    # Conversão de texto para áudio
                    audio_gen = client.text_to_speech.convert(
                        voice_id=config.get("eleven_tts_voice_id"),
                        text=paragraph,
                        model_id=config.get("eleven_tts_model_id", "eleven_multilingual_v2"),
                        output_format="mp3_44100_128",
                        voice_settings=voice_settings
                    )

                    with open(output_audio_file, "wb") as f:
                        for chunk in audio_gen:
                            f.write(chunk)

                    # Backup TXT
                    output_txt_file = txt_dir / f"{seq_prefix}_{prefix}_parag_{idx}.txt"
                    output_txt_file.write_text(paragraph, encoding="utf-8")

                    print(f"✅ Áudio gerado: {output_audio_file.name} (Fonte: {source_label}) usando conta {account}")
                    success = True
                    file_counter += 1  # Incrementa para o próximo arquivo
                    break
                except Exception as e:
                    print(f"❌ Erro ao usar a conta {account}: {e}")

            if success and output_audio_file and output_txt_file:
                mapping.append({
                    "seção": title,
                    "parágrafo": idx,
                    "arquivo_mp3": str(output_audio_file.relative_to(audios_dir.parent)),
                    "arquivo_txt": str(output_txt_file.relative_to(txt_dir.parent)),
                    "texto_paragrafo": paragraph,
                    "fonte": source_label
                })
            else:
                print(f"❌ Não foi possível gerar áudio para parágrafo {idx} da seção {title}")


def main_eleven_tts_narracao():
    BASE_DIR = Path(__file__).resolve().parent.parent
    config_file = BASE_DIR / "utils" / "config.json"
    pregacao_json = BASE_DIR / "gemini" / "gemini_narracao_gerada.json"
    pregacao_txt = BASE_DIR / "gemini" / "gemini_narracao_gerada.txt"
    audios_dir = BASE_DIR / "media_audios_narracao"
    txt_dir = BASE_DIR / "eleven_narracao_txt_backup"
    
    ELEVEN_DIR = Path(__file__).resolve().parent
    mapping_json_file = ELEVEN_DIR / "eleven_narracao_mapeamento.json"
    mapping_csv_file = ELEVEN_DIR / "eleven_narracao_mapeamento.csv"
    eleven_keys_file = ELEVEN_DIR / "eleven_api_keys.json"

    clients = check_credits(eleven_keys_file)
    if not clients:
        print("❌ Nenhuma chave válida disponível para gerar áudio.")
        exit(1)

    if pregacao_txt.is_file() and pregacao_txt.stat().st_size > 0:
        print("✅ Pregação carregada do TXT.")
        sections = parse_txt_sections(pregacao_txt)
        source_label = "TXT"
    else:
        print("⚠️ Falha ao carregar TXT. Usando JSON como fallback.")
        sections = load_json(pregacao_json)
        if not sections:
            print("❌ Nenhum arquivo válido encontrado para gerar a pregação.")
            exit(1)
        source_label = "JSON"

    config = load_json(config_file) or {}

    generate_speech_and_mapping(sections, source_label, config, clients, audios_dir, txt_dir, mapping_json_file, mapping_csv_file)

    print("🎉 Workflow completo: áudios, TXT, JSON e CSV gerados com sucesso!")
