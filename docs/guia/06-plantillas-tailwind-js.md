# 6. Plantillas, Tailwind y JavaScript

## Jinja: herencia de plantillas

`templates/base.html` tiene lo común: el `<head>`, el encabezado `#1E2D40` con el menú, los mensajes flash y el
`<script>`. Cada pantalla **hereda** de ella y solo rellena el hueco `content`:

```jinja
{% extends "base.html" %}
{% block title %}Proyectos{% endblock %}
{% block content %}
    <h1 class="text-2xl font-bold">Proyectos</h1>
    ...
{% endblock %}
```

### Menú con la opción activa

```jinja
{% set nav = [('views.dashboard', 'Dashboard', ['views.dashboard']),
              ('views.cases', 'Casos de Prueba', ['views.cases', 'views.cases_new', 'views.cases_detail', ...]), ...] %}
{% for endpoint, label, active in nav %}
<a href="{{ url_for(endpoint) }}" class="nav-link {% if request.endpoint in active %}active{% endif %}">{{ label }}</a>
{% endfor %}
```

`request.endpoint` es el nombre de la ruta actual. La pestaña "Casos de Prueba" se ilumina también en las páginas de
nuevo caso y detalle.

## Macros: componentes reutilizables

`templates/macros.html` define piezas que se repiten, como la etiqueta de estado:

```jinja
{% macro status_badge(status) -%}
{%- set icons = {'passed': '✓', 'failed': '✕', 'blocked': '⊘', 'untested': '○'} -%}
{%- set classes = {'passed': 'badge-passed', 'failed': 'badge-failed', 'blocked': 'badge-blocked', 'untested': 'badge-untested'} -%}
<span class="badge {{ classes[status] }}"><span aria-hidden="true">{{ icons[status] }}</span>{{ status|capitalize }}</span>
{%- endmacro %}
```

Y se usan así: `{% from "macros.html" import status_badge %}` … `{{ status_badge(r.status) }}`.

**Cada estado lleva color, ícono y texto.** Alrededor de 1 de cada 12 hombres distingue mal el rojo del verde. Si el
estado fuera solo de color, no podrían leerlo.

## Tailwind CSS

Tailwind es CSS por **clases utilitarias**: en lugar de escribir `.tarjeta { padding: 20px; border-radius: 12px }`,
se combinan clases en el HTML: `class="p-5 rounded-xl"`.

### Configuración (`static/src/tailwind.config.js`)

```js
module.exports = {
  content: ["./templates/**/*.html", "./static/js/**/*.js"],   // dónde buscar clases usadas
  theme: { extend: { colors: {
    navy:  { DEFAULT: "#1E2D40", 700: "#2A3D55", 900: "#192734" },   // encabezado pedido
    mint:  { DEFAULT: "#2ECC71", ... },                              // botones principales
    passed:   { DEFAULT: "#1A7F4B", soft: "#E3F4EA" },
    failed:   { DEFAULT: "#D92D45", soft: "#FCE8EB" },
    blocked:  { DEFAULT: "#F0BE2C", soft: "#FDF4D9", ink: "#7A5A00" },
    untested: { DEFAULT: "#AEB8C6", soft: "#EEF1F5", ink: "#475569" },
  } } },
};
```

Al definir el color `passed`, Tailwind crea clases como `bg-passed`, `text-passed` y `bg-passed-soft`.

### Componentes propios (`static/src/input.css`)

Las combinaciones repetidas se agrupan con `@apply`:

```css
@layer components {
  .btn         { @apply inline-flex items-center justify-center gap-1.5 rounded-md border ... ; }
  .btn-primary { @apply border-mint bg-mint text-navy hover:border-mint-600 hover:bg-mint-600; }
  .badge-passed { @apply bg-passed-soft text-passed; }
  ...
}
```

### Compilar

El navegador no entiende `@apply` ni `@tailwind`. Hay que **compilar** a CSS normal:

