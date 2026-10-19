"""Pantallas HTML (Jinja + Tailwind). Usan formularios normales (POST → redirige) y la misma lógica que la API."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app import db
from app.models import (CASE_TYPES, PRIORITIES, STATUS_LABELS, STATUSES, Project, Section, TestCase, TestResult,
                        TestRun)
from app.services import (ValidationError, close_run, create_run, dashboard_stats, delete_object, filter_cases,
                          get_or_404, record_result, save_case, save_project, save_section, section_tree,
                          steps_to_text)

views = Blueprint("views", __name__)


@views.app_context_processor
def common_context():
    """Variables disponibles en todas las plantillas."""
    projects = db.session.scalars(db.select(Project).order_by(Project.name)).all()
    return {"all_projects": projects, "current_project": current_project(projects), "STATUS_LABELS": STATUS_LABELS,
            "PRIORITIES": PRIORITIES, "CASE_TYPES": CASE_TYPES, "STATUSES": STATUSES}


def current_project(projects=None):
    """Proyecto activo: el de ?project=, el guardado en la sesión o el más antiguo."""
    projects = projects if projects is not None else db.session.scalars(db.select(Project).order_by(Project.name)).all()
    wanted = request.args.get("project", type=int) or session.get("project_id")
    project = next((p for p in projects if p.id == wanted), None) or min(projects, key=lambda p: p.id, default=None)
    if project:
        session["project_id"] = project.id
    return project


def require_project():
    """Como current_project(), pero exige que exista uno (para las acciones que crean datos)."""
    project = current_project()
    if project is None:
        raise ValidationError("Primero crea un proyecto")
    return project


def remember_project(project_id):
    """Las páginas de detalle fijan su proyecto para que el selector del encabezado coincida."""
    session["project_id"] = project_id


# ----------------------------------------------------------------------------- dashboard
@views.get("/")
def dashboard():
    return render_template("dashboard.html", stats=dashboard_stats())


# ----------------------------------------------------------------------------- proyectos
@views.get("/projects")
def projects():
    return render_template("projects/list.html")


@views.post("/projects")
def projects_create():
    project = save_project(request.form)
    flash(f"Proyecto «{project.name}» creado", "success")
    return redirect(url_for("views.cases", project=project.id))


@views.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
def projects_edit(project_id):
    project = get_or_404(Project, project_id)
    if request.method == "POST":
        save_project(request.form, project)
        flash("Proyecto actualizado", "success")
        return redirect(url_for("views.projects"))
    return render_template("projects/edit.html", project=project)


@views.post("/projects/<int:project_id>/delete")
def projects_delete(project_id):
    project = get_or_404(Project, project_id)
    delete_object(project)
    session.pop("project_id", None)
    flash(f"Proyecto «{project.name}» eliminado", "success")
    return redirect(url_for("views.projects"))


# ----------------------------------------------------------------------------- casos de prueba
@views.get("/cases")
def cases():
    project = current_project()
    if project is None:
        return redirect(url_for("views.projects"))
    section_id = request.args.get("section", type=int)
    priority = request.args.get("priority") or None
    q = request.args.get("q") or None
    items = filter_cases(project, section_id, priority, q)
    current_section = db.session.get(Section, section_id) if section_id else None
    return render_template("cases/list.html", project=project, tree=section_tree(project), cases=items,
                           current_section=current_section, priority=priority, q=q or "")


@views.post("/sections")
def sections_create():
    project = require_project()
    section = save_section(project, request.form)
    flash(f"Sección «{section.name}» creada", "success")
    return redirect(url_for("views.cases", section=section.id))


@views.post("/sections/<int:section_id>/delete")
def sections_delete(section_id):
    section = get_or_404(Section, section_id)
    total = section.total_cases()
    delete_object(section)
    flash(f"Sección eliminada junto con {total} caso(s)", "success")
    return redirect(url_for("views.cases"))


@views.route("/cases/new", methods=["GET", "POST"])
def cases_new():
    project = require_project()
    if request.method == "POST":
        case = save_case(project, request.form)
        flash(f"Caso C{case.id} creado", "success")
        return redirect(url_for("views.cases", section=case.section_id))
    return render_template("cases/form.html", project=project, tree=section_tree(project), case=None,
                           steps_text="", section_id=request.args.get("section", type=int))


@views.get("/cases/<int:case_id>")
def cases_detail(case_id):
    case = get_or_404(TestCase, case_id)
    remember_project(case.project_id)
    return render_template("cases/detail.html", case=case)


@views.route("/cases/<int:case_id>/edit", methods=["GET", "POST"])
def cases_edit(case_id):
    case = get_or_404(TestCase, case_id)
    remember_project(case.project_id)
    if request.method == "POST":
        save_case(case.project, request.form, case)
        flash(f"Caso C{case.id} actualizado", "success")
        return redirect(url_for("views.cases_detail", case_id=case.id))
    return render_template("cases/form.html", project=case.project, tree=section_tree(case.project), case=case,
                           steps_text=steps_to_text(case.steps), section_id=case.section_id)


@views.post("/cases/<int:case_id>/delete")
def cases_delete(case_id):
    case = get_or_404(TestCase, case_id)
    section_id = case.section_id
    delete_object(case)
    flash(f"Caso C{case_id} eliminado", "success")
    return redirect(url_for("views.cases", section=section_id))


# ----------------------------------------------------------------------------- ejecuciones
@views.get("/runs")
def runs():
    project = current_project()
    if project is None:
        return redirect(url_for("views.projects"))
    return render_template("runs/list.html", project=project)


@views.route("/runs/new", methods=["GET", "POST"])
def runs_new():
    project = require_project()
    if request.method == "POST":
        data = {"name": request.form.get("name"), "description": request.form.get("description"),
                "include_all": request.form.get("include_all") == "1",
                "case_ids": request.form.getlist("case_ids")}
        run = create_run(project, data)
        flash(f"Ejecución R{run.id} creada con {len(run.results)} casos", "success")
        return redirect(url_for("views.runs_detail", run_id=run.id))
    return render_template("runs/form.html", project=project, tree=section_tree(project))


@views.get("/runs/<int:run_id>")
def runs_detail(run_id):
    run = get_or_404(TestRun, run_id)
    remember_project(run.project_id)
    status = request.args.get("status") or None
    results = [r for r in run.results if not status or r.status == status]
    return render_template("runs/detail.html", run=run, results=results, status_filter=status)


@views.post("/results/<int:result_id>")
def results_update(result_id):
    result = get_or_404(TestResult, result_id)
    record_result(result, request.form)
    flash(f"T{result.id}: {STATUS_LABELS[result.status]}", "success")
    return redirect(url_for("views.runs_detail", run_id=result.run_id, status=request.form.get("status_filter") or None)
                    + f"#t{result.id}")


@views.post("/runs/<int:run_id>/close")
def runs_close(run_id):
    close_run(get_or_404(TestRun, run_id))
    flash("Ejecución cerrada", "success")
    return redirect(url_for("views.runs_detail", run_id=run_id))


@views.post("/runs/<int:run_id>/delete")
def runs_delete(run_id):
    delete_object(get_or_404(TestRun, run_id))
    flash("Ejecución eliminada", "success")
    return redirect(url_for("views.runs"))
