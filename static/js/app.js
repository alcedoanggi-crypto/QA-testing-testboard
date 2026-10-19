// QA TestBoard - comportamiento mínimo del lado del cliente.
// Todo funciona sin JavaScript (formularios normales); esto solo mejora la experiencia.
// Se usan atributos data-* para que el HTML declare qué comportamiento necesita.

document.addEventListener("DOMContentLoaded", () => {
    // <select data-autosubmit>: envía su formulario al cambiar (selector de proyecto, filtro de prioridad).
    document.querySelectorAll("[data-autosubmit]").forEach((el) => {
        el.addEventListener("change", () => el.form && el.form.submit());
    });

    // <form data-confirm="¿Seguro?">: pide confirmación antes de acciones destructivas.
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.confirm)) event.preventDefault();
        });
    });

    // Botón × de los mensajes flash.
    document.querySelectorAll("[data-dismiss]").forEach((btn) => {
        btn.addEventListener("click", () => btn.closest("[data-flash]").remove());
    });

    // Nueva ejecución: mostrar la lista de casos solo cuando se eligen "casos específicos".
    const picker = document.getElementById("case-picker");
    const toggles = document.querySelectorAll("[data-case-picker-toggle]");
    const syncPicker = () => {
        const chosen = document.querySelector("[data-case-picker-toggle]:checked");
        picker.classList.toggle("hidden", !chosen || chosen.value !== "0");
    };
    if (picker) {
        toggles.forEach((radio) => radio.addEventListener("change", syncPicker));
        syncPicker();
    }

    // Detalle de ejecución: avisar antes de enviar Failed/Blocked sin comentario
    // (el servidor también lo valida; esto evita el viaje de ida y vuelta).
    document.querySelectorAll("form[data-result-form]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const status = form.elements.status.value;
            const comment = form.elements.comment;
            if ((status === "failed" || status === "blocked") && !comment.value.trim()) {
                event.preventDefault();
                comment.classList.add("!border-failed", "!ring-failed/30");
                comment.focus();
                comment.placeholder = "Escribe por qué falló o está bloqueado";
            }
        });
    });
});
