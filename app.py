import hashlib
import io
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from github import Github, GithubException
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

st.set_page_config(page_title="PROMETHEUS · Coevaluación M03", page_icon="◈", layout="wide")

MISSION = "03"
DATA_FILE = Path(__file__).parent / "estudiantes.csv"
DEFAULT_REPO = "Alejandra-LozC/mision03"
DEFAULT_BRANCH = "main"

ROLES = [
    "Coordinador/a de misión",
    "Especialista anatómico/a",
    "Investigador/a biomédico/a",
    "Documentador/a",
    "Integrador/a y portavoz",
]

ROLE_RESPONSIBILITIES = {
    "Coordinador/a de misión": ["Organizó el trabajo y la distribución de las seis articulaciones.","Coordinó tiempos y tareas y dio seguimiento al avance.","Verificó que todas las articulaciones fueran analizadas.","Identificó información pendiente o inconsistencias en el trabajo del equipo."],
    "Especialista anatómico/a": ["Verificó la correcta identificación de cada articulación.","Confirmó los huesos y superficies articulares participantes.","Determinó el subtipo sinovial con base en características anatómicas.","Utilizó nomenclatura anatómica y relaciones/orientación correctas.","Comprobó que las clasificaciones estuvieran sustentadas con evidencia."],
    "Investigador/a biomédico/a": ["Analizó cómo la configuración articular condiciona el movimiento.","Relacionó la anatomía con aspectos básicos de biomecánica.","Identificó características anatómicas relevantes para un dispositivo biomédico.","Definió información anatómica indispensable para el diseño biomédico."],
    "Documentador/a": ["Registró la evidencia del laboratorio mediante fotografías, esquemas o notas.","Organizó la información correspondiente a las seis articulaciones.","Preparó fichas, esquemas o tablas para integrar la información.","Integró las fuentes y contribuyó a la preparación del PDF final."],
    "Integrador/a y portavoz": ["Integró las contribuciones de los integrantes.","Verificó la coherencia entre estructura, clasificación, movimiento y aplicación biomédica.","Detectó contradicciones o información faltante.","Contribuyó a las conclusiones del equipo y a su explicación cuando fue necesario."],
}
LEVELS = {
    4: "Profesional — Desempeñó las responsabilidades de su rol de manera clara, constante y autónoma, con una participación que contribuyó directamente al avance del equipo.",
    3: "Competente todavía con áreas de oportunidad — Desempeñó adecuadamente las responsabilidades de su rol y realizó las tareas esperadas, aunque pudo haber aspectos por fortalecer.",
    2: "Adecuado pero evidentemente en desarrollo — Cumplió parcialmente las responsabilidades de su rol o necesitó apoyo, recordatorios o seguimiento para completar su participación.",
    1: "Solamente fue testigo del proceso — Su participación observable fue mínima y no permitió identificar un desempeño efectivo de las responsabilidades del rol.",
}


st.markdown("""
<style>
.stApp { background:#071018; color:#EAF7FF; }
.block-container { max-width:1150px; padding-top:1.5rem; padding-bottom:3rem; }
h1,h2,h3 { color:#5CE1FF; }
.case-card { border:1px solid #16485C; border-radius:14px; padding:18px; background:linear-gradient(135deg,#09151F,#071018); margin-bottom:14px; }
.gold-card { border:1px solid #8D6B1F; border-radius:14px; padding:18px; background:linear-gradient(135deg,#17140B,#071018); margin-bottom:14px; }
.small-note { color:#B8CBD5; font-size:.92rem; }
</style>
""", unsafe_allow_html=True)


def load_students():
    if not DATA_FILE.exists():
        st.error("No se encontró estudiantes.csv en el repositorio.")
        st.info("Coloca en el repositorio un archivo estudiantes.csv con las columnas: id, nombre_completo y mision03. La columna rol es opcional.")
        st.stop()
    df = pd.read_csv(DATA_FILE, dtype=str).fillna("")
    required = {"id", "nombre_completo", "mision03"}
    missing = required - set(df.columns)
    if missing:
        st.error(f"A estudiantes.csv le faltan columnas: {', '.join(sorted(missing))}")
        st.stop()
    df["id"] = df["id"].str.strip()
    df["nombre_completo"] = df["nombre_completo"].str.strip()
    df["mision03"] = pd.to_numeric(df["mision03"], errors="coerce")
    df = df.dropna(subset=["mision03"]).copy()
    df["mision03"] = df["mision03"].astype(int)
    return df


