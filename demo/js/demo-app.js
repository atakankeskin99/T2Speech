(async function () {
    "use strict";
    const $ = selector => document.querySelector(selector);
    const params = new URLSearchParams(location.search);
    const page = document.body.dataset.page;
    // All pages must discard stale in-memory data when restored through browser Back.
    window.addEventListener("pageshow", event => { if (event.persisted) location.reload(); });
    let state;
    let decks;
    const escape = text => String(text).replace(/[&<>"']/g, character =>
        ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[character]);
    const deckUrl = id => `deck.html?deck=${encodeURIComponent(id)}`;
    const setupUrl = id => `study_setup.html?deck=${encodeURIComponent(id)}`;
    const studyUrl = id => `study.html?session=${encodeURIComponent(id)}`;
    const completeUrl = id => `study_complete.html?session=${encodeURIComponent(id)}`;
    const status = message => { $("#demo-status").textContent = message; };
    function transact(change) {
        const next = JSON.parse(JSON.stringify(state));
        const result = change(next);
        DemoStorage.save(next); // Commit in memory only after tab storage accepts the write.
        state = next;
        return result;
    }
    function sessionPanel(session) {
        const info = DemoSession.view(session);
        return `<section class="study-resume-panel" aria-labelledby="resume-heading">
            <div class="study-resume-heading"><div><p class="study-lifecycle-eyebrow">IN PROGRESS</p>
            <h2 id="resume-heading">Continue your session</h2></div>
            <span class="study-resume-percentage">${Math.round(info.progress * 100)}%</span></div>
            <p class="study-resume-summary">${info.good_count} of ${info.total_cards} completed · ${session.pending.length} remaining</p>
            <progress class="study-progress study-resume-progress" value="${info.good_count}" max="${info.total_cards}" aria-label="Current session progress"></progress>
            <div class="study-flow-actions"><a class="button-primary" href="${studyUrl(session.id)}">Resume session</a></div></section>`;
    }
    try {
        const response = await fetch("data/sample-decks.json");
        if (!response.ok) throw new Error("Sample decks could not be loaded. Serve the demo over HTTP and try again.");
        decks = await response.json();
        state = DemoStorage.load();
        DemoStorage.save(state); // Detect disabled or full storage before allowing a session to start.
        window.DemoApp = {state: () => state, transact, status, deckUrl, setupUrl, studyUrl, completeUrl};
        $("#demo-loading").hidden = true;
        if (page === "library") {
            $("#deck-count").textContent = decks.length;
            $("#deck-list").innerHTML = decks.map(deck => `<li class="deck-row"><div class="deck-info">
                <a class="deck-title" href="${deckUrl(deck.id)}">${escape(deck.name)}</a>
                <p class="deck-description">${escape(deck.description)}</p></div>
                <span class="deck-count">${deck.cards.length} cards</span></li>`).join("");
            $("#page-content").hidden = false;
            return;
        }
        const session = params.has("session") ? state.sessions[params.get("session")] : null;
        const deck = decks.find(item => item.id === (session?.deck_id || params.get("deck")));
        if (!deck) throw new Error("This sample deck or tab session is unavailable. Return to the Library to begin.");
        document.title = `${deck.name} · T2Speech demo`;
        document.querySelectorAll("[data-deck-link]").forEach(link => { link.href = deckUrl(deck.id); });
        document.querySelectorAll("[data-setup-link]").forEach(link => { link.href = setupUrl(deck.id); });
        document.querySelectorAll("[data-deck-name]").forEach(element => { element.textContent = deck.name; });
        if (page === "deck") {
            const active = DemoSession.activeSession(state, deck.id);
            $("#deck-description").textContent = deck.description;
            $("#deck-languages").textContent = `Front: ${deck.front_language} · Back: ${deck.back_language} · Sample cards are read-only.`;
            $("#deck-study-content").innerHTML = active ? sessionPanel(active) +
                `<a class="button-secondary" href="${setupUrl(deck.id)}">Start new session</a>` :
                `<p class="deck-study-description">Practice your cards at your own pace. Choose a card order and begin a new session.</p>
                 <div class="deck-study-actions"><a class="button-primary" href="${setupUrl(deck.id)}">Study this deck</a></div>`;
            $("#card-list").innerHTML = deck.cards.map(card => `<li class="card-list-item"><div class="card-content">
                <p class="card-front" lang="${escape(deck.front_language)}">${escape(card.front)}</p>
                <p class="card-back" lang="${escape(deck.back_language)}">${escape(card.back)}</p></div></li>`).join("");
        } else if (page === "setup") {
            $("#card-count").textContent = deck.cards.length;
            const active = DemoSession.activeSession(state, deck.id);
            if (active) $("#resume-container").innerHTML = sessionPanel(active);
            $("#start-session").disabled = !deck.cards.length;
            let confirmationId = null;
            let confirmedOptions = null;
            function start(options, replacement = null) {
                const created = transact(next => DemoSession.startSession(next, deck, options, replacement));
                location.assign(studyUrl(created.id));
            }
            $("#study-setup-form").addEventListener("submit", event => {
                event.preventDefault();
                const options = {shuffle: $("#shuffle").checked, reverse: $("#reverse").checked};
                const current = DemoSession.activeSession(state, deck.id);
                if (!current) {
                    try { start(options); } catch (error) { status(error.message); }
                    return;
                }
                confirmationId = current.id;
                confirmedOptions = options;
                const info = DemoSession.view(current);
                $("#replace-progress").textContent = `${info.good_count} of ${info.total_cards} completed`;
                $("#replace-options").textContent = `Shuffle: ${options.shuffle ? "On" : "Off"} · Reverse: ${options.reverse ? "On" : "Off"}`;
                $("#setup-panels").hidden = true;
                $("#replace-panel").hidden = false;
                $("#cancel-replace").focus();
            });
            const cancel = () => {
                confirmationId = null;
                confirmedOptions = null;
                $("#replace-panel").hidden = true;
                $("#setup-panels").hidden = false;
                $("#start-session").focus();
            };
            $("#cancel-replace").addEventListener("click", cancel);
            $("#confirm-replace").addEventListener("click", () => {
                if (!confirmationId) return;
                try { start(confirmedOptions, confirmationId); } catch (error) { status(error.message); }
            });
            document.addEventListener("keydown", event => {
                if (event.key === "Escape" && !$("#replace-panel").hidden) { event.preventDefault(); cancel(); }
            });
        } else if (page === "study") {
            if (!session) throw new Error("This session is unavailable in this browser tab.");
            if (session.status === "completed") { location.replace(completeUrl(session.id)); return; }
            if (session.status !== "active") throw new Error("This session was abandoned when it was replaced. Return to the deck to resume the new session.");
            window.initializeDemoStudy(session.id);
        } else if (page === "complete") {
            if (!session || session.status !== "completed") {
                throw new Error(session?.status === "abandoned" ? "This session was abandoned, not completed. Return to the deck." :
                    "This session has not been completed. Return to the deck to resume studying.");
            }
            const info = DemoSession.view(session);
            $("#completed-count").textContent = info.good_count;
            $("#total-count").textContent = info.total_cards;
            $("#completion-progress").value = info.good_count;
            $("#completion-progress").max = info.total_cards;
            document.addEventListener("keydown", event => {
                if (event.key === "Escape" && !event.target.closest("input, textarea, select, [contenteditable]")) location.assign(deckUrl(deck.id));
            });
        }
        $("#page-content").hidden = false;
    } catch (error) {
        $("#demo-loading").hidden = true;
        status(`${error.message} If browser storage is blocked, enable session storage to use the demo.`);
        $("#recovery").hidden = false;
        $("#reset-demo").addEventListener("click", () => {
            if (!window.confirm("Clear all demo sessions in this tab?")) return;
            try { DemoStorage.reset(); location.assign("index.html"); }
            catch { status("Browser session storage is unavailable. Enable it and reload the demo."); }
        });
    }
})();
