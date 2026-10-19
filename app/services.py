"""Lógica de negocio compartida por la API JSON y las pantallas HTML.

Las rutas no validan ni calculan nada por su cuenta: llaman a estas funciones. Así las reglas
(campos obligatorios, estados válidos, cálculo de avance…) existen en un solo lugar y se prueban una vez.
"""
from app import db
from app.models import (CASE_TYPES, PRIORITIES, STATUSES, Project, Section, TestCase, TestResult, TestRun, now)


class ValidationError(ValueError):
    """Dato inválido: la API responde 400 y las pantallas muestran el mensaje."""


# ----------------------------------------------------------------------------- validadores
def clean_text(data, key, label, max_len, required=False):
    value = str(data.get(key) or "").strip()
    if required and not value:
        raise ValidationError(f"El campo «{label}» es obligatorio")
    if len(value) > max_len:
        raise ValidationError(f"«{label}» admite máximo {max_len} caracteres")
    return value


def clean_choice(data, key, label, options, default):
    value = str(data.get(key) or default).strip()
    if value not in options:
        raise ValidationError(f"«{label}» inválido. Valores permitidos: {', '.join(options)}")
    return value


def get_or_404(model, obj_id):
    return db.get_or_404(model, obj_id)


def to_id(value, label):
    """Convierte un id que llega como texto ("3") a número; si no es numérico es un error 400, no un 500."""
    if isinstance(value, int) or str(value).isdigit():
        return int(value)
    raise ValidationError(f"«{label}» debe ser un número")


def parse_steps(value):
    """Acepta una lista [{action, expected}] (API) o texto con un paso por línea "acción | resultado" (formulario)."""
    if isinstance(value, str):
        steps = []
        for line in value.splitlines():
            if not line.strip():
                continue
            action, _, expected = line.partition("|")
            steps.append({"action": action.strip(), "expected": expected.strip()})
        value = steps
    if not isinstance(value, list):
        raise ValidationError("Los pasos deben ser una lista")
    clean = []
    for i, step in enumerate(value, start=1):
        if not isinstance(step, dict):
            raise ValidationError(f"El paso {i} debe ser un objeto {{action, expected}}")
        action = str(step.get("action") or "").strip()
        expected = str(step.get("expected") or "").strip()
        if not action and not expected:
            continue
        if not action:
            raise ValidationError(f"El paso {i} tiene resultado esperado pero no acción")
        clean.append({"action": action[:1000], "expected": expected[:1000]})
    return clean


def steps_to_text(steps):
    return "\n".join(f"{s['action']} | {s['expected']}".rstrip(" |") for s in steps or [])


# ----------------------------------------------------------------------------- proyectos
def save_project(data, project=None):
    name = clean_text(data, "name", "Nombre", 120, required=True)
    description = clean_text(data, "description", "Descripción", 2000)
    project = project or Project()
    project.name, project.description = name, description
    db.session.add(project)
    db.session.commit()
    return project


def delete_object(obj):
    db.session.delete(obj)
    db.session.commit()


# ----------------------------------------------------------------------------- secciones
def save_section(project, data, section=None):
    name = clean_text(data, "name", "Nombre", 120, required=True)
    parent = None
    parent_id = data.get("parent_id") or None
    if parent_id:
        parent = get_or_404(Section, to_id(parent_id, "Sección padre"))
        if parent.project_id != project.id:
            raise ValidationError("La sección padre pertenece a otro proyecto")
        if section is not None and parent.id in section.descendant_ids():
            raise ValidationError("Una sección no puede moverse dentro de sí misma")
    if section is None:
        section = Section(position=len(project.sections) + 1)
    section.name = name
    section.parent = parent
    section.project = project
    db.session.add(section)
    db.session.commit()
    return section


def section_tree(project):
    """Secciones en orden de árbol (padre y luego hijos) con su profundidad, para la barra lateral."""
    ordered = []

    def walk(nodes, depth):
        for node in sorted(nodes, key=lambda s: (s.position, s.id)):
            ordered.append((node, depth))
            walk(node.children, depth + 1)

    walk([s for s in project.sections if s.parent_id is None], 0)
    return ordered


