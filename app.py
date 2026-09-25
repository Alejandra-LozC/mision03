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

CRITERIA = [
    {
        "name": "Cumplimiento del rol",
        "weight": 0.25,
        "descriptors": {
            4: "Cumple de manera constante y autónoma las responsabilidades de su rol en la Misión 03. Se anticipa a necesidades del equipo y contribuye a que el análisis de las articulaciones avance.",
            3: "Cumple adecuadamente las responsabilidades de su rol y realiza las tareas requeridas dentro del tiempo establecido.",
            2: "Cumple solo parte de las responsabilidades de su rol o requiere recordatorios y seguimiento para completar sus tareas.",
            1: "No cumple las responsabilidades de su rol o su falta de participación afecta el avance del equipo.",
        },
    },
    {
        "name": "Aporte al expediente",
        "weight": 0.20,
        "descriptors": {
            4: "Realiza aportaciones sustanciales que mejoran la calidad, precisión o integración del Expediente de Validación Articular. Sus contribuciones son claramente identificables.",
            3: "Realiza aportaciones pertinentes que contribuyen directamente a completar el expediente solicitado.",
            2: "Realiza aportaciones ocasionales, incompletas o que requieren ser corregidas o complementadas por otros integrantes.",
            1: "Su aportación es mínima, poco pertinente o no contribuye de manera significativa al producto final.",
        },
    },
    {
        "name": "Razonamiento anatómico",
        "weight": 0.20,
        "descriptors": {
            4: "Aplica con precisión conocimientos anatómicos para relacionar huesos, superficies, configuración, subtipo sinovial y movimiento, y sustenta sus conclusiones con evidencia.",
            3: "Aplica correctamente conceptos anatómicos para analizar las articulaciones y proporciona explicaciones adecuadas.",
            2: "Reconoce algunos conceptos anatómicos, pero presenta dificultades para relacionarlos, justificarlos o aplicarlos al análisis.",
            1: "Presenta dificultades importantes para aplicar conceptos anatómicos o sus conclusiones carecen de fundamento anatómico.",
        },
    },
    {
        "name": "Colaboración e integración",
        "weight": 0.20,
        "descriptors": {
            4: "Escucha, comunica sus ideas con claridad, integra las aportaciones de los demás y favorece activamente la relación Anatomía → Clasificación → Movimiento → Ingeniería Biomédica.",
            3: "Se comunica de manera clara y respetuosa, participa en las discusiones y considera las aportaciones de sus compañeros.",
            2: "Participa de manera irregular, comunica sus ideas de forma poco clara o tiene dificultades para integrar las aportaciones de otros.",
            1: "Presenta poca disposición para colaborar, dificulta la comunicación o no favorece el trabajo conjunto.",
        },
    },
    {
        "name": "Responsabilidad y profesionalismo",
        "weight": 0.15,
        "descriptors": {
            4: "Cumple acuerdos y tiempos, mantiene una actitud responsable y demuestra iniciativa, respeto y compromiso con el trabajo del equipo.",
            3: "Cumple los acuerdos y tiempos establecidos y mantiene una actitud respetuosa y responsable durante la misión.",
            2: "Presenta incumplimientos ocasionales de acuerdos o tiempos y requiere recordatorios para mantener su participación y compromiso.",
            1: "Incumple repetidamente acuerdos o tiempos, muestra poca responsabilidad o afecta negativamente el funcionamiento del equipo.",
        },
    },
]

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
    token = st.secrets.get("GITHUB_TOKEN", "")
    repo_name = st.secrets.get("GITHUB_REPO", DEFAULT_REPO)
    branch = st.secrets.get("GITHUB_BRANCH", DEFAULT_BRANCH)
    if not token:
        return False, "No hay GITHUB_TOKEN configurado en Streamlit Secrets."
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


