try {
    const savedTheme = localStorage.getItem("t2speech-theme");
    document.documentElement.dataset.theme = savedTheme === "dark" ? "dark" : "light";
} catch {
    document.documentElement.dataset.theme = "light";
}

const themeSelect = document.querySelector("#theme-select");

if (themeSelect) {
    themeSelect.value = document.documentElement.dataset.theme || "dark";

    themeSelect.addEventListener("change", () => {
        const theme = themeSelect.value === "light" ? "light" : "dark";
        document.documentElement.dataset.theme = theme;

        try {
            localStorage.setItem("t2speech-theme", theme);
        } catch {
            // The selected theme still applies for this page when storage is unavailable.
        }
    });
}

const createDeckToggle = document.querySelector("#create-deck-toggle");
const createDeckPanel = document.querySelector("#create-deck-panel");
const closeCreateDeck = document.querySelector("#close-create-deck");
const cancelCreateDeck = document.querySelector("#cancel-create-deck");
const deckNameInput = document.querySelector("#name");

function setCreateDeckOpen(isOpen) {
    if (!createDeckToggle || !createDeckPanel) {
        return;
    }

    createDeckPanel.hidden = !isOpen;
    createDeckToggle.setAttribute("aria-expanded", String(isOpen));

    if (isOpen) {
        deckNameInput?.focus();
    } else {
        createDeckToggle.focus();
    }
}

createDeckToggle?.addEventListener("click", () => {
    setCreateDeckOpen(createDeckPanel.hidden);
});

closeCreateDeck?.addEventListener("click", () => setCreateDeckOpen(false));
cancelCreateDeck?.addEventListener("click", () => setCreateDeckOpen(false));

createDeckPanel?.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        event.preventDefault();
        setCreateDeckOpen(false);
    }
});

const deleteForms = document.querySelectorAll(".delete-deck-form");
const deleteDialog = document.querySelector("#delete-deck-dialog");
const skipCheckbox = document.querySelector("#skip-delete-confirmation");
const cancelButton = document.querySelector("#cancel-deck-delete");
const confirmButton = document.querySelector("#confirm-deck-delete");

let pendingDeleteForm = null;

if (deleteDialog && skipCheckbox && cancelButton && confirmButton) {
    deleteForms.forEach((form) => {
        form.addEventListener("submit", (event) => {
            let skipConfirmation = false;

            try {
                skipConfirmation = localStorage.getItem("skipDeckDeleteConfirmation") === "true";
            } catch {
                // Keep the confirmation enabled if browser storage is unavailable.
            }

            if (skipConfirmation) {
                return;
            }

            event.preventDefault();
            pendingDeleteForm = form;
            skipCheckbox.checked = false;
            deleteDialog.showModal();
        });
    });

    cancelButton.addEventListener("click", () => {
        pendingDeleteForm = null;
        deleteDialog.close();
    });

    deleteDialog.addEventListener("cancel", () => {
        pendingDeleteForm = null;
    });

    confirmButton.addEventListener("click", () => {
        if (pendingDeleteForm === null) {
            return;
        }

        if (skipCheckbox.checked) {
            try {
                localStorage.setItem("skipDeckDeleteConfirmation", "true");
            } catch {
                // The current deletion can proceed without saving this preference.
            }
        }

        const formToSubmit = pendingDeleteForm;
        pendingDeleteForm = null;

        deleteDialog.close();
        formToSubmit.submit();
    });
}