# ----------------------------------------------------------------------------- casos
def save_case(project, data, case=None):
    """Valida todo primero y solo después toca el objeto: un dato inválido no deja cambios a medias."""
    section = get_or_404(Section, to_id(data["section_id"], "Sección")) if data.get("section_id") else None
    if section is None:
        raise ValidationError("Elige la sección del caso")
    if section.project_id != project.id:
        raise ValidationError("La sección pertenece a otro proyecto")
    values = {
        "title": clean_text(data, "title", "Título", 250, required=True),
        "preconditions": clean_text(data, "preconditions", "Precondiciones", 4000),
        "priority": clean_choice(data, "priority", "Prioridad", PRIORITIES, "Medium"),
        "type": clean_choice(data, "type", "Tipo", CASE_TYPES, "Functional"),
        "refs": clean_text(data, "refs", "Referencias", 250),
        "steps": parse_steps(data.get("steps", [])),
    }
    case = case or TestCase()
    for key, value in values.items():
        setattr(case, key, value)
    case.section = section
    case.project = project
    db.session.add(case)
    db.session.commit()
    return case


def filter_cases(project, section_id=None, priority=None, q=None):
    query = db.select(TestCase).where(TestCase.project_id == project.id)
    if section_id:
        section = get_or_404(Section, to_id(section_id, "section_id"))
        query = query.where(TestCase.section_id.in_(section.descendant_ids()))   # incluye subsecciones
    if priority:
        query = query.where(TestCase.priority == priority)
    if q:
        term = q.strip()
        if term[:1] in "cC" and term[1:].isdigit():
            query = query.where(TestCase.id == int(term[1:]))
        else:
            query = query.where(TestCase.title.ilike(f"%{term}%") | TestCase.refs.ilike(f"%{term}%"))
    return db.session.scalars(query.order_by(TestCase.section_id, TestCase.id)).all()


# ----------------------------------------------------------------------------- ejecuciones
def create_run(project, data):
    name = clean_text(data, "name", "Nombre", 150, required=True)
    if data.get("include_all", True) in (True, "1", "true", "on", 1):
        cases = list(project.cases)
    else:
        try:
            ids = {int(i) for i in data.get("case_ids") or []}
        except (TypeError, ValueError):
            raise ValidationError("case_ids debe ser una lista de números") from None
        cases = [c for c in project.cases if c.id in ids]
        if len(cases) != len(ids):
            raise ValidationError("Algunos casos no pertenecen al proyecto")
    if not cases:
        raise ValidationError("La ejecución necesita al menos un caso de prueba")
    description = clean_text(data, "description", "Descripción", 2000)
    # Se calculan las "fotos" de cada caso ANTES de crear la ejecución: así el autoflush
    # (que se dispara al leer case.section) no encuentra objetos a medio armar.
    snapshots = [dict(case=case, case_title=case.title, section_path=case.section.path, priority=case.priority)
                 for case in sorted(cases, key=lambda c: (c.section.path, c.id))]
    run = TestRun(name=name, description=description)
    db.session.add(run)
    run.results = [TestResult(status="untested", **snap) for snap in snapshots]
    run.project = project
    db.session.commit()
    return run


def record_result(result, data):
    """Registra el resultado de un caso en una ejecución (la "ejecución" del caso)."""
    if result.run.is_completed:
        raise ValidationError("La ejecución está cerrada; no admite resultados nuevos")
    status = clean_choice(data, "status", "Estado", STATUSES, "passed")
    comment = clean_text(data, "comment", "Comentario", 4000)
    if status in ("failed", "blocked") and not comment:
        raise ValidationError("Describe el problema en el comentario (obligatorio para Failed y Blocked)")
    result.status = status
    result.comment = comment
    result.executed_by = clean_text(data, "executed_by", "Ejecutado por", 80) or "QA"
    result.executed_at = now() if status != "untested" else None
    db.session.commit()
    return result


def close_run(run):
    if run.is_completed:
        raise ValidationError("La ejecución ya está cerrada")
    run.is_completed = True
    run.completed_at = now()
    db.session.commit()
    return run


# ----------------------------------------------------------------------------- dashboard
def dashboard_stats():
    projects = db.session.scalars(db.select(Project).order_by(Project.name)).all()
    active_runs = db.session.scalars(db.select(TestRun).where(TestRun.is_completed.is_(False))).all()
    totals = {s: 0 for s in STATUSES}
    for run in active_runs:
        for status, n in run.stats().items():
            if status in totals:
                totals[status] += n
    total = sum(totals.values())
    totals["total"] = total
    totals["progress"] = round((total - totals["untested"]) / total * 100, 1) if total else 0.0
    totals["pass_rate"] = round(totals["passed"] / total * 100, 1) if total else 0.0
    recent = db.session.scalars(db.select(TestResult).where(TestResult.executed_at.is_not(None))
                                .order_by(TestResult.executed_at.desc()).limit(8)).all()
    return {"projects": projects, "active_runs": active_runs, "totals": totals,
            "cases": db.session.scalar(db.select(db.func.count(TestCase.id))), "recent": recent}
