"""Modelos de datos (SQLAlchemy 2.x).

    Project ──< Section (árbol: parent_id) ──< TestCase
       │                                           │
       └──< TestRun ──< TestResult >───────────────┘  (case_id puede quedar NULL si se borra el caso)
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db

STATUSES = ["passed", "failed", "blocked", "untested"]
STATUS_LABELS = {"passed": "Passed", "failed": "Failed", "blocked": "Blocked", "untested": "Untested"}
PRIORITIES = ["Low", "Medium", "High", "Critical"]
CASE_TYPES = ["Functional", "Smoke", "Regression", "Performance"]


def now():
    return datetime.now().replace(microsecond=0)


class Project(db.Model):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=now)

    sections: Mapped[list["Section"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    cases: Mapped[list["TestCase"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    runs: Mapped[list["TestRun"]] = relationship(back_populates="project", cascade="all, delete-orphan",
                                                 order_by="TestRun.id.desc()")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description,
                "created_at": self.created_at.isoformat(sep=" "), "cases": len(self.cases),
                "sections": len(self.sections), "runs": len(self.runs)}


class Section(db.Model):
    """Carpeta de casos. `parent_id` apunta a la sección padre (NULL = raíz)."""
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sections.id"))
    name: Mapped[str] = mapped_column(String(120))
    position: Mapped[int] = mapped_column(default=0)

    project: Mapped[Project] = relationship(back_populates="sections")
    parent: Mapped[Optional["Section"]] = relationship(back_populates="children", remote_side=[id])
    children: Mapped[list["Section"]] = relationship(back_populates="parent", cascade="all, delete-orphan",
                                                     order_by="Section.position")
    cases: Mapped[list["TestCase"]] = relationship(back_populates="section", cascade="all, delete-orphan")

    @property
    def path(self):
        """Ruta completa: 'Facturación › Emitir factura'."""
        names, node = [], self
        while node is not None:
            names.insert(0, node.name)
            node = node.parent
        return " › ".join(names)

    def descendant_ids(self):
        ids = [self.id]
        for child in self.children:
            ids += child.descendant_ids()
        return ids

    def total_cases(self):
        return len(self.cases) + sum(child.total_cases() for child in self.children)

    def to_dict(self):
        return {"id": self.id, "project_id": self.project_id, "parent_id": self.parent_id, "name": self.name,
                "path": self.path, "cases": len(self.cases), "total_cases": self.total_cases()}


class TestCase(db.Model):
    __tablename__ = "test_cases"
    __test__ = False   # que pytest no confunda el modelo con una clase de pruebas

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"))
    title: Mapped[str] = mapped_column(String(250))
    preconditions: Mapped[str] = mapped_column(Text, default="")
    steps: Mapped[list] = mapped_column(JSON, default=list)          # [{"action": ..., "expected": ...}]
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    type: Mapped[str] = mapped_column(String(20), default="Functional")
    refs: Mapped[str] = mapped_column(String(250), default="")
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)

    project: Mapped[Project] = relationship(back_populates="cases")
    section: Mapped[Section] = relationship(back_populates="cases")
    results: Mapped[list["TestResult"]] = relationship(back_populates="case")

    @property
    def last_status(self):
        executed = [r for r in self.results if r.status != "untested" and r.executed_at]
        return max(executed, key=lambda r: r.executed_at).status if executed else None

    def to_dict(self):
        return {"id": self.id, "code": f"C{self.id}", "project_id": self.project_id, "section_id": self.section_id,
                "section": self.section.path, "title": self.title, "preconditions": self.preconditions,
                "steps": self.steps or [], "priority": self.priority, "type": self.type, "refs": self.refs,
                "last_status": self.last_status, "updated_at": self.updated_at.isoformat(sep=" ")}


class TestRun(db.Model):
    __tablename__ = "test_runs"
    __test__ = False

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")
    is_completed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now)
    completed_at: Mapped[Optional[datetime]]

    project: Mapped[Project] = relationship(back_populates="runs")
    results: Mapped[list["TestResult"]] = relationship(back_populates="run", cascade="all, delete-orphan",
                                                       order_by="TestResult.id")

    def stats(self):
        counts = {s: 0 for s in STATUSES}
        for r in self.results:
            counts[r.status] += 1
        total = len(self.results)
        counts["total"] = total
        counts["progress"] = round((total - counts["untested"]) / total * 100, 1) if total else 0.0
        counts["pass_rate"] = round(counts["passed"] / total * 100, 1) if total else 0.0
        return counts

    def to_dict(self, with_results=False):
        data = {"id": self.id, "code": f"R{self.id}", "project_id": self.project_id, "name": self.name,
                "description": self.description, "is_completed": self.is_completed,
                "created_at": self.created_at.isoformat(sep=" "), "stats": self.stats()}
        if with_results:
            data["results"] = [r.to_dict() for r in self.results]
        return data


class TestResult(db.Model):
    """Resultado de un caso dentro de una ejecución. Guarda una copia del título y la sección para que la
    ejecución conserve lo que realmente se probó aunque el caso cambie o se elimine."""
    __tablename__ = "test_results"
    __test__ = False

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id"))
    case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("test_cases.id", ondelete="SET NULL"))
    case_title: Mapped[str] = mapped_column(String(250))
    section_path: Mapped[str] = mapped_column(String(400), default="")
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    status: Mapped[str] = mapped_column(String(20), default="untested")
    comment: Mapped[str] = mapped_column(Text, default="")
    executed_by: Mapped[str] = mapped_column(String(80), default="")
    executed_at: Mapped[Optional[datetime]]

    run: Mapped[TestRun] = relationship(back_populates="results")
    case: Mapped[Optional[TestCase]] = relationship(back_populates="results")

    def to_dict(self):
        return {"id": self.id, "code": f"T{self.id}", "run_id": self.run_id, "case_id": self.case_id,
                "case_title": self.case_title, "section": self.section_path, "priority": self.priority,
                "status": self.status, "comment": self.comment, "executed_by": self.executed_by,
                "executed_at": self.executed_at.isoformat(sep=" ") if self.executed_at else None}
