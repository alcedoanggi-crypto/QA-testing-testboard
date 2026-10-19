# 3. Base de datos con SQLAlchemy

## ¿Qué es un ORM?

SQLAlchemy es un **ORM** (*Object-Relational Mapper*): cada tabla es una clase de Python y cada fila es un objeto.
En vez de escribir SQL a mano, la búsqueda se escribe así:

```python
db.session.scalars(db.select(TestCase).where(TestCase.priority == "High")).all()
```

y SQLAlchemy genera `SELECT * FROM test_cases WHERE priority = 'High'`.

## El diagrama

```
Project ──< Section (árbol: parent_id) ──< TestCase
   │                                          │
   └──< TestRun ──< TestResult >──────────────┘
```

`──<` significa "uno a muchos": un proyecto tiene muchas secciones.

## Estilo SQLAlchemy 2.x

```python
class Project(db.Model):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=now)

    sections: Mapped[list["Section"]] = relationship(back_populates="project", cascade="all, delete-orphan")
```

- `Mapped[int]` es una **anotación de tipo**: la columna es un entero obligatorio. `Mapped[Optional[int]]` la hace
  opcional (admite NULL).
- `relationship(...)` no es una columna. Es un atajo para navegar: `project.sections` devuelve la lista de secciones.
- `back_populates` conecta los dos lados: `section.project` y `project.sections` son la misma relación vista desde
  cada extremo.
- `cascade="all, delete-orphan"` hace que, al borrar un proyecto, también se borren sus secciones, casos y
  ejecuciones. Sin esto quedarían filas "huérfanas" apuntando a un proyecto que ya no existe.

## El árbol de secciones (relación consigo misma)

Una sección puede estar dentro de otra. Basta una columna que apunte a la **misma** tabla:

```python
class Section(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sections.id"))   # NULL = está en la raíz

    parent: Mapped[Optional["Section"]] = relationship(back_populates="children", remote_side=[id])
    children: Mapped[list["Section"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
```

`remote_side=[id]` le dice a SQLAlchemy cuál lado es el "padre". Como ambos extremos son la misma tabla, no lo
puede adivinar solo.

Con eso, la ruta completa de una carpeta se arma subiendo por los padres:

```python
@property
def path(self):
    names, node = [], self
    while node is not None:
        names.insert(0, node.name)
        node = node.parent
    return " › ".join(names)          # "Autenticación › Login"
```

Y para contar los casos de una carpeta **incluyendo sus subcarpetas** se usa **recursión**: una función que se llama
a sí misma para cada hijo.

```python
def total_cases(self):
    return len(self.cases) + sum(child.total_cases() for child in self.children)

def descendant_ids(self):
    ids = [self.id]
    for child in self.children:
        ids += child.descendant_ids()
    return ids
```

`descendant_ids()` sirve para el filtro "ver los casos de Autenticación": se buscan los casos cuyo `section_id`
esté en `[Autenticación, Login, Recuperar contraseña]`.

## Pasos como JSON

Los pasos de un caso son una lista de `{"action", "expected"}`. Una tabla `steps` aparte sería lo "más normalizado",
pero los pasos siempre se leen y guardan **junto** con su caso y nunca se buscan por separado. Por eso se guardan
en una columna JSON:

```python
steps: Mapped[list] = mapped_column(JSON, default=list)   # [{"action": "...", "expected": "..."}]
```

Ojo: es `default=list` (la función), no `default=[]`. Si se usara la lista, todas las filas compartirían el mismo objeto.

## La "foto" del caso en cada resultado

Este es el detalle de diseño más importante:

```python
class TestResult(db.Model):
    run_id: Mapped[int] = mapped_column(ForeignKey("test_runs.id"))
    case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("test_cases.id", ondelete="SET NULL"))
    case_title: Mapped[str] = mapped_column(String(250))      # ← copia
    section_path: Mapped[str] = mapped_column(String(400), default="")   # ← copia
    priority: Mapped[str] = mapped_column(String(20))         # ← copia
    status: Mapped[str] = mapped_column(String(20), default="untested")
```

**¿Por qué copiar el título si ya está en el caso?** Una ejecución es un **registro histórico**. Si en marzo
"Login válido" pasó, y en abril alguien renombra o borra ese caso, el reporte de marzo debe seguir diciendo lo que
se probó en marzo. Así funciona TestRail también.

- `case_id` es opcional y `ondelete="SET NULL"`: al borrar el caso, el resultado se conserva con `case_id = NULL`
  y la pantalla muestra "(caso eliminado)".
- Hay una prueba que verifica esto: `test_borrar_caso_conserva_historial`.

## Cálculos derivados: no se guardan, se calculan

El "último estado" de un caso y las estadísticas de una ejecución **no son columnas**. Se calculan cada vez:

```python
def stats(self):
    counts = {s: 0 for s in STATUSES}
    for r in self.results:
        counts[r.status] += 1
    total = len(self.results)
    counts["total"] = total
    counts["progress"] = round((total - counts["untested"]) / total * 100, 1) if total else 0.0
    counts["pass_rate"] = round(counts["passed"] / total * 100, 1) if total else 0.0
    return counts
```

Guardar el dato calculado en una columna obligaría a actualizarla cada vez que cambie un resultado, y tarde o
temprano se desincroniza. Calcularlo siempre da el valor correcto. Fíjate también en el `if total else 0.0`, que
evita dividir por cero cuando una ejecución no tiene casos.

- **Progreso** = ejecutados / total. Una ejecución con 6 de 8 resultados distintos de Untested va al 75 %.
- **Pass rate** = passed / total. 4 Passed de 8 da 50 %.

## `__test__ = False`

```python
class TestCase(db.Model):
    __test__ = False
```

pytest recoge como pruebas las clases que empiezan por `Test`. Así `TestCase`, `TestRun` y `TestResult` no se
confunden con clases de pruebas.

➡️ Siguiente: [4. Servicios y validación](04-servicios-y-validacion.md)
