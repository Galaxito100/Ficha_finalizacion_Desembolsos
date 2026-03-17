import re
import os
import tempfile
import streamlit as st
from pathlib import Path

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="CAF – Extractor FR",
    layout="wide",
    page_icon="🏦"
)

# ── Estilo CAF ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&family=Open+Sans:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Open Sans', sans-serif;
    background-color: #f4f6f9;
}
.caf-header {
    background: linear-gradient(135deg, #004A8F 0%, #006BB6 100%);
    padding: 28px 36px;
    border-radius: 12px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 20px rgba(0,74,143,0.25);
}
.caf-header-title {
    color: white;
    font-family: 'Montserrat', sans-serif;
    font-size: 26px;
    font-weight: 800;
    letter-spacing: 0.5px;
    margin: 0;
}
.caf-header-sub {
    color: rgba(255,255,255,0.80);
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 4px;
}
.section-header {
    background: linear-gradient(90deg, #004A8F 0%, #006BB6 100%);
    color: white;
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    padding: 10px 20px;
    border-radius: 6px;
    margin: 24px 0 0 0;
}
.caf-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 12px;
    margin-bottom: 8px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.caf-table tr:nth-child(even) { background-color: #EEF3F9; }
.caf-table tr:nth-child(odd)  { background-color: #ffffff; }
.caf-table td {
    padding: 11px 18px;
    font-size: 13.5px;
    border-bottom: 1px solid #dce6f0;
    vertical-align: top;
}
.caf-table td:first-child {
    background-color: #004A8F;
    color: white;
    font-family: 'Montserrat', sans-serif;
    font-weight: 600;
    font-size: 12.5px;
    width: 280px;
    letter-spacing: 0.3px;
}
.caf-table td:last-child { color: #1a2e45; }
div.stButton > button {
    background: linear-gradient(135deg, #004A8F, #006BB6);
    color: white;
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.8px;
    border: none;
    padding: 12px 36px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 4px 14px rgba(0,74,143,0.3);
    width: 100%;
}
div.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(0,74,143,0.4);
}
.caf-footer {
    text-align: center;
    color: #8fa3bd;
    font-size: 11.5px;
    margin-top: 40px;
    padding-top: 16px;
    border-top: 1px solid #dce6f0;
    letter-spacing: 0.5px;
}
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="caf-header">
    <div>
        <div class="caf-header-sub">Gerencia Corporativa de Riesgos · Dirección de Riesgo Soberano</div>
        <div class="caf-header-title">Ficha de Finalización de Desembolsos</div>
    </div>
    <div style="color:white; font-family:Montserrat; font-size:32px; font-weight:900; letter-spacing:-1px;">CAF</div>
</div>
""", unsafe_allow_html=True)

# ── Upload + Botón ─────────────────────────────────────────────────────────────
col_up, col_btn = st.columns([3, 1])
with col_up:
    archivo = st.file_uploader("Sube tu documento (.pdf o .docx)", type=["pdf", "docx"])
with col_btn:
    st.write("")
    st.write("")
    procesar = st.button("⚙️ Procesar")

archivo_excel = st.file_uploader(
    "Sube la base de EED (.xlsx) para verificación de calidad",
    type=["xlsx"],
    help="Debe contener la hoja 'Consolidado (2019 - 2025)' con columna 'Codigo de documento'"
)

# ── Funciones de extracción ────────────────────────────────────────────────────
def extraer_texto_pdf(ruta):
    import pdfplumber
    texto_completo = []
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            for tabla in pagina.extract_tables():
                for fila in tabla:
                    texto_completo.append(" | ".join([c or "" for c in fila]))
            texto_plano = pagina.extract_text()
            if texto_plano:
                texto_completo.append(texto_plano)
    return "\n".join(texto_completo)

def extraer_texto_docx(ruta):
    from docx import Document
    doc = Document(ruta)
    lineas = []
    for parrafo in doc.paragraphs:
        if parrafo.text.strip():
            lineas.append(parrafo.text.strip())
    for tabla in doc.tables:
        for fila in tabla.rows:
            celdas = [c.text.strip() for c in fila.cells]
            celdas = list(dict.fromkeys(celdas))  # elimina duplicados de celdas combinadas
            lineas.append(" | ".join(celdas))
    return "\n".join(lineas)

SEP = r"[\s|]+"

def buscar_campo(texto, patron, grupo=1):
    match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
    if not match:
        return "No encontrado"
    valor = match.group(grupo).strip().strip("|").strip()
    return valor if valor else "No encontrado"

def normalizar(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn").strip()

def celda_a_html(celda):
    """Convierte una celda docx a HTML preservando hipervínculos.
    Tipo 1: w:hyperlink r:id  → links normales
    Tipo 2: w:fldChar + w:instrText → links SharePoint/campo
    """
    from docx.oxml.ns import qn
    import re as _re

    partes = []
    for parrafo in celda.paragraphs:
        texto_parrafo = ""
        # Aplanar todos los elementos del párrafo en una lista
        elems = list(parrafo._p)
        skip_until_end = False
        url_campo = ""
        texto_campo = ""
        in_separate = False

        for elem in elems:
            tag = elem.tag.split("}")[-1]

            if tag == "hyperlink":
                # Tipo 1: w:hyperlink con r:id
                rId = elem.get(qn("r:id"))
                url = ""
                if rId and rId in celda.part.rels:
                    url = celda.part.rels[rId].target_ref
                texto_link = "".join(
                    t.text for r in elem.findall(qn("w:r"))
                    for t in r.findall(qn("w:t")) if t.text
                )
                if url and texto_link:
                    texto_parrafo += f'<a href="{url}" target="_blank" style="color:#006BB6">{texto_link}</a>'
                else:
                    texto_parrafo += texto_link

            elif tag == "r":
                # Puede contener fldChar, instrText, o texto normal
                fld = elem.find(qn("w:fldChar"))
                instr = elem.find(qn("w:instrText"))
                t_elem = elem.find(qn("w:t"))

                if fld is not None:
                    ft = fld.get(qn("w:fldCharType"), "")
                    if ft == "begin":
                        url_campo = ""
                        texto_campo = ""
                        in_separate = False
                        skip_until_end = True
                    elif ft == "separate":
                        in_separate = True
                    elif ft == "end":
                        # Emitir el link acumulado
                        if url_campo and texto_campo:
                            texto_parrafo += f'<a href="{url_campo}" target="_blank" style="color:#006BB6">{texto_campo}</a>'
                        elif texto_campo:
                            texto_parrafo += texto_campo
                        skip_until_end = False
                        in_separate = False

                elif instr is not None and instr.text:
                    # Extraer URL de HYPERLINK "url"
                    m = _re.search(r'HYPERLINK\s+"([^"]+)"', instr.text)
                    if m:
                        url_campo = m.group(1)

                elif t_elem is not None and t_elem.text:
                    if in_separate:
                        texto_campo += t_elem.text
                    elif not skip_until_end:
                        texto_parrafo += t_elem.text

        if texto_parrafo.strip():
            partes.append(texto_parrafo)
    return "<br>".join(partes) if partes else ""

def extraer_presentacion_informes(ruta, extension):
    """
    Busca la tabla que contiene tanto "Cumplimiento contractual" como
    "Presentación de informes". Dentro de esa tabla, empieza a leer
    solo desde la fila de "Cumplimiento contractual" hacia abajo.
    Etiquetas aceptadas (match parcial normalizado sin tildes):
      auditor / auditoria financiera → Última auditoría
      informe final del prestamo / informe final / final → Final
      condicion / pendiente / pendientes → Pendientes
    """
    resultados = {"Última auditoría": "No encontrado", "Final": "No encontrado", "Pendientes": "No encontrado"}
    mapa = [
        ("ultima auditoria",           "Última auditoría"),
        ("auditoria financiera",       "Última auditoría"),
        ("auditor",                    "Última auditoría"),
        ("informe final del prestamo", "Final"),
        ("informe final",              "Final"),
        ("final",                      "Final"),
        ("condiciones pendientes",     "Pendientes"),
        ("condicion",                  "Pendientes"),
        ("pendientes",                 "Pendientes"),
        ("pendiente",                  "Pendientes"),
    ]

    try:
        if extension == ".docx":
            from docx import Document
            from docx.table import Table

            doc = Document(ruta)
            for elem in doc.element.body:
                if elem.tag.split("}")[-1] != "tbl":
                    continue
                tabla = Table(elem, doc)
                texto_tabla = normalizar(" ".join(c.text for fila in tabla.rows for c in fila.cells))

                # Solo tablas que contengan AMBAS secciones
                if "presentacion de informes" not in texto_tabla:
                    continue

                # Encontrar la fila donde está "Cumplimiento contractual"
                # (o "Presentación de informes" si no hay encabezado de sección)
                fila_inicio = 0
                for j, fila in enumerate(tabla.rows):
                    texto_fila = normalizar(" ".join(c.text for c in fila.cells))
                    if "cumplimiento contractual" in texto_fila:
                        fila_inicio = j
                        break

                # Leer filas desde fila_inicio
                for j, fila in enumerate(tabla.rows):
                    if j < fila_inicio:
                        continue
                    raw = [c.text.strip() for c in fila.cells]
                    seen = set(); celdas = []
                    for c in raw:
                        if c and c not in seen:
                            seen.add(c); celdas.append(c)
                    if len(celdas) < 2:
                        continue
                    etiqueta_norm = normalizar(celdas[-2])
                    valor_texto = celdas[-1].strip()
                    # Ignorar placeholders vacíos o guiones
                    if not valor_texto or valor_texto in ("-", "—"):
                        continue
                    # Buscar la celda real de contenido — última celda única (no repetida)
                    seen_ids = set()
                    celdas_unicas = []
                    for c in fila.cells:
                        cid = id(c._tc)
                        if cid not in seen_ids:
                            seen_ids.add(cid)
                            celdas_unicas.append(c)
                    # La celda de valor es la última única
                    celda_contenido = celdas_unicas[-1] if len(celdas_unicas) >= 2 else None
                    valor_html = celda_a_html(celda_contenido) if celda_contenido else ""
                    # Usar HTML si tiene contenido; si no, usar texto plano
                    valor = valor_html.strip() or valor_texto
                    for clave, nombre in mapa:
                        if clave in etiqueta_norm and resultados[nombre] == "No encontrado":
                            resultados[nombre] = valor
                            break

        else:
            import pdfplumber
            with pdfplumber.open(ruta) as pdf:
                texto_completo = "\n".join(p.extract_text() or "" for p in pdf.pages)
            m_sec = re.search(r"cumplimiento\s+contractual", texto_completo, re.IGNORECASE)
            texto = texto_completo[m_sec.start():] if m_sec else texto_completo
            for clave, nombre in mapa:
                m = re.search(rf"{re.escape(clave)}[^\n]*\n([^\n]+)", texto, re.IGNORECASE)
                if m and resultados[nombre] == "No encontrado":
                    resultados[nombre] = m.group(1).strip()

    except Exception as e:
        for k in resultados:
            resultados[k] = f"Error: {e}"
    return resultados
def extraer_objetivo_general(ruta, extension):
    """
    Busca la fila 'Objetivo general y específicos' y extrae
    el párrafo que sigue a 'Objetivo General:' dentro de esa celda.
    """
    try:
        if extension == ".docx":
            from docx import Document
            doc = Document(ruta)
            for tabla in doc.tables:
                for fila in tabla.rows:
                    celdas_raw = [c.text.strip() for c in fila.cells]
                    celdas = list(dict.fromkeys(celdas_raw))
                    if len(celdas) < 2:
                        continue
                    if "objetivo general" not in celdas[0].lower():
                        continue
                    # Texto completo de la celda valor (última celda)
                    celda_valor = fila.cells[-1].text
                    # Buscar el párrafo después de "Objetivo General:"
                    m = re.search(
                        r"Objetivo General[:\s]*\n+([\s\S]+?)(?:\n\s*\n|\nObjetivos Espec|$)",
                        celda_valor, re.IGNORECASE
                    )
                    if m:
                        return " ".join(m.group(1).split())  # limpiar saltos internos
                    # Si no hay etiqueta, devolver todo el contenido
                    if celda_valor.strip() and celda_valor.strip() not in ("-", "—"):
                        return celda_valor.strip()
        else:
            import pdfplumber
            with pdfplumber.open(ruta) as pdf:
                texto = "\n".join(p.extract_text() or "" for p in pdf.pages)
            m = re.search(r"Objetivo General[:\s]*\n+([\s\S]+?)(?:\n\s*\n|Objetivos Espec)", texto, re.IGNORECASE)
            if m:
                return " ".join(m.group(1).split())
    except Exception:
        pass
    return "No encontrado"

def celda_dispensas_a_html(celda):
    """Convierte la celda de Dispensas y enmiendas a HTML,
    preservando párrafos, tabla interna y lista numerada."""
    from docx.oxml.ns import qn
    html = ""

    # Recorrer elementos en orden (párrafos y tablas internas)
    for elem in celda._tc:
        tag = elem.tag.split("}")[-1]

        if tag == "p":
            # Párrafo — extraer texto
            texto = "".join(
                n.text for n in elem.iter(qn("w:t")) if n.text
            ).strip()
            if texto:
                html += f'<p style="margin:6px 0">{texto}</p>'

        elif tag == "tbl":
            # Tabla interna — renderizar como tabla HTML
            from docx.table import Table
            from docx.api import Document as _Doc
            tabla_interna = Table(elem, celda._tc)
            html += '<table style="border-collapse:collapse;width:100%;margin:10px 0">'
            for i, fila in enumerate(tabla_interna.rows):
                celdas = [c.text.strip() for c in fila.cells]
                celdas = list(dict.fromkeys(celdas))
                bg = "#EEF3F9" if i % 2 == 0 else "#ffffff"
                es_header = i == 0
                html += "<tr>"
                for c in celdas:
                    if es_header:
                        html += f'<th style="background:#004A8F;color:white;padding:6px 10px;font-size:12px;text-align:left">{c}</th>'
                    else:
                        html += f'<td style="background:{bg};padding:6px 10px;font-size:12px;border-bottom:1px solid #dce6f0">{c}</td>'
                html += "</tr>"
            html += "</table>"

    return html if html.strip() else None

def extraer_dispensas(ruta, extension):
    """Extrae el contenido completo de 'Dispensas y enmiendas' como HTML."""
    try:
        if extension == ".docx":
            from docx import Document
            doc = Document(ruta)
            for tabla in doc.tables:
                for fila in tabla.rows:
                    seen = set(); unicas = []
                    for c in fila.cells:
                        cid = id(c._tc)
                        if cid not in seen:
                            seen.add(cid); unicas.append(c)
                    if len(unicas) < 2:
                        continue
                    etiqueta = unicas[0].text.strip().lower()
                    if "dispensa" not in etiqueta and "enmienda" not in etiqueta:
                        continue
                    celda = unicas[-1]
                    valor_texto = celda.text.strip()
                    if not valor_texto or valor_texto in ("-", "—"):
                        continue
                    html = celda_dispensas_a_html(celda)
                    return html if html else valor_texto
        else:
            import pdfplumber
            with pdfplumber.open(ruta) as pdf:
                texto = "\n".join(p.extract_text() or "" for p in pdf.pages)
            m = re.search(r"Dispensas y enmiendas[\s|]+([\s\S]+?)(?:\n[A-Z][^\n]{0,40}\n)", texto, re.IGNORECASE)
            if m:
                parrafos = [p.strip() for p in m.group(1).splitlines() if p.strip()]
                return "<br>".join(parrafos)
    except Exception:
        pass
    return "No encontrado"

def tabla_html(filas):
    rows = ""
    for label, valor in filas:
        rows += f"<tr><td>{label}</td><td>{valor or '—'}</td></tr>"
    return f'<table class="caf-table">{rows}</table>'

# ── Limpiar resultados si no hay archivo ─────────────────────────────────────
if archivo is None and "resultados" in st.session_state:
    for k in ["resultados","informes","objetivo","dispensas","vista"]:
        st.session_state.pop(k, None)

# ── Limpiar si no hay archivo ─────────────────────────────────────────────────
if archivo is None:
    for k in ["resultados", "informes", "objetivo", "dispensas", "vista"]:
        st.session_state.pop(k, None)

# ── Procesamiento ──────────────────────────────────────────────────────────────
if procesar:
    if archivo is None:
        st.warning("⚠️ Por favor sube un archivo antes de procesar.")
    else:
        extension = Path(archivo.name).suffix.lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
            tmp.write(archivo.read())
            ruta_tmp = tmp.name

        with st.spinner("Procesando documento..."):
            texto     = extraer_texto_pdf(ruta_tmp) if extension == ".pdf" else extraer_texto_docx(ruta_tmp)
            informes  = extraer_presentacion_informes(ruta_tmp, extension)
            objetivo  = extraer_objetivo_general(ruta_tmp, extension)
            dispensas = extraer_dispensas(ruta_tmp, extension)

        os.unlink(ruta_tmp)

        # Guardar todo en session_state para persistir entre reruns
        st.session_state["resultados"] = {
            "N° de Operación (CFA)":            buscar_campo(texto, r"CFA\s*[–\-]\s*([\d]+(?:/[\d]+)*)"),
            "Nombre de la Operación":           buscar_campo(texto, r"Nombre de la operaci[oó]n"                  + SEP + r"([^|\n]+)"),
            "Prestatario":                       buscar_campo(texto, r"Prestatario"                                + SEP + r"([^|\n]+)"),
            "País":                              buscar_campo(texto, r"Pa[ií]s"                                    + SEP + r"([^|\n]+)"),
            "Garante":                           buscar_campo(texto, r"Garante"                                    + SEP + r"([^|\n]+)"),
            "Monto préstamo CAF (Aprobado)":     buscar_campo(texto, r"Monto del pr[eé]stamo[\s\S]*?aprobado CAF" + SEP + r"((?:Contractual[^|\n]+|(?:US\$|USD)\s*[\d.,]+[^|\n]*))"),
            "Monto préstamo CAF (Desembolsado)": (lambda: (
                lambda c1, c2: c1 if c1 != "No encontrado" else c2
            )(
                buscar_campo(texto, r"Desembolsado:\s*((?:US\$|USD)\s*[\d.,]+[^\n]*)"),
                buscar_campo(texto, r"Monto del pr[eé]stamo[^\n]*aprobado CAF[^\n]*\nMonto del pr[eé]stamo[^\n]*aprobado CAF[\s|]+([^\n]+)")
            ))(),
        }
        st.session_state["informes"]  = informes
        st.session_state["objetivo"]  = objetivo
        st.session_state["dispensas"] = dispensas
        st.session_state["vista"]     = "informe"

# ── Renderizado (siempre visible si hay datos en session_state) ────────────────
if "resultados" in st.session_state:
    resultados = st.session_state["resultados"]
    informes   = st.session_state["informes"]
    objetivo   = st.session_state["objetivo"]
    dispensas  = st.session_state["dispensas"]

    # Botones de vista
    st.write("")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        if st.button("📋  Informe de Apoyo", use_container_width=True):
            st.session_state["vista"] = "informe"
    with col_v2:
        if st.button("🔍  Verificación de Calidad de la Ficha", use_container_width=True):
            st.session_state["vista"] = "calidad"

    vista = st.session_state.get("vista", "informe")

    if vista == "informe":
        st.markdown('<div class="section-header">📋 &nbsp;Informe de la Operación</div>', unsafe_allow_html=True)
        st.markdown(tabla_html(list(resultados.items())), unsafe_allow_html=True)

        st.markdown('<div class="section-header">📄 &nbsp;Presentación de Informes</div>', unsafe_allow_html=True)
        st.markdown(tabla_html([
            ("Última auditoría", informes["Última auditoría"]),
            ("Final",            informes["Final"]),
            ("Pendientes",       informes["Pendientes"]),
        ]), unsafe_allow_html=True)

        st.markdown('<div class="section-header">📝 &nbsp;Descripción de la Operación</div>', unsafe_allow_html=True)
        st.markdown(tabla_html([
            ("Objetivo General", objetivo),
        ]), unsafe_allow_html=True)

    elif vista == "calidad":
        # Resaltar siglas de documentos (EED, CCI, GOI, STCI) + guion o espacio + número
        dispensas_html = re.sub(
            r'((EED|CCI|GOI|STCI)[-\s][\d]+)',
            r'<span style="color:#006BB6;font-weight:700">\1</span>',
            dispensas
        )
        st.markdown('<div class="section-header">⚖️ &nbsp;Dispensas y Enmiendas</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:white;padding:18px 24px;border-radius:8px;margin-top:12px;box-shadow:0 2px 12px rgba(0,0,0,0.08);font-size:13.5px;color:#1a2e45;line-height:1.8;">{dispensas_html}</div>', unsafe_allow_html=True)

        # ── Comparación con base Excel ─────────────────────────────────────────
        if archivo_excel is not None:
            st.markdown('<div class="section-header">📊 &nbsp;Verificación contra Base EED</div>', unsafe_allow_html=True)
            try:
                import pandas as pd

                df = pd.read_excel(archivo_excel, sheet_name="Consolidado (2019 - 2025)")

                # Buscar columnas necesarias (tolerante a variaciones)
                col_codigo = next(
                    (c for c in df.columns if "codigo" in c.lower() and "doc" in c.lower()), None
                )
                col_operacion = next(
                    (c for c in df.columns if "operaci" in c.lower() and "n" in c.lower()), None
                )
                if col_codigo is None:
                    st.warning("⚠️ No se encontró la columna 'Codigo de documento' en el Excel.")
                elif col_operacion is None:
                    st.warning("⚠️ No se encontró la columna 'Número de la operación' en el Excel.")
                else:
                    # Obtener CFA de la ficha — separar números individuales
                    cfa_raw = resultados.get("N° de Operación (CFA)", "")
                    numeros_cfa = [n.strip() for n in cfa_raw.split("/") if n.strip()]

                    # Filtrar: la celda debe contener TODOS los números del CFA
                    # (cubre orden inverso: "8261/8262" == "8262/8261")
                    col_op_upper = df[col_operacion].astype(str).str.upper()
                    if len(numeros_cfa) == 1:
                        mask = col_op_upper.str.contains(f"CFA{numeros_cfa[0]}", na=False)
                    else:
                        mask = col_op_upper.apply(
                            lambda v: all(n in v for n in numeros_cfa)
                        )
                    df_filtrado = df[mask]

                    if df_filtrado.empty:
                        st.warning(f"⚠️ No se encontraron filas para CFA{cfa_raw} en la columna '{col_operacion}'.")
                        total_excel = 0
                    else:
                        # Contar códigos distintos no vacíos para ese CFA
                        total_excel = df_filtrado[col_codigo].dropna().nunique()

                    # Extraer total del docx desde la tabla de dispensas
                    m_total = re.search(r"Total.*?([\d]+)", dispensas, re.IGNORECASE | re.DOTALL)
                    total_ficha = int(m_total.group(1)) if m_total else None

                    # Mostrar comparación
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Total en Ficha (docx)", total_ficha if total_ficha else "No encontrado")
                    with col_b:
                        st.metric("Total en Base Excel", total_excel)
                    with col_c:
                        if total_ficha is not None:
                            if total_ficha == total_excel:
                                st.markdown('<div style="background:#E8F5E9;border-left:5px solid #43A047;border-radius:6px;padding:14px 18px;margin-top:8px;font-size:14px;color:#1b5e20;font-weight:700">✅ Coinciden</div>', unsafe_allow_html=True)
                            else:
                                diff = total_ficha - total_excel
                                signo = "+" if diff > 0 else ""
                                st.markdown(f'<div style="background:#FFF8E1;border-left:5px solid #F5A623;border-radius:6px;padding:14px 18px;margin-top:8px;font-size:14px;color:#5a3e00;font-weight:700">⚠️ Diferencia: {signo}{diff}</div>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error al leer el Excel: {e}")
        else:
            st.info("📂 Sube la base de EED (.xlsx) para comparar el total de dispensas.")

    st.markdown('<div class="caf-footer">CAF – Banco de Desarrollo de América Latina y el Caribe &nbsp;·&nbsp; Gerencia Corporativa de Riesgos</div>', unsafe_allow_html=True)
