// Study Mode — reveal, speech, shortcuts and session-local settings.
// Phase 2 keeps the existing Web Speech API and session flow intact.
const revealButton = document.getElementById("reveal-button");
const answer = document.getElementById("answer");
const ratingActions = document.getElementById("rating-actions");
const revealedInput = document.getElementById("revealed-input");
const againButton = document.querySelector('button[name="rating"][value="again"]');
const goodButton = document.querySelector('button[name="rating"][value="good"]');

const settingsTrigger = document.getElementById("settings-trigger");
const settingsPanel = document.getElementById("study-settings");
const settingsAnchor = document.getElementById("settings-anchor");
const settingsClose = document.getElementById("settings-close");
const settingsForm = document.getElementById("study-settings-form");
const settingsSaveStatus = document.getElementById("settings-save-status");
const settingsRetry = document.getElementById("settings-retry");
const settingsInlineStatus = document.getElementById("settings-save-inline");
const autoSpeakSelect = document.getElementById("auto-speak");
const speechRateInput = document.getElementById("speech-rate");
const autoRevealCheckbox = document.getElementById("auto-reveal");
const revealDelayInput = document.getElementById("reveal-delay");
const revealDelayField = document.getElementById("reveal-delay-field");

const speakFrontButton = document.getElementById("speak-front");
const speakBackButton = document.getElementById("speak-back");
const frontText = document.getElementById("front-text");
const backText = document.getElementById("back-text");
const audioStatus = document.getElementById("audio-status");
const deckUrl = document.body.dataset.deckUrl;

const speechAvailable = "speechSynthesis" in window;
let availableVoices = speechAvailable ? window.speechSynthesis.getVoices() : [];
let lastSpeech = null;
let autoRevealTimer = null;
let initialAutoSpeakStarted = false;
let voiceWaitAttempts = 0;
let ratingSubmitted = false;
let ratingSubmissionAllowed = false;

// Numeric fields use a committed, valid value while the user is typing.
// Every POST sends all four settings, so serialize requests to avoid stale writes.
const currentSettings = {
    auto_reveal: autoRevealCheckbox.checked,
    reveal_delay_seconds: Number(revealDelayInput.value),
    auto_speak: autoSpeakSelect.value,
    speech_rate: Number(speechRateInput.value)
};
let settingsRevision = 0;
let savedRevision = 0;
let lastFailedRevision = -1;
let saveInFlight = null;
let numericSaveTimer = null;
let navigatingAway = false;
const invalidNumericInputs = new Map();

function setAudioStatus(message) {
    audioStatus.textContent = message;
}

function stopSpeech() {
    if (speechAvailable) {
        window.speechSynthesis.cancel();
    }
}

function findLocalVoice(language) {
    const wantedLanguage = language.toLowerCase();
    const baseLanguage = wantedLanguage.split("-")[0];
    return (
        availableVoices.find(voice =>
            voice.localService && voice.lang.toLowerCase() === wantedLanguage
        ) ||
        availableVoices.find(voice =>
            voice.localService &&
            voice.lang.toLowerCase().split("-")[0] === baseLanguage
        )
    );
}

function clearAutoRevealTimer() {
    if (autoRevealTimer !== null) {
        window.clearTimeout(autoRevealTimer);
        autoRevealTimer = null;
    }
}

function scheduleAutoReveal() {
    clearAutoRevealTimer();
    if (!currentSettings.auto_reveal || !answer.hidden) {
        return;
    }
    const delaySeconds = currentSettings.reveal_delay_seconds;
    if (!Number.isInteger(delaySeconds) || delaySeconds < 1) {
        return;
    }
    autoRevealTimer = window.setTimeout(() => {
        autoRevealTimer = null;
        if (answer.hidden) {
            revealButton.click();
        }
    }, delaySeconds * 1000);
}

