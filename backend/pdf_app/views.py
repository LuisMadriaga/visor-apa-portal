from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
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
import os
from django.conf import settings
from pathlib import Path
from .crypto_utils import make_pdf_token, parse_pdf_token, make_access_token, parse_access_token  
from django.views.decorators.csrf import csrf_exempt
from cryptography.fernet import InvalidToken
from django.views.decorators.http import require_http_methods
from functools import wraps

from .models import LogAcceso, LogVisualizacion

def get_client_ip(request):
    """
    Obtiene la IP real del cliente considerando cadenas de proxies.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        # Toma la primera IP (cliente real)
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip

def generar_pdf_token(request, token):
    try:
        payload = parse_pdf_token(token)
        rut = payload["rut"]
        numero_biopsia = payload["num"]
    except Exception:
        return HttpResponseBadRequest("Enlace inválido o expirado.")

    return generar_pdf(request, rut, numero_biopsia)

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
@require_api_key  
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
        rut = payload["rut"]

        # 🧩 REGISTRAR ACCESO EXITOSO
        LogAcceso.objects.create(
            rut_paciente=rut,
            token_hash=token[:80],  # Guardamos parte del hash
            ip=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            estado="OK"
        )

        return JsonResponse({
            "valid": True,
            "rut": rut
        })
    
    except InvalidToken:
        # 🧩 REGISTRAR TOKEN INVÁLIDO
        LogAcceso.objects.create(
            token_hash=token[:80],
            ip=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            estado="FAIL"
        )
        return JsonResponse({
            "valid": False,
            "error": "Token inválido o expirado"
        }, status=401)
    
    except Exception as e:
        return JsonResponse({
            "valid": False,
            "error": "Error al validar token"
        }, status=500)

def debug_unicode(texto, campo=None):
    """Imprime caracteres Unicode invisibles o sospechosos."""
    for ch in texto:
        if ord(ch) < 32 or ord(ch) > 126:  # fuera de ASCII normal
            print(f"🧪 [{campo}] Caracter raro: '{ch}' (Unicode: {hex(ord(ch))})")


# === 🔧 Limpieza general de datos ===
campos_con_vinetas = [
    "antecendentes_clinicos", "examen_macroscopico", "examen_microscopico",
    "conclusion_diagnostica", "informe_complementario"
]

campos_normalizados = {
    "anecedentes_clinicos": "antecedentes_clinicos_rtf",
    "examen_macroscopico": "examen_macroscopico_rtf",
    "examen_microscopico": "examen_microscopico_rtf",
    "conclusion_diagnostica": "conclusion_diagnostica_rtf",
    "informe_complementario": "informe_complementario_rtf",
}


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


def limpiar_comandos_width(texto):
    """
    Limpia comandos Width que aparecen en el texto.
    Estos comandos son separadores mal interpretados del formato RTF.
    """
    if not texto or not isinstance(texto, str):
        return texto
    
    # 🔸 Convertir secuencias de Width como separadores en saltos de línea
    # Patrón: 2 o más comandos Width consecutivos = salto de línea
    texto = re.sub(r'(?:Width\d+){2,}', '\n', texto)
    
    # 🔸 Limpiar cualquier Width residual individual (basura)
    texto = re.sub(r'Width\d+', '', texto)
    
    return texto


def limpiar_caracteres_invisibles_mejorado(texto):
    """
    🔧 SOLUCIÓN MEJORADA: Elimina TODOS los caracteres invisibles problemáticos
    que causan cortes de palabras en PDFs.
    """
    if not texto or not isinstance(texto, str):
        return texto
    
    # 1️⃣ Eliminar soft-hyphen y caracteres de ancho cero
    texto = re.sub(r'[\u00AD\u200B\u200C\u200D\u2060\uFEFF]', '', texto)
    
    # 2️⃣ Reemplazar NBSP por espacio normal
    texto = texto.replace('\u00A0', ' ')
    
    # 3️⃣ Eliminar caracteres de control (excepto saltos de línea y tabs)
    texto = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', texto)
    
    # 4️⃣ Normalizar Unicode a forma canónica compuesta (NFC)
    # Esto junta tildes separadas con sus letras base
    texto = unicodedata.normalize('NFC', texto)
    
    # 5️⃣ Eliminar espacios múltiples
    texto = re.sub(r'[ \t]{2,}', ' ', texto)
    
    # 6️⃣ Limpiar espacios alrededor de saltos de línea
    texto = re.sub(r' *\n *', '\n', texto)
    
    return texto.strip()


def limpiar_caracteres_rtf_hex(texto):
    """
    Limpia texto RTF: elimina soft-hyphen, zero-width, NBSP,
    corrige tildes combinadas y normaliza para evitar cortes.
    """
    if not texto or not isinstance(texto, str):
        return texto

    # 🔹 Sustituye caracteres hex comunes por acentos reales
    hex_chars = {
        r"\'e1": "á", r"\'e9": "é", r"\'ed": "í", r"\'f3": "ó", r"\'fa": "ú",
        r"\'c1": "Á", r"\'c9": "É", r"\'cd": "Í", r"\'d3": "Ó", r"\'da": "Ú",
        r"\'f1": "ñ", r"\'d1": "Ñ", r"\'fc": "ü", r"\'dc": "Ü",
        r"\'b0": "°", r"\'ba": "º"
    }
    for hex_code, char in hex_chars.items():
        texto = texto.replace(hex_code, char)

    # 🔹 Aplica la limpieza mejorada
    return limpiar_caracteres_invisibles_mejorado(texto)


def limpiar_caracteres_invisibles(texto):
    """
    🔧 VERSIÓN ORIGINAL mantenida por compatibilidad
    """
    return limpiar_caracteres_invisibles_mejorado(texto)


def limpiar_rtf(texto):
    """
    Limpia formato RTF a texto plano.
    """
    if not texto or not isinstance(texto, str):
        return texto

    # 🔸 CRÍTICO: Convertir secuencias Width en saltos de línea
    # Primero, identificar el patrón repetitivo Width\d+Width\d+Width\d+Width\d+ como separador
    # Patrón: uno o más grupos de Width seguidos de números
    texto = re.sub(r'(?:Width\d+){2,}', '\n', texto)
    
    # 🔸 Limpiar cualquier Width residual individual
    texto = re.sub(r'Width\d+', '', texto)
    
    # 🔸 Eliminar bloques de grupos completos
    texto = re.sub(r"\{[^}]*\}", "", texto)
    
    # 🔸 Eliminar comandos RTF comunes
    texto = re.sub(r"\\[a-z]+\d*\s?", "", texto)
    
    # 🔸 Eliminar secuencias RTF específicas
    texto = re.sub(r"\\par\b", "\n", texto)
    texto = re.sub(r"\\line\b", "\n", texto)
    texto = re.sub(r"\\tab\b", "\t", texto)
    
    # 🔸 Limpiar caracteres RTF especiales
    texto = re.sub(r"\\[\\'~\-_*]", "", texto)
    
    # 🔸 Eliminar llaves residuales
    texto = texto.replace("{", "").replace("}", "")
    
    # 🔸 Aplicar limpieza de caracteres invisibles MEJORADA
    texto = limpiar_caracteres_invisibles_mejorado(texto)
    
    # 🔸 Normalizar saltos de línea (eliminar más de 2 saltos consecutivos)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    
    # 🔸 Limpiar espacios al inicio y final de cada línea
    lineas = [linea.strip() for linea in texto.split('\n')]
    texto = '\n'.join(linea for linea in lineas if linea)
    
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
            SELECT 
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
            "rut": rut_value,  
            "servicio": servicio,
            "medico": medico,
            "fecha": fecha.strftime("%d/%m/%Y %H:%M") if fecha else "",
            # 🔗 Nueva URL cifrada
            "url": f"/visor_apa_portal_2/api/pdf/v2/{token}/" if token else None
        })

    return JsonResponse(data, safe=False)


def obtener_informes(request, rut):
    """Obtiene los informes de un paciente por RUT"""
    con = conectar_Anatomia_Patologica()
    if not con:
        return JsonResponse({"error": "Error de conexión a la base de datos"}, status=500)

    cursor = con.cursor()
    cursor.execute("""
        SELECT 
            NUMERO_BIOPSIA,
            CONVERT(VARCHAR, VALIDACION, 103) AS FECHA_VALIDACION,
            TIPO_EXAMEN
        FROM datos_informes
        WHERE RUT = ?
        ORDER BY VALIDACION DESC
    """, (rut,))
    
    rows = cursor.fetchall()
    cursor.close()
    con.close()

    if not rows:
        return JsonResponse([], safe=False)

    data = []
    for row in rows:
        numero_biopsia, fecha_validacion, tipo_examen = row
        token = make_pdf_token(rut, numero_biopsia)
        
        base_url = getattr(settings, "FRONTEND_URL", None)
        if not base_url:
            scheme = request.headers.get("X-Forwarded-Proto", "http")
            host = request.headers.get("X-Forwarded-Host", request.get_host())
            base_url = f"{scheme}://{host}"
        
        pdf_url = f"{base_url}/api/generar-pdf-token/{token}"
        
        data.append({
            "numero_biopsia": numero_biopsia,
            "fecha_validacion": fecha_validacion,
            "tipo_examen": tipo_examen,
            "pdf_url": pdf_url
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

    # === 🔧 Limpieza MEJORADA de datos ===
    campos_con_vinetas = [
        "antecendentes_clinicos", "examen_macroscopico", "examen_microscopico",
        "conclusion_diagnostica", "informe_complementario"
    ]

    for inf in informes:

        # 🧠 PRIORIZAR CAMPOS NORMALIZADOS si existen
        for campo_norm, campo_rtf in {
            "antecendentes_clinicos": "antecendentes_clinicos_rtf",
            "examen_macroscopico": "examen_macroscopico_rtf",
            "examen_microscopico": "examen_microscopico_rtf",
            "conclusion_diagnostica": "conclusion_diagnostica_rtf",
            "informe_complementario": "informe_complementario_rtf",
        }.items():
            
            normalizado = inf.get(campo_norm, "")
            rtf = inf.get(campo_rtf, "")

            # ⚠️ Solo usamos el RTF si el normalizado está vacío
            if (not normalizado or normalizado.strip() == "") and rtf:
                inf[campo_norm] = limpiar_rtf(rtf)

        # 🔄 Procesar todos los campos
        for campo, valor in list(inf.items()):
            if isinstance(valor, datetime):
                inf[campo] = valor.strftime("%d/%m/%Y %H:%M")
                continue

            if isinstance(valor, str):
                v = valor

                # 1️⃣ Limpiar comandos Width (CRÍTICO para evitar basura RTF)
                v = limpiar_comandos_width(v)

                # 2️⃣ Limpiar caracteres RTF hex si existen
                if r"\'" in v:
                    v = limpiar_caracteres_rtf_hex(v)

                # 3️⃣ Procesar campos RTF
                if campo.endswith("_rtf"):
                    v = limpiar_rtf(v)
                    campo_limpio = campo.replace("_rtf", "")
                    inf[campo_limpio] = v or inf.get(campo_limpio, "")
                else:
                    # 4️⃣ Normalizar saltos de línea según tipo de campo
                    if campo in campos_con_vinetas:
                        v = v.strip().replace("\r\n", "\n").replace("\r", "\n")
                    else:
                        v = v.strip().replace("\r", "").replace("\n", " ")

                # 5️⃣ APLICAR LIMPIEZA MEJORADA (elimina todos los caracteres invisibles)
                v = limpiar_caracteres_invisibles_mejorado(v)
                
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
            diagnostico_line = next((l for l in lineas if l.startswith("Diagnóstico:")), None)
            if diagnostico_line:
                lineas.remove(diagnostico_line)
                lineas.insert(0, diagnostico_line)
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

    # === 🔹 Convertir guiones a viñetas ===
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
        informes[0]["formulario_fish"] = limpiar_rtf(informes[0].get("formulario_fish", ""))
        informes[0]["interpretacion"] = limpiar_rtf(informes[0].get("interpretacion", ""))
        informes[0]["referencia"] = limpiar_rtf(informes[0].get("referencia", ""))

    # === 🔹 CONSTRUIR RUTAS ABSOLUTAS PARA IMÁGENES ===
    # Directorio base de archivos estáticos
    static_dir = os.path.join(settings.BASE_DIR, "backend", "static")
    
    # Rutas absolutas para WeasyPrint
    logo_path = os.path.join(static_dir, "img", "Logotipo_secundario_sin_slogan.png")
    firmas_dir = os.path.join(static_dir, "firmas")
    
    # Verificar si el logo existe
    if not os.path.exists(logo_path):
        print(f"⚠️ Logo no encontrado en: {logo_path}")
    
    # === 🔹 Context para el template ===
    context = {
        "informes": informes,
        "barcode": barcode_base64,
        "es_fish": es_fish,
        "logo_path": f"file://{logo_path}",  # Ruta absoluta para el logo
        "firmas_dir": f"file://{firmas_dir}",  # Ruta absoluta para firmas
    }

    template_name = "pdf_informe_apa.html"
    html_string = render_to_string(template_name, context)
    pdf_buffer = BytesIO()

    # === 🔹 Generar PDF con base_url correcto ===
    HTML(
        string=html_string,
        base_url=f"file://{static_dir}/"  # Base para resolver rutas relativas
    ).write_pdf(pdf_buffer)

    pdf_buffer.seek(0)


    # === 🔹 Registrar visualización PDF ===
    try:
        token_hash = request.GET.get("token") or ""
        ip = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "Desconocido")[:255]


        nuevo_log = LogVisualizacion.objects.create(
            rut_paciente=str(rut),
            documento_id=str(numero_biopsia),
            ip=ip,
            user_agent=user_agent,
            token_hash=token_hash[:80],
            accion="VISUALIZACION_PDF"
        )

    except Exception as e:
        print(f"❌ Error registrando visualización PDF: {e}")


    # === 🔹 Respuesta HTTP ===
    response = HttpResponse(pdf_buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="informe_{numero_biopsia}.pdf"'
    response["Access-Control-Allow-Origin"] = "*"
    response["X-Frame-Options"] = "ALLOWALL"
    response["Cross-Origin-Opener-Policy"] = "same-origin"
    response["Cross-Origin-Embedder-Policy"] = "require-corp"

    return response