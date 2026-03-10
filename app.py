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
.caf-alert {
    background: #FFF8E1;
    border-left: 5px solid #F5A623;
    border-radius: 6px;
    padding: 14px 18px;
    font-size: 13.5px;
    color: #5a3e00;
    line-height: 1.7;
    box-shadow: 0 2px 8px rgba(245,166,35,0.12);
    margin-bottom: 4px;
    margin-top: 12px;
}
.caf-success {
    background: #E8F5E9;
    border-left: 5px solid #43A047;
    border-radius: 6px;
    padding: 14px 18px;
    font-size: 13.5px;
    color: #1b5e20;
    line-height: 1.7;
    margin-bottom: 4px;
    margin-top: 12px;
}
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
        <div class="caf-header-title">Extractor de Datos &nbsp;|&nbsp; Informe Final de Resultados</div>
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
            # Eliminar duplicados que genera Word en celdas combinadas
            celdas = list(dict.fromkeys(celdas))
            lineas.append(" | ".join(celdas))
    return "\n".join(lineas)

SEP = r"[\s|]+"

def buscar_campo(texto, patron, grupo=1):
    match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE)
    if not match:
        return "No encontrado"
    valor = match.group(grupo).strip().strip("|").strip()
    return valor if valor else "No encontrado"

def buscar_campo_multilinea(texto, patron):
    match = re.search(patron, texto, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if not match:
        return "No encontrado"
    return " | ".join(g.strip() for g in match.groups() if g and g.strip())

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
            texto = extraer_texto_pdf(ruta_tmp) if extension == ".pdf" else extraer_texto_docx(ruta_tmp)

        os.unlink(ruta_tmp)

        # ── Sección 1: Identificación ──────────────────────────────────────────
        nombre_operacion = buscar_campo(texto, r"Nombre de la operaci[oó]n" + SEP + r"([^|\n]+)")
        prestatario      = buscar_campo(texto, r"Prestatario"               + SEP + r"([^|\n]+)")
        org_ejecutor     = buscar_campo(texto, r"Organismo Ejecutor"        + SEP + r"([^|\n]+)")
        pais             = buscar_campo(texto, r"Pa[ií]s"                   + SEP + r"([^|\n]+)")
        garante          = buscar_campo(texto, r"Garante"                   + SEP + r"([^|\n]+)")

        st.markdown('<div class="section-header">📋 &nbsp;1. Identificación</div>', unsafe_allow_html=True)
        st.markdown(tabla_html([
            ("Nombre de la Operación",  nombre_operacion),
            ("Prestatario",             prestatario),
            ("Organismo Ejecutor",      org_ejecutor),
            ("País",                    pais),
            ("Garante",                 garante),
        ]), unsafe_allow_html=True)

        # ── Sección 2: Datos Generales ─────────────────────────────────────────
        monto_ppi_contractual  = buscar_campo(texto, r"Monto total del PPI[\s\S]*?aprobado CAF" + SEP + r"(Contractual[^|\n]+)")
        monto_ppi_final        = buscar_campo(texto, r"(Final\s+USD[^|\n]+)")
        monto_prestamo_cont    = buscar_campo(texto, r"Monto del pr[eé]stamo[\s\S]*?aprobado CAF" + SEP + r"(Contractual[^|\n]+)")
        monto_prestamo_desemb  = buscar_campo(texto, r"(Desembolsado:\s*US\$[^|\n]+)")
        monto_verde            = buscar_campo(texto, r"Monto financiamiento verde"               + SEP + r"([^|\n]+)")
        fecha_vigencia         = buscar_campo(texto, r"Fecha de entrada en vigencia"             + SEP + r"([^|\n]+)")
        fecha_primer_desemb    = buscar_campo(texto, r"Fecha del primer desembolso"              + SEP + r"([^|\n]+)")
        fecha_segundo_desemb   = buscar_campo(texto, r"Fecha del segundo desembolso"             + SEP + r"([^|\n]+)")
        fecha_ultimo_desemb    = buscar_campo(texto, r"Fecha del [uú]ltimo desembolso"           + SEP + r"([^|\n]+)")
        plazo_desembolsos      = buscar_campo(texto, r"Plazo de desembolsos"                     + SEP + r"([^|\n]+)")
        fecha_fin_ppi          = buscar_campo(texto, r"Fecha estimada de finalizaci[oó]n del PPI"+ SEP + r"([^|\n]+)")
        fecha_inicio_op        = buscar_campo(texto, r"Fecha estimada para inicio de operaci[oó]n" + SEP + r"([^|\n]+)")
        desemb_justificar      = buscar_campo(texto, r"Desembolsos por justificar"               + SEP + r"([^|\n]+)")

        st.markdown('<div class="section-header">📊 &nbsp;2. Datos Generales</div>', unsafe_allow_html=True)
        st.markdown(tabla_html([
            ("Monto total PPI aprobado CAF (Contractual)", monto_ppi_contractual),
            ("Monto total PPI aprobado CAF (Final)",       monto_ppi_final),
            ("Monto préstamo aprobado CAF (Contractual)",  monto_prestamo_cont),
            ("Monto préstamo aprobado CAF (Desembolsado)", monto_prestamo_desemb),
            ("Monto financiamiento verde",                 monto_verde),
            ("Fecha de entrada en vigencia",               fecha_vigencia),
            ("Fecha del primer desembolso",                fecha_primer_desemb),
            ("Fecha del segundo desembolso",               fecha_segundo_desemb),
            ("Fecha del último desembolso",                fecha_ultimo_desemb),
            ("Plazo de desembolsos",                       plazo_desembolsos),
            ("Fecha estimada de finalización del PPI",     fecha_fin_ppi),
            ("Fecha estimada para inicio de operación",    fecha_inicio_op),
            ("Desembolsos por justificar",                 desemb_justificar),
        ]), unsafe_allow_html=True)

        st.markdown('<div class="caf-footer">CAF – Banco de Desarrollo de América Latina y el Caribe &nbsp;·&nbsp; Gerencia Corporativa de Riesgos</div>', unsafe_allow_html=True)