function speakText(text, language) {
    if (!speechAvailable) {
        setAudioStatus("Text-to-speech is unavailable. You can continue studying.");
        return;
    }
    availableVoices = window.speechSynthesis.getVoices();
    if (availableVoices.length === 0) {
        setAudioStatus("Speech voices are still loading. Please try again shortly.");
        return;
    }
    const voice = findLocalVoice(language);
    if (!voice) {
        setAudioStatus("No local voice is available for this language. You can continue studying.");
        return;
    }
    stopSpeech();
    setAudioStatus("");
    const utterance = new SpeechSynthesisUtterance(text.trim());
    utterance.voice = voice;
    utterance.lang = language;
    utterance.rate = currentSettings.speech_rate;
    utterance.onerror = () => {
        setAudioStatus("Audio playback failed. You can continue studying.");
    };
    lastSpeech = { text, language };
    window.speechSynthesis.speak(utterance);
}

function tryInitialAutoSpeak() {
    if (initialAutoSpeakStarted || currentSettings.auto_speak === "off") {
        return;
    }
    availableVoices = window.speechSynthesis.getVoices();
    if (availableVoices.length === 0 && voiceWaitAttempts < 20) {
        voiceWaitAttempts += 1;
        window.setTimeout(tryInitialAutoSpeak, 100);
        return;
    }
    initialAutoSpeakStarted = true;
    speakText(frontText.textContent, speakFrontButton.dataset.language);
}

if (speechAvailable) {
    window.speechSynthesis.addEventListener("voiceschanged", () => {
        availableVoices = window.speechSynthesis.getVoices();
        tryInitialAutoSpeak();
    });
}

revealButton.addEventListener("click", () => {
    clearAutoRevealTimer();
    answer.hidden = false;
    revealButton.hidden = true;
    revealButton.parentElement.hidden = true;
    ratingActions.hidden = false;
    revealedInput.value = "true";
    answer.focus({ preventScroll: true });
    if (currentSettings.auto_speak === "front_back") {
        speakText(backText.textContent, speakBackButton.dataset.language);
    }
});

speakFrontButton.addEventListener("click", () => {
    speakText(frontText.textContent, speakFrontButton.dataset.language);
});
speakBackButton.addEventListener("click", () => {
    speakText(backText.textContent, speakBackButton.dataset.language);
});

function isSettingsOpen() {
    return !settingsPanel.hidden;
}

function openSettings() {
    settingsPanel.hidden = false;
    settingsTrigger.setAttribute("aria-expanded", "true");
    autoSpeakSelect.focus();
}

function closeSettings(restoreFocus = false) {
    if (!isSettingsOpen()) {
        return;
    }
    const focusedWithin = settingsPanel.contains(document.activeElement);
    settingsPanel.hidden = true;
    settingsTrigger.setAttribute("aria-expanded", "false");
    if (restoreFocus || focusedWithin) {
        settingsTrigger.focus();
    }
}

settingsTrigger.addEventListener("click", () => {
    if (isSettingsOpen()) {
        closeSettings(true);
    } else {
        openSettings();
    }
});
settingsClose.addEventListener("click", () => closeSettings(true));

document.addEventListener("pointerdown", event => {
    if (isSettingsOpen() && !settingsAnchor.contains(event.target)) {
        // Do not steal the external element's focus when it is clicked.
        closeSettings(false);
    }
});

// Keep keyboard navigation inside the non-modal settings dialog until it closes.
settingsPanel.addEventListener("keydown", event => {
    if (event.key !== "Tab") {
        return;
    }
    const controls = Array.from(settingsPanel.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
    )).filter(element => element.getClientRects().length > 0);
    if (controls.length === 0) {
        return;
    }
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
    }
});

function setSaveStatus(message, state = "") {
    const visibleInputError = [...invalidNumericInputs.entries()].find(
        ([input]) => input !== revealDelayInput || currentSettings.auto_reveal
    );
    if (visibleInputError && state !== "error") {
        message = visibleInputError[1];
        state = "invalid";
    }
    settingsSaveStatus.textContent = message;
    settingsSaveStatus.dataset.state = state;
    settingsInlineStatus.textContent = message;
    settingsInlineStatus.dataset.state = state;
    settingsRetry.hidden = state !== "error";
}

function showDelayField() {
    revealDelayField.hidden = !currentSettings.auto_reveal;
}

