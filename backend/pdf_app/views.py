from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from backend.conexiones import conectar_Anatomia_Patologica
from datetime import datetime
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO
import base64
import re
import unicodedata
import json

from django.conf import settings
from pathlib import Path



from .crypto_utils import make_pdf_token   # 🔹 Asegúrate de haber creado este módulo



from django.http import HttpResponse, HttpResponseBadRequest
from .crypto_utils import parse_pdf_token

def generar_pdf_token(request, token):
    try:
        payload = parse_pdf_token(token)
        rut = payload["rut"]
        numero_biopsia = payload["num"]
    except Exception:
        return HttpResponseBadRequest("Enlace inválido o expirado.")
    # Reutiliza tu lógica actual:
    return generar_pdf(request, rut, numero_biopsia)


# views.py (agregar al inicio)
from django.views.decorators.csrf import csrf_exempt
from .crypto_utils import make_access_token, parse_access_token
from cryptography.fernet import InvalidToken

# views.py
from django.views.decorators.http import require_http_methods
from functools import wraps

def require_api_key(view_func):
    """Decorator para validar API key."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        expected_key = getattr(settings, "API_KEY", None)
        
        if not expected_key or api_key != expected_key:
            return JsonResponse({"error": "No autorizado"}, status=403)
        
        return view_func(request, *args, **kwargs)
    return wrapper

@csrf_exempt
@require_api_key  # 🔹 Agregar protección
def generate_access_token(request):
    """
    Genera un token de acceso cifrado para un RUT.
    POST /api/generate-access-token/
    Body: {"rut": "12345678-9"}
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)
    
    try:
        data = json.loads(request.body)
        rut = data.get("rut", "").strip()
        
        if not rut:
            return JsonResponse({"error": "RUT requerido"}, status=400)
        
        token = make_access_token(rut)
        
        # Generar URL completa
        base_url = getattr(settings, "FRONTEND_URL", None)
        if not base_url:
            scheme = request.headers.get("X-Forwarded-Proto", "http")
            host = request.headers.get("X-Forwarded-Host", request.get_host())
            base_url = f"{scheme}://{host}"
        
        access_url = f"{base_url}/?token={token}"
        
        return JsonResponse({
            "success": True,
            "token": token,
            "url": access_url,
            "expires_in_seconds": 86400  # 24h
        })
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def validate_access_token(request):
    """
    Valida un token de acceso y devuelve el RUT.
    GET /api/validate-access/?token=xxxxx
    """
    token = request.GET.get("token", "").strip()
    
    if not token:
        return JsonResponse({"error": "Token requerido"}, status=400)
    
    try:
        payload = parse_access_token(token)
        return JsonResponse({
            "valid": True,
            "rut": payload["rut"]
        })
    
    except InvalidToken:
        return JsonResponse({
            "valid": False,
            "error": "Token inválido o expirado"
        }, status=401)
    
    except Exception as e:
        return JsonResponse({
            "valid": False,
            "error": "Error al validar token"
        }, status=500)

def convertir_a_vinetas(texto):
    """
    Convierte texto con guiones (- ...) en listas HTML con viñetas.
    Los párrafos simples se mantienen como <p>.
    """
    if not texto:
        return texto
    
    # Dividir por líneas
    lineas = texto.split('\n')
    resultado = []
    en_lista = False
    
    for linea in lineas:
        linea = linea.strip()
        
        # Verificar si es un item de lista (empieza con guion)
        if re.match(r'^-\s+', linea):
            # Si no estamos en una lista, iniciar una
            if not en_lista:
                resultado.append('<ul>')
                en_lista = True
            
            # Remover el guion y agregar como item de lista
            contenido = re.sub(r'^-\s+', '', linea)
            resultado.append(f'<li>{contenido}</li>')
        
        else:
            # Si estamos en una lista, cerrarla
            if en_lista:
                resultado.append('</ul>')
                en_lista = False
            
            # Si la línea no está vacía, agregar como párrafo
            if linea:
                resultado.append(f'<p>{linea}</p>')
    
    # Cerrar lista si quedó abierta
    if en_lista:
        resultado.append('</ul>')
    
    return '\n'.join(resultado)


