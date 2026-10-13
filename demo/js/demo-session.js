/* Browser-only counterpart of the production study queue. No transport or DOM. */
(function (root) {
    "use strict";
    const defaults = Object.freeze({auto_reveal: false, reveal_delay_seconds: 5,
        auto_speak: "off", speech_rate: 1});

    function validateSettings(settings) {
        if (typeof settings.auto_reveal !== "boolean" ||
            !Number.isSafeInteger(settings.reveal_delay_seconds) || settings.reveal_delay_seconds < 1 ||
            !["off", "front", "front_back"].includes(settings.auto_speak) ||
            !Number.isFinite(settings.speech_rate) || settings.speech_rate < 0.1 || settings.speech_rate > 10) {
            throw new Error("Invalid session settings.");
        }
    }

    function validateSession(session) {
        if (!session || typeof session.id !== "string" || typeof session.deck_id !== "string" ||
            !["active", "completed", "abandoned"].includes(session.status) ||
            typeof session.shuffle !== "boolean" || typeof session.reverse !== "boolean" ||
            typeof session.revealed !== "boolean" ||
            !Number.isSafeInteger(session.revision) || session.revision < 0 ||
            typeof session.front_language !== "string" || typeof session.back_language !== "string" ||
            !Array.isArray(session.cards) || !session.cards.length || !Array.isArray(session.pending)) {
            throw new Error("Invalid stored demo session.");
        }
        const ids = session.cards.map(card => {
            if (typeof card.id !== "string" || typeof card.front !== "string" || typeof card.back !== "string") {
                throw new Error("Invalid card snapshot.");
            }
            return card.id;
        });
        if (new Set(ids).size !== ids.length || new Set(session.pending).size !== session.pending.length ||
            session.pending.some(id => !ids.includes(id)) ||
            (session.status === "active" && !session.pending.length) ||
            (session.status === "completed" && session.pending.length)) {
            throw new Error("Invalid session queue.");
        }
        validateSettings(session.settings);
    }

    function activeSession(state, deckId) {
        return Object.values(state.sessions).find(session => session.deck_id === deckId && session.status === "active");
    }

    function startSession(state, deck, options = {}, replaceSessionId = null, random = Math.random) {
        if (!deck.cards.length) throw new Error("Cannot start a study session with an empty deck.");
        const previous = activeSession(state, deck.id);
        // Confirmation identifies the exact session. A stale confirmation cannot replace another session.
        if (previous && replaceSessionId !== previous.id) throw new Error("Confirm replacing your unfinished session first.");
        const cards = deck.cards.map(card => ({id: card.id, front: card.front, back: card.back}));
        const pending = cards.map(card => card.id);
        if (options.shuffle === true) {
            for (let i = pending.length - 1; i > 0; i--) {
                const j = Math.floor(random() * (i + 1));
                [pending[i], pending[j]] = [pending[j], pending[i]];
            }
        }
        const id = root.crypto?.randomUUID?.() || `demo-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        const session = {id, deck_id: deck.id, status: "active", shuffle: options.shuffle === true,
            reverse: options.reverse === true, front_language: deck.front_language,
            back_language: deck.back_language, cards, pending, revealed: false, revision: 0,
            settings: {...defaults}};
        validateSession(session);
        if (previous) previous.status = "abandoned";
        state.sessions[id] = session;
        return session;
    }

    function view(session) {
        const total = session.cards.length;
        const good = total - session.pending.length;
        const card = session.status === "active" ? session.cards.find(item => item.id === session.pending[0]) : null;
        return {total_cards: total, good_count: good, progress: good / total,
            current_card: card ? {
                id: card.id, front: session.reverse ? card.back : card.front,
                back: session.reverse ? card.front : card.back,
                front_language: session.reverse ? session.back_language : session.front_language,
                back_language: session.reverse ? session.front_language : session.back_language
            } : null};
    }

    function reveal(session, revision) {
        if (session.status !== "active" || session.revision !== revision) return false;
        session.revealed = true;
        return true;
    }

    function rate(session, rating, cardId, revision) {
        if (!["again", "good"].includes(rating)) throw new Error("Invalid rating.");
        if (session.status !== "active" || !session.revealed || session.revision !== revision ||
            session.pending[0] !== cardId) return false;
        const current = session.pending.shift();
        if (rating === "again") session.pending.splice(Math.min(3, session.pending.length), 0, current);
        session.revision++;
        session.revealed = false;
        if (!session.pending.length) session.status = "completed";
        return true;
    }

    function updateSettings(session, changes) {
        if (session.status !== "active") throw new Error("Study session is not active.");
        const settings = {...session.settings, ...changes};
        validateSettings(settings);
        session.settings = settings;
    }

    const api = {defaults, validateSettings, validateSession, activeSession, startSession, view, reveal, rate, updateSettings};
    root.DemoSession = api;
    if (typeof module !== "undefined") module.exports = api;
})(globalThis);