function encodeSettings(snapshot) {
    const data = new URLSearchParams();
    if (snapshot.auto_reveal) {
        data.set("auto_reveal", "true");
    }
    data.set("reveal_delay_seconds", String(snapshot.reveal_delay_seconds));
    data.set("auto_speak", snapshot.auto_speak);
    data.set("speech_rate", String(snapshot.speech_rate));
    return data;
}

function parseSaveError(response, body) {
    if (body && typeof body.detail === "string") {
        return body.detail;
    }
    return `Server returned ${response.status}.`;
}

async function sendLatestSettings() {
    if (saveInFlight) {
        return saveInFlight;
    }
    if (numericSaveTimer !== null) {
        clearTimeout(numericSaveTimer);
        numericSaveTimer = null;
    }
    if (savedRevision >= settingsRevision) {
        return;
    }
    const revision = settingsRevision;
    const snapshot = { ...currentSettings };
    setSaveStatus("Saving…", "saving");

    saveInFlight = (async () => {
        try {
            const response = await fetch(settingsForm.action, {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                credentials: "same-origin",
                keepalive: true,
                body: encodeSettings(snapshot)
            });
            const body = await response.json().catch(() => null);
            if (!response.ok || body?.saved !== true) {
                throw new Error(parseSaveError(response, body));
            }
            savedRevision = revision;
            if (settingsRevision === revision) {
                setSaveStatus("Saved", "saved");
            }
        } catch (error) {
            if (settingsRevision === revision) {
                lastFailedRevision = revision;
                setSaveStatus("Couldn't save settings. Retry from Settings.", "error");
            }
        } finally {
            saveInFlight = null;
            // Only one write at a time. Send the newest *whole* snapshot next.
            if (settingsRevision > revision) {
                void sendLatestSettings();
            }
        }
    })();
    return saveInFlight;
}

function queueSettingsSave(debounce = false) {
    settingsRevision += 1;
    lastFailedRevision = -1;
    setSaveStatus("Saving…", "saving");
    if (numericSaveTimer !== null) {
        clearTimeout(numericSaveTimer);
        numericSaveTimer = null;
    }
    if (debounce) {
        numericSaveTimer = window.setTimeout(() => {
            numericSaveTimer = null;
            void sendLatestSettings();
        }, 450);
    } else {
        void sendLatestSettings();
    }
}

async function ensureSettingsSaved() {
    if (numericSaveTimer !== null) {
        clearTimeout(numericSaveTimer);
        numericSaveTimer = null;
    }
    while (savedRevision < settingsRevision) {
        if (saveInFlight) {
            await saveInFlight;
        } else if (lastFailedRevision === settingsRevision) {
            return false;
        } else {
            await sendLatestSettings();
        }
    }
    return true;
}

settingsRetry.addEventListener("click", () => {
    lastFailedRevision = -1;
    void sendLatestSettings();
});

settingsForm.addEventListener("submit", event => {
    event.preventDefault(); // Enter in a field must not reload the page.
    void sendLatestSettings();
});

autoSpeakSelect.addEventListener("change", () => {
    currentSettings.auto_speak = autoSpeakSelect.value;
    // Changing auto-speak does not cause immediate playback or reveal an answer.
    queueSettingsSave();
});

autoRevealCheckbox.addEventListener("change", () => {
    currentSettings.auto_reveal = autoRevealCheckbox.checked;
    showDelayField();
    scheduleAutoReveal();
    queueSettingsSave();
});

function acceptNumericInput(input, property, message) {
    if (!input.validity.valid || input.value === "") {
        invalidNumericInputs.set(input, message);
        setSaveStatus(message, "invalid");
        return false;
    }
    const value = Number(input.value);
    if (!Number.isFinite(value) ||
        (property === "reveal_delay_seconds" && !Number.isInteger(value))) {
        invalidNumericInputs.set(input, message);
        setSaveStatus(message, "invalid");
        return false;
    }
    invalidNumericInputs.delete(input);
    if (currentSettings[property] !== value) {
        currentSettings[property] = value;
        if (property === "reveal_delay_seconds") {
            scheduleAutoReveal();
        }
        // Apply valid numerical changes now, but avoid saving partial typing.
        queueSettingsSave(true);
    } else if (savedRevision === settingsRevision) {
        setSaveStatus("", "");
    }
    return true;
}