```powershell
npx tailwindcss@3 -c static/src/tailwind.config.js -i static/src/input.css -o static/css/tailwind.css --minify
```

El compilador recorre los archivos de `content`, encuentra qué clases se usan y genera **solo esas**. Así el CSS
final pesa ~19 KB en vez de varios MB.

> **Error real encontrado en el desarrollo:** la primera versión del macro escribía `class="badge badge-{{ status }}"`.
> En las capturas, las etiquetas salían **sin color**. El compilador lee el texto de las plantillas y nunca vio
> `badge-passed` escrito completo, solo `badge-{{ status }}`, así que no generó esas clases.
> **Lección:** con Tailwind, las clases siempre se escriben completas. Para elegirlas de forma dinámica se usa un
> diccionario con los nombres enteros, como en el macro de arriba.

## El diseño de la vista de casos

```
┌───────────────┬────────────────────────────────────────────┐
│ SECCIONES     │  Casos de Prueba            [+ Nuevo caso] │
│ 📁 Todas    8 │  [buscar…] [prioridad ▾] [Filtrar]         │
│ 📁 Autent.  4 │  ┌──────────────────────────────────────┐  │
│   📁 Login  3 │  │ ID │ Título │ Sección │ Prioridad │…│  │
│ ...           │  └──────────────────────────────────────┘  │
│ [Nueva secc.] │                                            │
└───────────────┴────────────────────────────────────────────┘
```

Es una grilla de dos columnas: `grid lg:grid-cols-[270px_minmax(0,1fr)]`. El prefijo `lg:` aplica solo en pantallas
grandes; en el celular, la barra lateral queda arriba. `minmax(0,1fr)` evita que una tabla ancha empuje la página
fuera de la pantalla.

La sangría del árbol sale de la profundidad que calcula `section_tree()`:

```jinja
{% for section, depth in tree %}
  <a style="padding-left: {{ 8 + depth * 16 }}px" ...>📁 {{ section.name }}</a>
{% endfor %}
```

## La barra de progreso apilada

```jinja
{% macro progress_bar(stats, height='h-2.5') -%}
<div class="flex {{ height }} gap-0.5 overflow-hidden rounded-full bg-untested-soft" role="img" aria-label="Passed 4, Failed 1, ...">
    {% for key, color in [('passed', 'bg-passed'), ('failed', 'bg-failed'), ('blocked', 'bg-blocked')] %}
    {% if stats.total and stats[key] %}<span class="{{ color }}" style="width: {{ stats[key] / stats.total * 100 }}%"></span>{% endif %}
    {% endfor %}
</div>
{%- endmacro %}
```

Cada tramo mide su porcentaje del total. Lo que queda sin pintar, el fondo gris, son los Untested. `gap-0.5` deja una
línea fina entre colores, y `aria-label` describe la barra para lectores de pantalla.

## JavaScript mínimo (`static/js/app.js`)

**Todo funciona sin JavaScript**, porque son formularios normales. El JS solo mejora la experiencia, y cada
comportamiento se activa con un atributo `data-*` en el HTML:

| Atributo | Qué hace |
|---|---|
| `data-autosubmit` | Envía el formulario al cambiar el `<select>` (selector de proyecto, filtro de prioridad) |
| `data-confirm="¿…?"` | Pide confirmación antes de eliminar |
| `data-dismiss` | Cierra un mensaje flash |
| `data-case-picker-toggle` | Muestra la lista de casos si se elige "casos específicos" |
| `data-result-form` | Avisa antes de enviar Failed/Blocked sin comentario |

```js
document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
        if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
});
```

`event.preventDefault()` cancela el envío. La validación del comentario existe **dos veces**: en JS, para dar una
respuesta inmediata, y en el servidor, por seguridad. Validar solo en el navegador nunca es suficiente, porque
cualquiera puede llamar a la API directamente.

➡️ Siguiente: [7. Pruebas con pytest](07-pruebas-pytest.md)
