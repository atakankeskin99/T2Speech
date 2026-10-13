(function (root) {
    "use strict";
    const KEY = "t2speech-demo-v1";
    function emptyState() { return {version: 1, sessions: {}}; }
    function validateState(state) {
        if (!state || state.version !== 1 || !state.sessions || Array.isArray(state.sessions) ||
            typeof state.sessions !== "object") throw new Error("Invalid stored demo data.");
        const activeDecks = new Set();
        for (const [id, session] of Object.entries(state.sessions)) {
            root.DemoSession.validateSession(session);
            if (id !== session.id) throw new Error("Invalid stored session identifier.");
            if (session.status === "active") {
                if (activeDecks.has(session.deck_id)) throw new Error("Duplicate active sessions.");
                activeDecks.add(session.deck_id);
            }
        }
        return state;
    }
    function load(storage = root.sessionStorage) {
        const raw = storage.getItem(KEY);
        return raw === null ? emptyState() : validateState(JSON.parse(raw));
    }
    function save(state, storage = root.sessionStorage) {
        validateState(state);
        storage.setItem(KEY, JSON.stringify(state));
    }
    function reset(storage = root.sessionStorage) { storage.removeItem(KEY); }
    const api = {KEY, emptyState, validateState, load, save, reset};
    root.DemoStorage = api;
    if (typeof module !== "undefined") module.exports = api;
})(globalThis);