speechRateInput.addEventListener("input", () => {
    acceptNumericInput(speechRateInput, "speech_rate", "Speech rate must be between 0.1 and 10.");
});
revealDelayInput.addEventListener("input", () => {
    acceptNumericInput(revealDelayInput, "reveal_delay_seconds", "Reveal delay must be a whole number of at least 1.");
});
// A committed number should be persisted without waiting for the debounce.
[speechRateInput, revealDelayInput].forEach(input => {
    input.addEventListener("change", () => {
        if (input.validity.valid && input.value !== "") {
            void sendLatestSettings();
        }
    });
});

async function navigateToDeck() {
    if (navigatingAway) {
        return;
    }
    navigatingAway = true;
    const saved = await ensureSettingsSaved();
    if (!saved && !window.confirm("Session settings could not be saved. Leave anyway?")) {
        navigatingAway = false;
        return;
    }
    stopSpeech();
    window.location.assign(deckUrl);
}

const backLink = document.querySelector(".study-back-link");
backLink.addEventListener("click", event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) {
        return;
    }
    if (settingsRevision > savedRevision) {
        event.preventDefault();
        void navigateToDeck();
    }
});

ratingActions.addEventListener("submit", event => {
    if (ratingSubmissionAllowed) {
        ratingSubmissionAllowed = false;
        clearAutoRevealTimer();
        stopSpeech();
        window.setTimeout(() => {
            againButton.disabled = true;
            goodButton.disabled = true;
        }, 0);
        return;
    }
    if (ratingSubmitted || answer.hidden) {
        event.preventDefault();
        return;
    }
    ratingSubmitted = true;
    if (settingsRevision > savedRevision) {
        event.preventDefault();
        const submitter = event.submitter;
        void (async () => {
            const saved = await ensureSettingsSaved();
            if (!saved && !window.confirm("Session settings could not be saved. Continue rating this card?")) {
                ratingSubmitted = false;
                return;
            }
            ratingSubmissionAllowed = true;
            ratingActions.requestSubmit(submitter);
        })();
        return;
    }
    clearAutoRevealTimer();
    stopSpeech();
    window.setTimeout(() => {
        againButton.disabled = true;
        goodButton.disabled = true;
    }, 0);
});

window.addEventListener("pagehide", () => {
    clearAutoRevealTimer();
    stopSpeech();
});

document.addEventListener("keydown", event => {
    if (event.repeat || event.ctrlKey || event.altKey || event.metaKey) {
        return;
    }
    if (event.key === "Escape") {
        if (isSettingsOpen()) {
            event.preventDefault();
            closeSettings(true);
            return;
        }
        // Respect native Escape behavior while a select or other editor is focused.
        if (event.target instanceof HTMLElement &&
            event.target.closest('input, textarea, select, [contenteditable="true"]')) {
            return;
        }
        event.preventDefault();
        void navigateToDeck();
        return;
    }
    if (isSettingsOpen()) {
        return;
    }
    const onControl = event.target instanceof HTMLElement &&
        event.target.closest('input, textarea, select, button, a, summary, [contenteditable="true"], [role="dialog"]');
    if (onControl) {
        return;
    }
    if (event.code === "Space" && answer.hidden) {
        event.preventDefault();
        revealButton.click();
        return;
    }
    if (event.key.toLowerCase() === "r" && lastSpeech) {
        event.preventDefault();
        speakText(lastSpeech.text, lastSpeech.language);
        return;
    }
    if (answer.hidden || ratingSubmitted) {
        return;
    }
    if (event.key === "1") {
        againButton.click();
    } else if (event.key === "2") {
        goodButton.click();
    }
});

showDelayField();
if (currentSettings.auto_speak !== "off") {
    tryInitialAutoSpeak();
}
scheduleAutoReveal();