def github_update_results_csv(payload):
    """Create/update a consolidated results.csv in the same GitHub repository."""
    token = st.secrets.get("GITHUB_TOKEN", "")
    repo_name = st.secrets.get("GITHUB_REPO", DEFAULT_REPO)
    branch = st.secrets.get("GITHUB_BRANCH", DEFAULT_BRANCH)
    if not token:
        raise RuntimeError("No hay GITHUB_TOKEN configurado en Streamlit Secrets.")

    gh = Github(token)
    repo = gh.get_repo(repo_name)
    csv_path = "results.csv"

    new_rows = []
    for ev in payload["evaluaciones"]:
        row = {
            "timestamp": payload["timestamp"],
            "evaluador_id": str(payload["evaluador_id"]),
            "evaluador_nombre": payload["evaluador_nombre"],
            "evaluador_rol": payload["evaluador_rol"],
            "equipo": payload["equipo"],
            "evaluado_id": str(ev["evaluado_id"]),
            "evaluado_nombre": ev["evaluado_nombre"],
            "puntuacion_ponderada_4": ev["puntuacion_ponderada_4"],
            "puntuacion_porcentaje": ev["puntuacion_porcentaje"],
            "comentario": ev["comentario"],
            "mejora": ev["mejora"],
        }
        row.update(ev["criterios"])
        new_rows.append(row)

    try:
        existing = repo.get_contents(csv_path, ref=branch)
        old_df = pd.read_csv(io.BytesIO(existing.decoded_content), dtype=str)
        # Una nueva entrega del mismo evaluador reemplaza su entrega anterior.
        old_df = old_df[
            ~(
                old_df["evaluador_id"].astype(str).eq(str(payload["evaluador_id"]))
                & old_df["equipo"].astype(str).eq(str(payload["equipo"]))
            )
        ]
    except GithubException as exc:
        if getattr(exc, "status", None) == 404:
            existing = None
            old_df = pd.DataFrame()
        else:
            raise

    new_df = pd.DataFrame(new_rows)
    combined = pd.concat([old_df, new_df], ignore_index=True)
    content = combined.to_csv(index=False, encoding="utf-8-sig")

    if existing is None:
        repo.create_file(
            csv_path,
            "Crear results.csv de coevaluación Misión 03",
            content,
            branch=branch
        )
    else:
        repo.update_file(
            csv_path,
            "Actualizar results.csv de coevaluación Misión 03",
            content,
            existing.sha,
            branch=branch
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
    st.image("assets/flujograma.png", use_container_width=True)
    st.info("Ingresa tu ID institucional desde el panel lateral para comenzar.")
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

st.markdown("### Criterios de coevaluación")
weights_text = " · ".join(f"{c['name']} {int(c['weight']*100)}%" for c in CRITERIA)
st.caption(weights_text)

if classmates.empty:
    st.warning("No hay compañeros asignados a tu equipo en estudiantes.csv.")
    st.stop()

with st.form("coevaluation_form"):
    all_results = []
    for _, person in classmates.iterrows():
        st.subheader(person["nombre_completo"])
        if "rol" in person and person["rol"].strip():
            st.caption(f"Rol registrado: {person['rol']}")
        values = {}
        for criterion in CRITERIA:
            name = criterion["name"]
            weight = criterion["weight"]
            st.markdown(f"**{name} — {int(weight*100)} %**")
            values[name] = st.radio(
                "Selecciona el nivel que mejor describe el desempeño observado:",
                [4, 3, 2, 1],
                format_func=lambda x, d=criterion["descriptors"]: f"{x} — {d[x]}",
                key=f"{person['id']}_{name}",
                label_visibility="collapsed",
            )
        comment = st.text_area(
            "Evidencia o aportación concreta que justifica tu evaluación",
            key=f"{person['id']}_comment",
            placeholder="Describe una conducta, aportación o evidencia observable de la Misión 03.",
        )
        improvement = st.text_area(
            "¿Qué podría mejorar en próximas misiones? (opcional)",
            key=f"{person['id']}_improvement",
        )
        all_results.append((person, values, comment, improvement))
        st.divider()

    submitted = st.form_submit_button("ENVIAR COEVALUACIÓN", use_container_width=True)

if submitted:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    evaluations = []
    for person, values, comment, improvement in all_results:
        weighted = sum(values[c["name"]] * c["weight"] for c in CRITERIA)
        evaluations.append({
            "evaluado_id": str(person["id"]),
            "evaluado_nombre": person["nombre_completo"],
            "rol": person.get("rol", ""),
            "puntuacion_ponderada_4": round(weighted, 3),
            "puntuacion_porcentaje": round(weighted / 4 * 100, 2),
            "criterios": {c["name"]: values[c["name"]] for c in CRITERIA},
            "comentario": comment.strip(),
            "mejora": improvement.strip(),
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

    with st.spinner("Guardando coevaluación en GitHub..."):
        ok, detail = github_save(payload)
        if ok:
            try:
                github_update_results_csv(payload)
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