def make_receipt_pdf(payload, confirmation_code):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=1.6*cm, leftMargin=1.6*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReceiptTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=18, leading=22, spaceAfter=10)
    subtitle = ParagraphStyle("ReceiptSub", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10, leading=14, spaceAfter=16)
    body = ParagraphStyle("ReceiptBody", parent=styles["Normal"], fontSize=9.5, leading=13)
    story = [
        Paragraph("PROMETHEUS", title),
        Paragraph("Misión 03 · Comprobante de Coevaluación", subtitle),
        Paragraph("Este documento acredita que se realizó y envió una coevaluación. No muestra las puntuaciones asignadas a los compañeros, para preservar la confidencialidad de la evaluación entre pares.", body),
        Spacer(1, 12),
    ]
    data = [
        ["Evaluador/a", payload["evaluador_nombre"]],
        ["ID institucional", payload["evaluador_id"]],
        ["Equipo", str(payload["equipo"])],
        ["Rol desempeñado", payload["evaluador_rol"]],
        ["Fecha y hora", payload["timestamp"]],
        ["Compañeros evaluados", str(len(payload["evaluaciones"]))],
        ["Código de comprobación", confirmation_code],
    ]
    table = Table(data, colWidths=[5*cm, 11*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), (0, -1), "#EAF3F7"),
        ("GRID", (0,0), (-1,-1), 0.5, "#9AAAB2"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph("Guarda este PDF y entrégalo en el espacio indicado por la profesora como evidencia de realización de la coevaluación.", body))
    doc.build(story)
    return buffer.getvalue()


def github_save(payload):
    github_secrets = st.secrets.get("github", {})
    token = github_secrets.get("GITHUB_TOKEN", "")
    repo_name = github_secrets.get("GITHUB_REPO", DEFAULT_REPO)
    branch = github_secrets.get("GITHUB_BRANCH", DEFAULT_BRANCH)
    if not token:
        return False, "No hay github.GITHUB_TOKEN configurado en Streamlit Secrets."
    try:
        gh = Github(token)
        repo = gh.get_repo(repo_name)
        evaluator_id = str(payload["evaluador_id"]).strip().replace("/", "_")
        path = f"respuestas/mision03_evaluador_{evaluator_id}.json"
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        try:
            existing = repo.get_contents(path, ref=branch)
            repo.update_file(path, f"Actualizar coevaluación Misión 03 - {evaluator_id}", content, existing.sha, branch=branch)
            return True, path
        except GithubException as exc:
            if getattr(exc, "status", None) != 404:
                raise
            repo.create_file(path, f"Registrar coevaluación Misión 03 - {evaluator_id}", content, branch=branch)
            return True, path
    except GithubException as e:
        msg = e.data.get("message", str(e)) if isinstance(getattr(e, "data", None), dict) else str(e)
        return False, f"GitHub rechazó el guardado: {msg}"
    except Exception as e:
        return False, f"No fue posible guardar la coevaluación: {e}"


def update_results_csv(rows):
    """Create/update the consolidated results.csv in GitHub for the current submission."""
    github_secrets = st.secrets.get("github", {})
    token = github_secrets.get("GITHUB_TOKEN", "")
    repo_name = github_secrets.get("GITHUB_REPO", DEFAULT_REPO)
    branch = github_secrets.get("GITHUB_BRANCH", DEFAULT_BRANCH)
    if not token:
        raise RuntimeError("No hay github.GITHUB_TOKEN configurado en Streamlit Secrets.")

    gh = Github(token)
    repo = gh.get_repo(repo_name)
    csv_path = "results.csv"

    new_df = pd.DataFrame(rows)

    try:
        existing = repo.get_contents(csv_path, ref=branch)
        old_df = pd.read_csv(io.BytesIO(existing.decoded_content), dtype=str)

        if not old_df.empty and "evaluador_id" in old_df.columns and "equipo" in old_df.columns:
            evaluator_id = str(rows[0]["evaluador_id"])
            team = str(rows[0]["equipo"])
            old_df = old_df[
                ~(
                    old_df["evaluador_id"].astype(str).eq(evaluator_id)
                    & old_df["equipo"].astype(str).eq(team)
                )
            ]

        combined = pd.concat([old_df, new_df], ignore_index=True)
        content = combined.to_csv(index=False, encoding="utf-8-sig")

        repo.update_file(
            csv_path,
            "Actualizar results.csv de coevaluación Misión 03",
            content,
            existing.sha,
            branch=branch,
        )
    except GithubException as exc:
        if getattr(exc, "status", None) != 404:
            raise
        content = new_df.to_csv(index=False, encoding="utf-8-sig")
        repo.create_file(
            csv_path,
            "Crear results.csv de coevaluación Misión 03",
            content,
            branch=branch,
        )


