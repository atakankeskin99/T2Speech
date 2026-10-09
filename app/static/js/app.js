
const deleteForms = document.querySelectorAll(".delete-deck-form");
const deleteDialog = document.querySelector("#delete-deck-dialog");
const skipCheckbox = document.querySelector("#skip-delete-confirmation");
const cancelButton = document.querySelector("#cancel-deck-delete");
const confirmButton = document.querySelector("#confirm-deck-delete");

let pendingDeleteForm = null;

deleteForms.forEach((form) => {
    form.addEventListener("submit", (event) => {
        const skipConfirmation =
            localStorage.getItem("skipDeckDeleteConfirmation") === "true";

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

confirmButton.addEventListener("click", () => {
    if (pendingDeleteForm === null) {
        return;
    }

    if (skipCheckbox.checked) {
        localStorage.setItem("skipDeckDeleteConfirmation", "true");
    }

    const formToSubmit = pendingDeleteForm;
    pendingDeleteForm = null;

    deleteDialog.close();
    formToSubmit.submit();
});