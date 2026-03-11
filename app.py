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

def extraer_presentacion_informes(ruta, extension):
    """
    Tabla 'Presentación de informes': 3 columnas físicas en Word.
      col[0] = "Presentación de informes" (combinada verticalmente → se repite al leer)
      col[1] = sub-etiqueta exacta: "Última auditoría" / "Final" / "Pendientes"
      col[2] = valor (texto largo)
    Estrategia: leemos las celdas RAW (con duplicados) y accedemos por índice fijo [1] y [2],
    que corresponden siempre a etiqueta y valor en tablas de 3 columnas.
    """
    resultados = {"Última auditoría": "No encontrado", "Final": "No encontrado", "Pendientes": "No encontrado"}
    # etiqueta exacta (lower) → nombre del campo
    mapa_exacto = {
        "última auditoría": "Última auditoría",
        "ultima auditoria": "Última auditoría",
        "final":            "Final",
        "pendientes":       "Pendientes",
    }
    try:
        if extension == ".docx":
            from docx import Document
            doc = Document(ruta)
            for tabla in doc.tables:
                texto_tabla = " ".join(c.text for fila in tabla.rows for c in fila.cells).lower()
                if "presentaci" not in texto_tabla or "informe" not in texto_tabla:
                    continue
                # Determinar número de columnas físicas de la tabla
                n_cols = len(tabla.columns)
                for fila in tabla.rows:
                    celdas_raw = [c.text.strip() for c in fila.cells]
                    if n_cols == 3 and len(celdas_raw) >= 3:
                        # Acceso directo: col[1]=etiqueta, col[2]=valor
                        etiqueta = celdas_raw[1].lower().strip()
                        valor    = celdas_raw[2].strip()
                    else:
                        # Fallback: desduplicar y usar penúltima/última
                        celdas = list(dict.fromkeys(celdas_raw))
                        celdas = [c for c in celdas if c]
                        if len(celdas) < 2:
                            continue
                        etiqueta = celdas[-2].lower().strip()
                        valor    = celdas[-1].strip()
                    nombre = mapa_exacto.get(etiqueta)
                    if nombre and valor and resultados[nombre] == "No encontrado":
                        resultados[nombre] = valor
        else:
            import pdfplumber
            with pdfplumber.open(ruta) as pdf:
                texto = "\n".join(p.extract_text() or "" for p in pdf.pages)
            for clave, nombre in mapa_exacto.items():
                m = re.search(rf"{re.escape(clave)}[^\n]*\n([^\n]+)", texto, re.IGNORECASE)
                if m and resultados[nombre] == "No encontrado":
                    resultados[nombre] = m.group(1).strip()
    except Exception as e:
        for k in resultados:
            resultados[k] = f"Error: {e}"
    return resultados

def tabla_html(filas):
    rows = ""
    for label, valor in filas:
        rows += f"<tr><td>{label}</td><td>{valor or '—'}</td></tr>"
    return f'<table class="caf-table">{rows}</table>'

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
            texto    = extraer_texto_pdf(ruta_tmp) if extension == ".pdf" else extraer_texto_docx(ruta_tmp)
            informes = extraer_presentacion_informes(ruta_tmp, extension)

        os.unlink(ruta_tmp)

        # ── Sección 1: Informe de la Operación ────────────────────────────────
        resultados = {
            "Nombre de la Operación":           buscar_campo(texto, r"Nombre de la operaci[oó]n"                  + SEP + r"([^|\n]+)"),
            "Prestatario":                       buscar_campo(texto, r"Prestatario"                                + SEP + r"([^|\n]+)"),
            "País":                              buscar_campo(texto, r"Pa[ií]s"                                    + SEP + r"([^|\n]+)"),
            "Garante":                           buscar_campo(texto, r"Garante"                                    + SEP + r"([^|\n]+)"),
            "Monto préstamo CAF (Aprobado)":     buscar_campo(texto, r"Monto del pr[eé]stamo[\s\S]*?aprobado CAF" + SEP + r"((?:Contractual[^|\n]+|(?:US\$|USD)\s*[\d.,]+[^|\n]*))"),
            "Monto préstamo CAF (Desembolsado)": buscar_campo(texto, r"(?:Desembolsado\s*(?::|[|\s])+\s*)((?:US\$|USD)\s*[\d.,]+[^\n]*)"),
        }

        st.markdown('<div class="section-header">📋 &nbsp;Informe de la Operación</div>', unsafe_allow_html=True)
        st.markdown(tabla_html(list(resultados.items())), unsafe_allow_html=True)

        # ── Sección 2: Presentación de Informes ───────────────────────────────
        st.markdown('<div class="section-header">📄 &nbsp;Presentación de Informes</div>', unsafe_allow_html=True)
        st.markdown(tabla_html([
            ("Última auditoría", informes["Última auditoría"]),
            ("Final",            informes["Final"]),
            ("Pendientes",       informes["Pendientes"]),
        ]), unsafe_allow_html=True)

        st.markdown('<div class="caf-footer">CAF – Banco de Desarrollo de América Latina y el Caribe &nbsp;·&nbsp; Gerencia Corporativa de Riesgos</div>', unsafe_allow_html=True)
