/* Preserves production Study Mode interactions; all writes use tab storage. */
window.initializeDemoStudy = function (sessionId) {
    "use strict";
    const app = window.DemoApp;
    const $ = selector => document.querySelector(selector);
    const session = () => app.state().sessions[sessionId];
    const settings = () => session().settings;
    const panel = $("#study-settings");
    const trigger = $("#settings-trigger");
    let timer = null;
    let voiceTimer = null;
    let displayed = null;
    let lastSpeech = null;
    let speechGeneration = 0;
    let leaving = false;
    const invalidInputs = new Map();
    const speechAvailable = () => !!window.speechSynthesis && typeof window.SpeechSynthesisUtterance === "function";
    function clearTimers() {
        clearTimeout(timer); timer = null;
        clearTimeout(voiceTimer); voiceTimer = null;
    }
    function stopSpeech() {
        speechGeneration++;
        try { if (speechAvailable()) window.speechSynthesis.cancel(); } catch { /* Studying remains available. */ }
    }
    function speak(text, language) {
        stopSpeech();
        if (!speechAvailable()) { $("#audio-status").textContent = "Text-to-speech is unavailable. You can continue studying."; return; }
        try {
            const voices = window.speechSynthesis.getVoices();
            const wanted = language.toLowerCase();
            const base = wanted.split("-")[0];
            const voice = voices.find(item => item.localService && item.lang.toLowerCase() === wanted) ||
                voices.find(item => item.localService && item.lang.toLowerCase().split("-")[0] === base);
            if (!voice) {
                $("#audio-status").textContent = voices.length ? "No local voice is available for this language. You can continue studying." :
                    "Speech voices are still loading. Try Play front shortly; you can continue studying.";
                return;
            }
            const generation = speechGeneration;
            const utterance = new SpeechSynthesisUtterance(text.trim());
            utterance.voice = voice; utterance.lang = language; utterance.rate = settings().speech_rate;
            utterance.onerror = () => {
                if (generation === speechGeneration && !leaving) $("#audio-status").textContent = "Audio playback failed. You can continue studying.";
            };
            $("#audio-status").textContent = "";
            lastSpeech = {text, language};
            window.speechSynthesis.speak(utterance);
        } catch { $("#audio-status").textContent = "Audio playback failed. You can continue studying."; }
    }
    function autoSpeakFront(attempt = 0, revision = displayed.revision) {
        if (leaving || session().revision !== revision || session().revealed || settings().auto_speak === "off") return;
        try {
            if (speechAvailable() && !window.speechSynthesis.getVoices().length && attempt < 20) {
                voiceTimer = setTimeout(() => autoSpeakFront(attempt + 1, revision), 100);
                return;
            }
        } catch { /* speak() reports unavailable audio. */ }
        speak(displayed.card.front, displayed.card.front_language);
    }
    function scheduleReveal() {
        clearTimeout(timer); timer = null;
        if (!leaving && settings().auto_reveal && !session().revealed) {
            const revision = displayed.revision;
            // Browsers clamp very large timeout values; chunk long delays without revealing early.
            const deadline = Date.now() + settings().reveal_delay_seconds * 1000;
            function tick() {
                if (leaving || session().revision !== revision || session().revealed) return;
                const remaining = deadline - Date.now();
                if (remaining <= 0) reveal();
                else timer = setTimeout(tick, Math.min(remaining, 2147483647));
            }
            tick();
        }
    }
    function showAnswer() {
        const revealed = session().revealed;
        $("#answer").hidden = !revealed;
        $("#rating-actions").hidden = !revealed;
        $("#reveal-button").hidden = revealed;
        $(".study-reveal-area").hidden = revealed;
        $("#revealed-input").value = String(revealed);
        document.querySelectorAll('[name="rating"]').forEach(button => { button.disabled = !revealed; });
    }
    function render(focus = false) {
        clearTimers(); stopSpeech(); lastSpeech = null;
        app.status("");
        const info = DemoSession.view(session());
        if (session().status === "completed") { leaving = true; location.replace(app.completeUrl(sessionId)); return; }
        displayed = {card: info.current_card, revision: session().revision};
        $("#good-count").textContent = info.good_count;
        $("#total-count").textContent = info.total_cards;
        $("#progress-percentage").textContent = `${Math.round(info.progress * 100)}%`;
        $("#study-progress").value = info.good_count;
        $("#study-progress").max = info.total_cards;
        $("#study-progress").textContent = `${Math.round(info.progress * 100)}%`;
        $("#remaining-count").textContent = `${session().pending.length} remaining`;
        $("#front-text").textContent = displayed.card.front;
        $("#back-text").textContent = displayed.card.back;
        $("#front-text").lang = displayed.card.front_language;
        $("#back-text").lang = displayed.card.back_language;
        $("#audio-status").textContent = "";
        showAnswer();
        if (focus) $("#front-text").focus({preventScroll: true});
        scheduleReveal();
        autoSpeakFront();
    }
    function reveal() {
        if (session().revealed || leaving) return;
        try {
            app.transact(next => DemoSession.reveal(next.sessions[sessionId], displayed.revision));
            app.status("");
            clearTimers(); showAnswer(); $("#answer").focus({preventScroll: true});
            if (settings().auto_speak === "front_back") speak(displayed.card.back, displayed.card.back_language);
        } catch { app.status("Could not save this session in browser tab storage. Free storage or enable it, then try again."); }
    }
    $("#reveal-button").addEventListener("click", reveal);
    $("#speak-front").addEventListener("click", () => speak(displayed.card.front, displayed.card.front_language));
    $("#speak-back").addEventListener("click", () => {
        if (session().revealed) speak(displayed.card.back, displayed.card.back_language);
    });
    $("#rating-actions").addEventListener("submit", event => {
        event.preventDefault();
        if (leaving || !session().revealed || !event.submitter) return;
        const expected = displayed;
        try {
            const accepted = app.transact(next => DemoSession.rate(next.sessions[sessionId], event.submitter.value,
                expected.card.id, expected.revision));
            if (accepted) render(true);
        } catch { app.status("Could not save your rating in browser tab storage. Try again after enabling storage or freeing space."); }
    });
    function closeSettings(restoreFocus = false) {
        if (panel.hidden) return;
        const within = panel.contains(document.activeElement);
        panel.hidden = true; trigger.setAttribute("aria-expanded", "false");
        if (restoreFocus || within) trigger.focus();
    }
    trigger.addEventListener("click", () => {
        if (!panel.hidden) closeSettings(true);
        else { panel.hidden = false; trigger.setAttribute("aria-expanded", "true"); $("#auto-speak").focus(); }
    });
    $("#settings-close").addEventListener("click", () => closeSettings(true));
    document.addEventListener("pointerdown", event => {
        if (!panel.hidden && !$("#settings-anchor").contains(event.target)) closeSettings();
    });
    panel.addEventListener("keydown", event => {
        if (event.key !== "Tab") return;
        const controls = [...panel.querySelectorAll("button, input, select")].filter(element => !element.disabled && element.getClientRects().length);
        const first = controls[0], last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    function saveStatus(message) {
        const invalid = [...invalidInputs.entries()].find(([property]) => property !== "reveal_delay_seconds" || settings().auto_reveal);
        if (invalid && message === "Saved in this tab") message = invalid[1];
        $("#settings-save-status").textContent = message;
        $("#settings-save-inline").textContent = message;
        $("#settings-save-status").dataset.state = invalid ? "invalid" : "";
        $("#settings-save-inline").dataset.state = invalid ? "invalid" : "";
    }
    function changeSetting(property, value) {
        try {
            app.transact(next => DemoSession.updateSettings(next.sessions[sessionId], {[property]: value}));
            saveStatus("Saved in this tab");
            $("#reveal-delay-field").hidden = !settings().auto_reveal;
            if (property === "auto_reveal" || property === "reveal_delay_seconds") scheduleReveal();
            // Production convention: changing auto-speak takes effect on the next face/card.
            if (property === "auto_speak" && value === "off") { clearTimeout(voiceTimer); stopSpeech(); }
        } catch { saveStatus("Could not save in browser tab storage. Try again."); }
    }
    $("#auto-speak").value = settings().auto_speak;
    $("#speech-rate").value = settings().speech_rate;
    $("#auto-reveal").checked = settings().auto_reveal;
    $("#reveal-delay").value = settings().reveal_delay_seconds;
    $("#reveal-delay-field").hidden = !settings().auto_reveal;
    $("#study-settings-form").addEventListener("submit", event => event.preventDefault());
    $("#auto-speak").addEventListener("change", event => changeSetting("auto_speak", event.target.value));
    $("#auto-reveal").addEventListener("change", event => changeSetting("auto_reveal", event.target.checked));
    for (const [id, property, message] of [
        ["#speech-rate", "speech_rate", "Speech rate must be between 0.1 and 10."],
        ["#reveal-delay", "reveal_delay_seconds", "Reveal delay must be a whole number of at least 1."]
    ]) {
        $(id).addEventListener("input", event => {
            const input = event.target;
            if (!input.validity.valid || input.value === "" || !Number.isFinite(Number(input.value)) ||
                (property === "reveal_delay_seconds" && !Number.isSafeInteger(Number(input.value)))) {
                invalidInputs.set(property, message); saveStatus(message); return;
            }
            invalidInputs.delete(property);
            changeSetting(property, Number(input.value));
        });
    }
    const cleanup = () => { leaving = true; clearTimers(); stopSpeech(); };
    window.addEventListener("pagehide", cleanup);
    document.addEventListener("keydown", event => {
        if (event.repeat || event.ctrlKey || event.altKey || event.metaKey || leaving) return;
        if (event.key === "Escape") {
            if (!panel.hidden) { event.preventDefault(); closeSettings(true); return; }
            if (event.target.closest('input, textarea, select, [contenteditable="true"]')) return;
            event.preventDefault(); cleanup(); location.assign(app.deckUrl(session().deck_id)); return;
        }
        if (!panel.hidden || event.target.closest('input, textarea, select, button, a, summary, [contenteditable="true"], [role="dialog"]')) return;
        if (event.code === "Space" && !session().revealed) { event.preventDefault(); reveal(); }
        else if (event.key.toLowerCase() === "r" && lastSpeech) { event.preventDefault(); speak(lastSpeech.text, lastSpeech.language); }
        else if (session().revealed && ["1", "2"].includes(event.key)) {
            event.preventDefault(); $(`[name="rating"][value="${event.key === "1" ? "again" : "good"}"]`).click();
        }
    });
    render();
};
