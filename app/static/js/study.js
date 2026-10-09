
const revealButton = document.getElementById("reveal-button");
const answer = document.getElementById("answer");
const ratingActions = document.getElementById("rating-actions");
const revealedInput = document.getElementById("revealed-input");

const againButton = document.querySelector(
    'button[name="rating"][value="again"]'
);

const goodButton = document.querySelector(
    'button[name="rating"][value="good"]'
);

revealButton.addEventListener("click", () => {
    answer.hidden = false;
    revealButton.hidden = true;
    ratingActions.hidden = false;
    revealedInput.value = "true";
});

document.addEventListener("keydown", (event) => {
    if (event.repeat || event.ctrlKey || event.altKey || event.metaKey) {
        return;
    }

    const isTyping =
        event.target instanceof HTMLElement &&
        event.target.closest(
            'input, textarea, select, [contenteditable="true"]'
        );

    if (isTyping) {
        return;
    }

    if (event.code === "Space" && answer.hidden) {
        event.preventDefault();
        revealButton.click();
        return;
    }

    if (event.key === "Escape") {
        window.location.href = document.body.dataset.deckUrl;
        return;
    }

    if (answer.hidden) {
        return;
    }

    if (event.key === "1") {
        againButton.click();
    } else if (event.key === "2") {
        goodButton.click();
    }
});