def limpiar_caracteres_rtf_hex(texto):
    """
    Decodifica caracteres hexadecimales RTF y elimina combinaciones problemáticas
    (soft-hyphen, zero-width, caracteres combinantes, etc.)
    """
    if not texto or not isinstance(texto, str):
        return texto

    # Mapeo básico de caracteres latinos comunes
    hex_chars = {
        r"\'e1": "á", r"\'e9": "é", r"\'ed": "í", r"\'f3": "ó", r"\'fa": "ú",
        r"\'c1": "Á", r"\'c9": "É", r"\'cd": "Í", r"\'d3": "Ó", r"\'da": "Ú",
        r"\'f1": "ñ", r"\'d1": "Ñ", r"\'fc": "ü", r"\'dc": "Ü",
        r"\'bf": "¿", r"\'a1": "¡", r"\'b0": "°"
    }

    # Sustituir secuencias hex por sus caracteres reales
    for hex_code, char in hex_chars.items():
        texto = texto.replace(hex_code, char)

    # 🔹 Eliminar caracteres invisibles que causan cortes
    texto = re.sub(r"[\u00AD\u200B\u200C\u200D\u2060]+", "", texto)  # soft/zero width
    texto = texto.replace("\u00A0", " ")  # NBSP → espacio normal

    # 🔹 Normalizar caracteres combinantes: "ó" → "ó"
    import unicodedata
    texto = unicodedata.normalize("NFC", texto)

    return texto.strip()


def limpiar_rtf(texto):
    """
    Limpia texto RTF: remueve comandos y codificación,
    preserva saltos de línea, acentos y elimina caracteres invisibles.
    """
    if not texto or not isinstance(texto, str):
        return texto

    # Primero decodifica hexadecimales
    texto = limpiar_caracteres_rtf_hex(texto)

    # Elimina comandos RTF
    texto = re.sub(r"{\\.*?}", "", texto)
    texto = re.sub(r"\\[a-z]+\d*", "", texto)
    texto = re.sub(r"[{}]", "", texto)

    # Sustituye saltos de párrafo por salto de línea
    texto = texto.replace("\\par", "\n")

    # Limpieza adicional
    texto = re.sub(r"[\u00AD\u200B\u200C\u200D\u2060]+", "", texto)
    texto = texto.replace("\u00A0", " ")
    texto = unicodedata.normalize("NFC", texto)
    texto = re.sub(r"[ \t]{2,}", " ", texto)

    return texto.strip()