students = load_students()

if "evaluator" not in st.session_state:
    st.session_state.evaluator = None
if "evaluator_role" not in st.session_state:
    st.session_state.evaluator_role = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "receipt" not in st.session_state:
    st.session_state.receipt = None

st.title("PROMETHEUS")
st.caption("COEVALUACIÓN · MISIÓN 03 · PLATAFORMA DE MOVIMIENTO")

with st.sidebar:
    st.header("Acceso")
    entered_id = st.text_input("ID institucional", max_chars=30, type="password")
    if st.button("Ingresar", use_container_width=True):
        match = students[students["id"] == entered_id.strip()]
        if match.empty:
            st.error("ID no encontrado.")
        else:
            st.session_state.evaluator = match.iloc[0].to_dict()
            st.session_state.evaluator_role = None
            st.session_state.submitted = False
            st.session_state.receipt = None
            st.rerun()

    if st.session_state.evaluator:
        ev = st.session_state.evaluator
        st.divider()
        st.write(f"**Equipo {int(ev['mision03'])}**")
        st.write(ev["nombre_completo"])
        if st.session_state.evaluator_role:
            st.write(f"**Rol:** {st.session_state.evaluator_role}")
        if st.button("Cerrar sesión", use_container_width=True):
            st.session_state.evaluator = None
            st.session_state.evaluator_role = None
            st.session_state.submitted = False
            st.session_state.receipt = None
            st.rerun()

if not st.session_state.evaluator:
    st.info("Ingresa tu ID institucional desde el panel lateral para comenzar incluye los 00 del inicio.")
    st.stop()

ev = st.session_state.evaluator
group = int(ev["mision03"])

if not st.session_state.evaluator_role:
    st.markdown("### Antes de comenzar")
    st.markdown('<div class="gold-card"><strong>Indica el rol que desempeñaste en la Misión 03.</strong><br><span class="small-note">No necesitas conocer ni registrar el rol de tus compañeros. Esta selección corresponde únicamente a tu propio rol y quedará incluida en tu comprobante.</span></div>', unsafe_allow_html=True)
    selected_role = st.selectbox("Mi rol en la Misión 03", ["Selecciona tu rol..."] + ROLES)
    if st.button("CONTINUAR A LA COEVALUACIÓN", use_container_width=True):
        if selected_role == "Selecciona tu rol...":
            st.error("Selecciona el rol que desempeñaste para continuar.")
        else:
            st.session_state.evaluator_role = selected_role
            st.rerun()
    st.stop()

classmates = students[(students["mision03"] == group) & (students["id"] != ev["id"])].sort_values("nombre_completo")

st.markdown(f'<div class="case-card"><h3>Equipo {group}</h3><div>Evalúa a cada integrante de tu equipo excepto a ti mismo.</div></div>', unsafe_allow_html=True)
st.markdown('<div class="case-card"><strong>Propósito:</strong> Valora el desempeño observado durante la Misión 03. Basa tus respuestas en conductas, aportaciones y evidencias relacionadas con el análisis de articulaciones, movimiento y aplicación biomédica; no en personalidad o afinidad.</div>', unsafe_allow_html=True)

st.markdown("### Coevaluación del desempeño del rol")
st.caption("Para cada compañero, indica primero el rol que realmente desempeñó. Después valora únicamente el desempeño de ese rol.")

if classmates.empty:
    st.warning("No hay compañeros asignados a tu equipo en estudiantes.csv.")
    st.stop()

all_results = []

