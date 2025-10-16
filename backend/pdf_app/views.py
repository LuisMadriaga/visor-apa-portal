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

    host = request.get_host()
    base_url = f"http://{host}"

    data = []
    for i, r in enumerate(rows):
        numero_biopsia, nombre, rut_value, servicio, medico, fecha = r
        rut_value = rut_value.strip() if rut_value else ""
        data.append({
            "id": i + 1,
            "numero_biopsia": numero_biopsia,
            "nombre": nombre,
            "rut": rut_value,
            "servicio": servicio,
            "medico": medico,
            "fecha": fecha.strftime("%d/%m/%Y %H:%M") if fecha else "",
            "url": f"{base_url}/api/pdf/{rut_value}/{numero_biopsia}/" if rut_value and numero_biopsia else None
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
# === 🔧 Limpieza general de datos ===
    campos_con_vinetas = [
        "antecendentes_clinicos", "examen_macroscopico",
        "conclusion_diagnostica", "informe_complementario"
    ]

    SOFT_BAD_CHARS_RE = re.compile(r"[\u00AD\u200B\u200C\u200D\u2060]")
    NBSP_RE = re.compile(r"\u00A0")

    for inf in informes:
        for campo, valor in list(inf.items()):
            # 1️⃣ Fechas
            if isinstance(valor, datetime):
                inf[campo] = valor.strftime("%d/%m/%Y %H:%M")
                continue

            # 2️⃣ Cadenas de texto
            if isinstance(valor, str):
                v = valor

                # Decodifica escapes hex si existen
                if r"\'" in v:
                    v = limpiar_caracteres_rtf_hex(v)

                # Si el campo es RTF completo, límpialo con función dedicada
                if campo.endswith("_rtf"):
                    v = limpiar_rtf(v)
                    campo_limpio = campo.replace("_rtf", "")
                    inf[campo_limpio] = v or inf.get(campo_limpio, "")
                else:
                    # Campos narrativos → preservar saltos de línea
                    if campo in campos_con_vinetas:
                        v = v.strip().replace("\r\n", "\n").replace("\r", "\n")
                    else:
                        v = v.strip().replace("\r", "").replace("\n", " ")

                # Limpieza de artefactos invisibles
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

    # === 🔹 Convertir guiones a viñetas ===
    for inf in informes:
        if 'antecendentes_clinicos' in inf:
            inf['antecendentes_clinicos'] = convertir_a_vinetas(inf['antecendentes_clinicos'])
        if 'examen_macroscopico' in inf:
            inf['examen_macroscopico'] = convertir_a_vinetas(inf['examen_macroscopico'])
        if 'conclusion_diagnostica' in inf:
            inf['conclusion_diagnostica'] = convertir_a_vinetas(inf['conclusion_diagnostica'])
        if 'informe_complementario' in inf:
            inf['informe_complementario'] = convertir_a_vinetas(inf['informe_complementario'])

    # === 🔹 Código de barras ===
    barcode_buffer = BytesIO()
    options = {
        "module_width": 0.6,
        "module_height": 22,
        "font_size": 11,
        "quiet_zone": 2.5,
        "text_distance": 6.0,
        "write_text": True,
    }
    Code128(str(numero_biopsia), writer=ImageWriter()).write(barcode_buffer, options)
    barcode_base64 = base64.b64encode(barcode_buffer.getvalue()).decode("utf-8")

    # === 🔹 Render HTML ===
    html_string = render_to_string(
        "pdf_informe_apa.html",
        {"informes": informes, "barcode": barcode_base64},
    )

    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)

    response = HttpResponse(pdf_buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="informe_{numero_biopsia}.pdf"'
    response["Access-Control-Allow-Origin"] = "*"
    response["X-Frame-Options"] = "ALLOWALL"
    response["Cross-Origin-Opener-Policy"] = "same-origin"
    response["Cross-Origin-Embedder-Policy"] = "require-corp"
    return response