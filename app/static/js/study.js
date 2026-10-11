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

const speakFrontButton = document.getElementById("speak-front");
const speakBackButton = document.getElementById("speak-back");
const frontText = document.getElementById("front-text");
const backText = document.getElementById("back-text");
const audioStatus = document.getElementById("audio-status");

const speechAvailable = "speechSynthesis" in window;
let availableVoices = speechAvailable
    ? window.speechSynthesis.getVoices()
    : [];
let lastSpeech = null;

if (speechAvailable) {
    window.speechSynthesis.addEventListener("voiceschanged", () => {
        availableVoices = window.speechSynthesis.getVoices();
    });
}

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
        availableVoices.find(
            voice =>
                voice.localService &&
                voice.lang.toLowerCase() === wantedLanguage
        ) ||
        availableVoices.find(
            voice =>
                voice.localService &&
                voice.lang.toLowerCase().split("-")[0] === baseLanguage
        )
    );
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
    utterance.rate = 1.0;

    utterance.onerror = () => {
        setAudioStatus("Audio playback failed. You can continue studying.");
    };

    lastSpeech = { text, language };
    window.speechSynthesis.speak(utterance);
}

revealButton.addEventListener("click", () => {
    answer.hidden = false;
    revealButton.hidden = true;
    ratingActions.hidden = false;
    revealedInput.value = "true";
});

speakFrontButton.addEventListener("click", () => {
    speakText(frontText.textContent, speakFrontButton.dataset.language);
});

speakBackButton.addEventListener("click", () => {
    speakText(backText.textContent, speakBackButton.dataset.language);
});

ratingActions.addEventListener("submit", stopSpeech);
window.addEventListener("pagehide", stopSpeech);

document.addEventListener("keydown", event => {
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
        stopSpeech();
        window.location.href = document.body.dataset.deckUrl;
        return;
    }

    if (event.key.toLowerCase() === "r" && lastSpeech) {
        event.preventDefault();
        speakText(lastSpeech.text, lastSpeech.language);
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