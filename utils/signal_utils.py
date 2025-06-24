import os
import json
from datetime import datetime
import pytz

def save_signal_log(entry: dict, log_path: str = "signals_log.json"):
    """
    Guarda una señal (FREE o VIP) en signals_log.json de forma estructurada como lista JSON.
    """
    signals_log = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            try:
                signals_log = json.load(f)
            except json.JSONDecodeError:
                pass

    signals_log.append(entry)

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(signals_log, f, ensure_ascii=False, indent=2)

def get_ny_timestamp_iso() -> str:
    """
    Retorna el timestamp actual en formato ISO 8601 con zona horaria de Nueva York.
    """
    tz = pytz.timezone("America/New_York")
    return datetime.now(tz).isoformat()


# Watermark utility
from PIL import Image

def apply_gamma_watermark(input_path: str, output_path: str, watermark_path: str = "gamma_logo_watermark.png"):
    """
    Aplica un watermark PNG transparente encima de una imagen y guarda la imagen resultante.
    """
    try:
        if not os.path.exists(input_path):
            print(f"❌ Imagen base no encontrada: {input_path}")
            return
        if not os.path.exists(watermark_path):
            print(f"❌ Logo de watermark no encontrado: {watermark_path}")
            return

        base_image = Image.open(input_path).convert("RGBA")
        watermark = Image.open(watermark_path).convert("RGBA")

        # Redimensionar el watermark proporcionalmente si es demasiado grande
        scale = 0.25
        wm_width = int(base_image.width * scale)
        wm_height = int(watermark.height * (wm_width / watermark.width))
        watermark = watermark.resize((wm_width, wm_height))

        # Posicionar en la esquina inferior derecha con margen
        margin = 20
        position = (base_image.width - wm_width - margin, base_image.height - wm_height - margin)

        # Componer imagen con watermark
        transparent = Image.new("RGBA", base_image.size)
        transparent.paste(base_image, (0, 0))
        transparent.paste(watermark, position, mask=watermark)
        transparent.convert("RGB").save(output_path, "PNG")

    except Exception as e:
        print(f"❌ Error aplicando watermark: {e}")

def apply_gamma_watermark_vip(input_path: str, output_path: str, watermark_path: str = "gamma_logo_watermark.png"):
    """
    Aplica un watermark a una imagen de señal VIP. Reutiliza la función base.
    """
    apply_gamma_watermark(input_path, output_path, watermark_path)