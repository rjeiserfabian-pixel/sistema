"""
Utilidad para obtener el logo de la empresa para uso en PDFs.
Compatible con URLs de Cloudinary y rutas locales como fallback.
"""
import os
import requests
from io import BytesIO


def get_logo_buffer(empresa, use_ticket_logo=False):
    """
    Devuelve un BytesIO con la imagen del logo de la empresa,
    descargándola desde Cloudinary si es una URL, o cargándola
    desde el sistema local como fallback.

    Args:
        empresa: Instancia del modelo Empresa.

    Returns:
        BytesIO con la imagen, o None si no se pudo cargar.
    """
    if not empresa:
        return None

    logo_value = None
    if use_ticket_logo and hasattr(empresa, 'logo_ticket') and empresa.logo_ticket:
        logo_value = str(empresa.logo_ticket)
    elif hasattr(empresa, 'logo') and empresa.logo:
        logo_value = str(empresa.logo)

    if not logo_value:
        return None

    # ---- CASO 1: Es una URL de Cloudinary (o cualquier URL HTTP) ----
    if logo_value.startswith('http://') or logo_value.startswith('https://'):
        try:
            response = requests.get(logo_value, timeout=10)
            if response.status_code == 200:
                buf = BytesIO(response.content)
                buf.seek(0)
                return buf
        except Exception as e:
            print(f"[logo_utils] Error descargando logo desde URL: {e}")
        return None

    # ---- CASO 2: Es una ruta local (legacy) ----
    from django.conf import settings
    possible_paths = [
        os.path.join(settings.MEDIA_ROOT, logo_value),
        os.path.join(settings.BASE_DIR, 'static', logo_value),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    buf = BytesIO(f.read())
                    buf.seek(0)
                    return buf
            except Exception as e:
                print(f"[logo_utils] Error cargando logo local: {e}")

    return None


def get_logo_image_for_pdf(empresa, width_mm=40, height_mm=40, circular=True, use_ticket_logo=False):
    """
    Devuelve un objeto Image de ReportLab listo para insertar en un PDF,
    aplicando recorte circular opcional.

    Args:
        empresa: Instancia del modelo Empresa.
        width_mm (float): Ancho en milímetros para el PDF.
        height_mm (float): Alto en milímetros para el PDF.
        circular (bool): Si True, aplica máscara circular a la imagen.
        use_ticket_logo (bool): Si True, usa el logo para tickets en lugar del principal.

    Returns:
        Objeto Image de ReportLab, o None si no se pudo cargar.
    """
    from reportlab.platypus import Image as RLImage
    from reportlab.lib.units import mm

    logo_buf = get_logo_buffer(empresa, use_ticket_logo=use_ticket_logo)
    if not logo_buf:
        return None

    try:
        from PIL import Image as PILImage, ImageDraw

        img = PILImage.open(logo_buf).convert("RGBA")

        if circular:
            img.thumbnail((200, 200), PILImage.Resampling.LANCZOS if hasattr(PILImage, 'Resampling') else PILImage.ANTIALIAS)
            w, h = img.size
            bg = PILImage.new('RGBA', (200, 200), (255, 255, 255, 0))
            bg.paste(img, ((200 - w) // 2, (200 - h) // 2))
            
            mask = PILImage.new('L', (200, 200), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 200, 200), fill=255)
            output = PILImage.new('RGBA', (200, 200), (255, 255, 255, 0))
            output.paste(bg, (0, 0), mask=mask)
            img = output

        out_buf = BytesIO()
        img.save(out_buf, format='PNG')
        out_buf.seek(0)

        rl_img = RLImage(out_buf, width=width_mm * mm, height=height_mm * mm)
        rl_img.hAlign = 'CENTER'
        rl_img.preserveAspectRatio = True
        return rl_img

    except Exception as e:
        print(f"[logo_utils] Error procesando logo para PDF: {e}")
        # Intentar insertar sin procesamiento circular
        try:
            logo_buf2 = get_logo_buffer(empresa, use_ticket_logo=use_ticket_logo)
            if logo_buf2:
                rl_img = RLImage(logo_buf2, width=width_mm * mm, height=height_mm * mm)
                rl_img.hAlign = 'CENTER'
                rl_img.preserveAspectRatio = True
                return rl_img
        except Exception:
            pass

    return None