for _, person in classmates.iterrows():
    st.subheader(person["nombre_completo"])

    evaluated_role = st.selectbox(
        "Rol que realmente desempeñó en la Misión 03",
        ["Selecciona el rol..."] + ROLES,
        key=f"{person['id']}_role",
    )

    level = None
    evidence = ""
    improvement = ""

    if evaluated_role != "Selecciona el rol...":
        st.markdown("**Responsabilidades que corresponden a este rol:**")
        for responsibility in ROLE_RESPONSIBILITIES[evaluated_role]:
            st.markdown(f"- {responsibility}")

        st.markdown("**Desempeño del rol**")
        level = st.radio(
            "Selecciona el nivel que mejor describe el desempeño observado:",
            [4, 3, 2, 1],
            format_func=lambda x: f"{x} — {LEVELS[x]}",
            key=f"{person['id']}_level",
        )

        evidence = st.text_area(
            "¿Qué podrías señalar como la evidencia más concreta de su participación, que te hizo calificar así?",
            key=f"{person['id']}_evidence",
            placeholder="Describe una conducta, aportación o evidencia observable.",
        )
        improvement = st.text_area(
            "¿Qué observación tienes sobre lo que podría mejorar al trabajar en grupo?",
            key=f"{person['id']}_improvement",
            placeholder="Escribe una observación concreta y útil.",
        )

    all_results.append((person, evaluated_role, level, evidence, improvement))
    st.divider()

submitted = st.button("ENVIAR COEVALUACIÓN", use_container_width=True)
if submitted:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    evaluations = []
    for person, evaluated_role, level, evidence, improvement in all_results:
        if evaluated_role == "Selecciona el rol..." or level is None:
            st.error(f"Selecciona el rol y la calificación de {person['nombre_completo']}.")
            st.stop()
        evaluations.append({
            "evaluado_id": str(person["id"]),
            "evaluado_nombre": person["nombre_completo"],
            "rol_evaluado": evaluated_role,
            "calificacion": int(level),
            "nivel": LEVELS[level],
            "evidencia_participacion": evidence.strip(),
            "observacion_trabajo_grupo": improvement.strip(),
        })

    canonical = json.dumps({
        "mision": MISSION,
        "evaluador_id": str(ev["id"]),
        "equipo": group,
        "timestamp": timestamp,
        "evaluaciones": evaluations,
    }, ensure_ascii=False, sort_keys=True)
    confirmation_code = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12].upper()

    payload = {
        "mision": MISSION,
        "timestamp": timestamp,
        "evaluador_id": str(ev["id"]),
        "evaluador_nombre": ev["nombre_completo"],
        "evaluador_rol": st.session_state.evaluator_role,
        "equipo": group,
        "evaluaciones": evaluations,
        "confirmation_code": confirmation_code,
    }

    evaluations_with_context = []
    for evaluation in evaluations:
        evaluations_with_context.append({
            "timestamp": timestamp,
            "evaluador_id": str(ev["id"]),
            "evaluador_nombre": ev["nombre_completo"],
            "rol_evaluador": st.session_state.evaluator_role,
            "equipo": group,
            **evaluation,
        })

    with st.spinner("Guardando coevaluación en GitHub..."):
        ok, detail = github_save(payload)
        if ok:
            try:
                update_results_csv(evaluations_with_context)
            except Exception as csv_error:
                # El JSON individual ya quedó guardado; informar el problema del consolidado.
                ok = False
                detail = f"El registro individual se guardó, pero no fue posible actualizar results.csv: {csv_error}"
    if ok:
        pdf_bytes = make_receipt_pdf(payload, confirmation_code)
        st.session_state.submitted = True
        st.session_state.receipt = pdf_bytes
        st.success("Coevaluación registrada correctamente.")
        st.caption(f"Registro guardado en GitHub: {detail}")
        st.markdown("### Evidencia de envío")
        st.write("Descarga este comprobante y entrégalo en Brightspace si tu profesora lo solicita.")
        st.download_button(
            "DESCARGAR COMPROBANTE PDF",
            data=pdf_bytes,
            file_name=f"Comprobante_Coevaluacion_M03_{ev['id']}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
        st.code(confirmation_code, language=None)
    else:
        st.error(detail)
        st.warning("La coevaluación no se marcó como registrada porque no pudo guardarse en el almacenamiento permanente.")

if st.session_state.submitted:
    st.info("Tu coevaluación ya fue enviada. Puedes cerrar sesión.")