def listar_informes(request, rut=None):
    """Devuelve lista resumida de informes disponibles."""
    con = conectar_Anatomia_Patologica()
    if not con:
        return JsonResponse({"error": "Error de conexión a Patcore"}, status=500)

    cursor = con.cursor()

    if rut:
        query = """
            SELECT 
                NUMERO_BIOPSIA,
                NOMBRE,
                RUT,
                SERVICIO,
                MEDICO_TRATANTE,
                VALIDACION AS FECHA_EXAMEN
            FROM datos_informes
            WHERE RUT = ?
            ORDER BY VALIDACION DESC
        """
        cursor.execute(query, (rut,))
    else:
        query = """
            SELECT TOP 10 
                NUMERO_BIOPSIA,
                NOMBRE,
                RUT,
                SERVICIO,
                MEDICO_TRATANTE,
                VALIDACION AS FECHA_EXAMEN
            FROM datos_informes
            WHERE RUT IS NOT NULL
            ORDER BY VALIDACION DESC
        """
        cursor.execute(query)

    rows = cursor.fetchall()
    cursor.close()
    con.close()

    if not rows:
        return JsonResponse([], safe=False)

    # 🔧 Determinar la URL base correcta considerando Docker
    base_url = getattr(settings, "FRONTEND_URL", None)
    if not base_url:
        scheme = request.headers.get("X-Forwarded-Proto", "http")
        host = request.headers.get("X-Forwarded-Host", request.get_host())
        base_url = f"{scheme}://{host}"

    print(f"🔗 Base URL generada: {base_url}")

    data = []
    for i, r in enumerate(rows):
        numero_biopsia, nombre, rut_value, servicio, medico, fecha = r
        rut_value = rut_value.strip() if rut_value else ""

        # 🔐 Generar token cifrado del RUT + número de biopsia
        token = None
        if rut_value and numero_biopsia:
            try:
                token = make_pdf_token(rut_value, numero_biopsia)
            except Exception as e:
                print(f"⚠️ Error generando token para {rut_value}: {e}")
                token = None

        data.append({
            "id": i + 1,
            "numero_biopsia": numero_biopsia,
            "nombre": nombre,
            "rut": rut_value,  # el RUT real sigue visible en la lista por ahora
            "servicio": servicio,
            "medico": medico,
            "fecha": fecha.strftime("%d/%m/%Y %H:%M") if fecha else "",
            # 🔗 Nueva URL cifrada
            "url": f"{base_url}/api/pdf/v2/{token}/" if token else None
        })

    return JsonResponse(data, safe=False)

