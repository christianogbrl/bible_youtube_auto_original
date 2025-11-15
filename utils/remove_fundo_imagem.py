from pathlib import Path
from rembg import remove
from PIL import Image
import io
from datetime import datetime

# =====================================================
# ⚙️ CONFIGURAÇÕES DE PASTAS
# =====================================================
base_path = Path(__file__).resolve().parent
input_folder = base_path / "media_imagens_originais"
output_folder = base_path / "media_imagens_sem_fundo"
log_file = output_folder / "log_processamento.txt"

# Cria as pastas se não existirem
input_folder.mkdir(exist_ok=True)
output_folder.mkdir(exist_ok=True)

# =====================================================
# 🧠 PROCESSAMENTO DAS IMAGENS
# =====================================================
processed_count = 0
skipped_count = 0
error_count = 0

# Inicia log
with log_file.open("a", encoding="utf-8") as log:
    log.write("\n" + "="*60 + "\n")
    log.write(f"🕒 Início do processamento: {datetime.now()}\n")
    log.write("="*60 + "\n")

    for file_path in input_folder.iterdir():
        if file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            output_path = output_folder / f"{file_path.stem}_sem_fundo.png"

            try:
                # Verifica se já foi processada
                if output_path.exists():
                    msg = f"⚠️ Pulado (já processada): {file_path.name}"
                    print(msg)
                    log.write(msg + "\n")
                    skipped_count += 1
                    continue

                # Lê imagem original
                with file_path.open("rb") as i:
                    input_data = i.read()

                # Remove fundo
                output_data = remove(input_data)
                output_image = Image.open(io.BytesIO(output_data)).convert("RGBA")

                # Salva imagem mantendo dimensões e qualidade originais
                output_image.save(output_path)

                msg = f"✅ Processada: {file_path.name} -> {output_path.name}"
                print(msg)
                log.write(msg + "\n")
                processed_count += 1

            except Exception as e:
                msg = f"❌ Erro ao processar {file_path.name}: {e}"
                print(msg)
                log.write(msg + "\n")
                error_count += 1

    # =====================================================
    # 📊 RESUMO FINAL
    # =====================================================
    total_images = processed_count + skipped_count + error_count
    log.write("\n========== 🧾 RESUMO FINAL ==========\n")
    log.write(f"📁 Total de imagens encontradas: {total_images}\n")
    log.write(f"✅ Processadas: {processed_count}\n")
    log.write(f"⚠️ Puladas (já existentes): {skipped_count}\n")
    log.write(f"❌ Com erro: {error_count}\n")
    log.write(f"🕒 Finalizado em: {datetime.now()}\n")
    log.write("=====================================\n")

print("\n🎉 Processamento concluído! Veja o log detalhado em:")
print(f"📄 {log_file}")
