"""API REST en JSON bajo /api. Endpoints CRUD de proyectos, secciones, casos, ejecuciones y resultados."""
from flask import Blueprint, jsonify, request

from app import db
from app.models import Project, Section, TestCase, TestResult, TestRun
from app.services import (ValidationError, close_run, create_run, dashboard_stats, delete_object, filter_cases,
                          get_or_404, record_result, save_case, save_project, save_section, section_tree)

api = Blueprint("api", __name__, url_prefix="/api")


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("El cuerpo de la petición debe ser JSON")
    return data


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


# ----------------------------------------------------------------------------- proyectos
@api.get("/projects")
def list_projects():
    return jsonify([p.to_dict() for p in db.session.scalars(db.select(Project).order_by(Project.name))])


@api.post("/projects")
def create_project():
    return jsonify(save_project(payload()).to_dict()), 201


@api.get("/projects/<int:project_id>")
def get_project(project_id):
    return jsonify(get_or_404(Project, project_id).to_dict())


@api.put("/projects/<int:project_id>")
def update_project(project_id):
    project = get_or_404(Project, project_id)
    return jsonify(save_project({**project.to_dict(), **payload()}, project).to_dict())


@api.delete("/projects/<int:project_id>")
def delete_project(project_id):
    delete_object(get_or_404(Project, project_id))
    return jsonify({"deleted": project_id})


# ----------------------------------------------------------------------------- secciones
@api.get("/projects/<int:project_id>/sections")
def list_sections(project_id):
    project = get_or_404(Project, project_id)
    return jsonify([dict(s.to_dict(), depth=depth) for s, depth in section_tree(project)])


@api.post("/projects/<int:project_id>/sections")
def create_section(project_id):
    return jsonify(save_section(get_or_404(Project, project_id), payload()).to_dict()), 201


@api.put("/sections/<int:section_id>")
def update_section(section_id):
    section = get_or_404(Section, section_id)
    data = {"name": section.name, "parent_id": section.parent_id, **payload()}
    return jsonify(save_section(section.project, data, section).to_dict())


@api.delete("/sections/<int:section_id>")
def delete_section(section_id):
    section = get_or_404(Section, section_id)
    removed = section.total_cases()
    delete_object(section)                      # en cascada: subsecciones y casos
    return jsonify({"deleted": section_id, "cases_deleted": removed})


# ----------------------------------------------------------------------------- casos de prueba
@api.get("/projects/<int:project_id>/cases")
def list_cases(project_id):
    project = get_or_404(Project, project_id)
    cases = filter_cases(project, request.args.get("section_id"), request.args.get("priority"), request.args.get("q"))
    return jsonify([c.to_dict() for c in cases])


@api.post("/projects/<int:project_id>/cases")
def create_case(project_id):
    return jsonify(save_case(get_or_404(Project, project_id), payload()).to_dict()), 201


@api.get("/cases/<int:case_id>")
def get_case(case_id):
    return jsonify(get_or_404(TestCase, case_id).to_dict())


@api.put("/cases/<int:case_id>")
def update_case(case_id):
    case = get_or_404(TestCase, case_id)
    return jsonify(save_case(case.project, {**case.to_dict(), **payload()}, case).to_dict())


@api.delete("/cases/<int:case_id>")
def delete_case(case_id):
    delete_object(get_or_404(TestCase, case_id))
    return jsonify({"deleted": case_id})


# ----------------------------------------------------------------------------- ejecuciones y resultados
@api.get("/projects/<int:project_id>/runs")
def list_runs(project_id):
    return jsonify([r.to_dict() for r in get_or_404(Project, project_id).runs])


@api.post("/projects/<int:project_id>/runs")
def create_test_run(project_id):
    return jsonify(create_run(get_or_404(Project, project_id), payload()).to_dict(with_results=True)), 201


@api.get("/runs/<int:run_id>")
def get_run(run_id):
    return jsonify(get_or_404(TestRun, run_id).to_dict(with_results=True))


@api.post("/runs/<int:run_id>/close")
def close_test_run(run_id):
    return jsonify(close_run(get_or_404(TestRun, run_id)).to_dict())


@api.delete("/runs/<int:run_id>")
def delete_run(run_id):
    delete_object(get_or_404(TestRun, run_id))
    return jsonify({"deleted": run_id})


@api.put("/results/<int:result_id>")
def update_result(result_id):
    return jsonify(record_result(get_or_404(TestResult, result_id), payload()).to_dict())


@api.get("/stats")
def stats():
    data = dashboard_stats()
    return jsonify({"projects": len(data["projects"]), "cases": data["cases"],
                    "active_runs": len(data["active_runs"]), "totals": data["totals"]})