def generar_pdf(request, rut, numero_biopsia):
    """Genera el PDF institucional del informe de anatomía patológica."""
    con = conectar_Anatomia_Patologica()
    if not con:
        return HttpResponse("❌ Error de conexión a la base de datos", status=500)

    cursor = con.cursor()
    cursor.execute("""
        SELECT *
        FROM datos_informes
        WHERE RUT = ? AND NUMERO_BIOPSIA = ?
    """, (rut, numero_biopsia))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()

    if not rows:
        con.close()
        return HttpResponse("Informe no encontrado", status=404)

    informes = [dict(zip(columns, row)) for row in rows]
    informes = [{k.strip().lower(): v for k, v in fila.items()} for fila in informes]

    # === 🔧 Limpieza general de datos ===
    campos_con_vinetas = [
        "antecendentes_clinicos", "examen_macroscopico", "examen_microscopico",
        "conclusion_diagnostica", "informe_complementario"
    ]

    SOFT_BAD_CHARS_RE = re.compile(r"[\u00AD\u200B\u200C\u200D\u2060]")
    NBSP_RE = re.compile(r"\u00A0")

    for inf in informes:
        for campo, valor in list(inf.items()):
            if isinstance(valor, datetime):
                inf[campo] = valor.strftime("%d/%m/%Y %H:%M")
                continue

            if isinstance(valor, str):
                v = valor
                if r"\'" in v:
                    v = limpiar_caracteres_rtf_hex(v)
                if campo.endswith("_rtf"):
                    v = limpiar_rtf(v)
                    campo_limpio = campo.replace("_rtf", "")
                    inf[campo_limpio] = v or inf.get(campo_limpio, "")
                else:
                    if campo in campos_con_vinetas:
                        v = v.strip().replace("\r\n", "\n").replace("\r", "\n")
                    else:
                        v = v.strip().replace("\r", "").replace("\n", " ")

                v = SOFT_BAD_CHARS_RE.sub("", v)
                v = NBSP_RE.sub(" ", v)
                v = unicodedata.normalize("NFC", v)
                v = re.sub(r"[ \t]{2,}", " ", v)
                inf[campo] = v

    # === 🔹 Consultar Técnicas Realizadas ===
    cursor = con.cursor()
    cursor.execute("""
        SELECT DISTINCT Tecnica
        FROM VISTA_LAMINAS_TOTAL
        WHERE [N° Caso] = ?
    """, (numero_biopsia,))
    tecnicas = [r[0] for r in cursor.fetchall()]
    cursor.close()
    con.close()

    tecnicas_formateadas = []
    if tecnicas:
        tecnicas = [t.strip() for t in tecnicas if t and t.strip()]
        tecnicas_formateadas = [tecnicas[i:i+4] for i in range(0, len(tecnicas), 4)]

    informes[0]["tecnicas_realizadas"] = tecnicas_formateadas

    # === 🔹 Reordenar "Diagnóstico:" al inicio si es examen FISH ===
    for inf in informes:
        if "FISH" in inf.get("tipo_examen", "").upper():
            texto = inf.get("conclusion_diagnostica") or ""
            lineas = [line.strip() for line in texto.splitlines() if line.strip()]

            # Buscar la línea que contiene "Diagnóstico:"
            diagnostico_line = next((l for l in lineas if l.startswith("Diagnóstico:")), None)

            # Si existe, moverla al principio
            if diagnostico_line:
                lineas.remove(diagnostico_line)
                lineas.insert(0, diagnostico_line)

            # Volver a unir el texto
            inf["conclusion_diagnostica"] = "\n".join(lineas)

    # === 🔹 Preformatear líneas de conclusión para el template ===
    for inf in informes:
        if inf.get("conclusion_diagnostica"):
            lineas = [l.strip() for l in inf["conclusion_diagnostica"].splitlines() if l.strip()]
            pares = []
            for l in lineas:
                if ":" in l:
                    etiqueta, valor = l.split(":", 1)
                    pares.append({"label": etiqueta.strip(), "valor": valor.strip()})
                else:
                    pares.append({"label": "", "valor": l.strip()})
            inf["conclusion_diagnostica_pares"] = pares


    # === 🔹 Convertir guiones a viñetas (después de reordenar) ===
    for inf in informes:
        for campo in ["antecendentes_clinicos", "examen_macroscopico", "examen_microscopico", "conclusion_diagnostica", "informe_complementario"]:
            if campo in inf:
                inf[campo] = convertir_a_vinetas(inf[campo])

    # === 🔹 Código de barras ===
    barcode_buffer = BytesIO()
    options = {
        "module_width": 0.6,
        "module_height": 22,
        "font_size": 11,
        "quiet_zone": 2.5,
        "text_distance": 6.0,
        "write_text": True
    }
    Code128(str(numero_biopsia), writer=ImageWriter()).write(barcode_buffer, options)
    barcode_base64 = base64.b64encode(barcode_buffer.getvalue()).decode("utf-8")

    # === 🔹 Detectar si es examen FISH ===
    tipo_examen = informes[0].get("tipo_examen", "").upper()
    es_fish = "DIAGNÓSTICO FISH" in tipo_examen

    if es_fish:
        # 🔹 Agregar campos específicos si existen
        informes[0]["formulario_fish"] = limpiar_rtf(informes[0].get("formulario_fish", ""))
        informes[0]["interpretacion"] = limpiar_rtf(informes[0].get("interpretacion", ""))
        informes[0]["referencia"] = limpiar_rtf(informes[0].get("referencia", ""))

    # === 🔹 Render HTML ===
    context = {
        "informes": informes,
        "barcode": barcode_base64,
        "STATIC_ROOT": str(Path(settings.STATIC_ROOT).absolute()),
        "es_fish": es_fish,
    }

    template_name = "pdf_informe_apa.html"
    html_string = render_to_string(template_name, context)

    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=str(Path(settings.STATIC_ROOT).absolute())).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)

    response = HttpResponse(pdf_buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="informe_{numero_biopsia}.pdf"'
    response["Access-Control-Allow-Origin"] = "*"
    response["X-Frame-Options"] = "ALLOWALL"
    response["Cross-Origin-Opener-Policy"] = "same-origin"
    response["Cross-Origin-Embedder-Policy"] = "require-corp"
    return response


