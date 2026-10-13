const {test} = require('node:test');
const assert = require('node:assert/strict');
const engine = require('../../demo/js/demo-session.js');
const storage = require('../../demo/js/demo-storage.js');
const deck = (count = 6) => ({id: 'deck', front_language: 'de-DE', back_language: 'en-GB',
    cards: Array.from({length: count}, (_, i) => ({id: `c${i}`, front: `Frage ${i}`, back: `Answer ${i}`}))});
function make(count = 6, options = {}) {
    const state = storage.emptyState();
    const session = engine.startSession(state, deck(count), options);
    return {state, session};
}
function rate(session, value) {
    const revision = session.revision;
    const id = session.pending[0];
    engine.reveal(session, revision);
    return engine.rate(session, value, id, revision);
}

test('empty deck is rejected without abandoning the previous session', () => {
    const {state, session} = make();
    assert.throws(() => engine.startSession(state, deck(0), {}, session.id), /empty deck/);
    assert.equal(session.status, 'active');
});
test('snapshots survive source changes and reverse swaps both text and languages', () => {
    const source = deck();
    const state = storage.emptyState();
    const session = engine.startSession(state, source, {reverse: true});
    source.cards[0].front = 'edited'; source.front_language = 'tr-TR';
    assert.deepEqual(engine.view(session).current_card,
        {id: 'c0', front: 'Answer 0', back: 'Frage 0', front_language: 'en-GB', back_language: 'de-DE'});
});
test('shuffle runs only when selected, using a deterministic random source', () => {
    const state = storage.emptyState();
    const ordered = engine.startSession(state, deck(), {shuffle: false}, null, () => { throw Error('unexpected shuffle'); });
    assert.deepEqual(ordered.pending, ['c0', 'c1', 'c2', 'c3', 'c4', 'c5']);
    const shuffled = engine.startSession(state, deck(), {shuffle: true}, ordered.id, () => 0);
    assert.deepEqual(shuffled.pending, ['c1', 'c2', 'c3', 'c4', 'c5', 'c0']);
    assert.equal(shuffled.shuffle, true);
});
for (const count of [1, 2, 3, 4, 6]) {
    test(`Again reinserts after up to three other cards (${count} cards)`, () => {
        const {session} = make(count);
        rate(session, 'again');
        const expected = deck(count).cards.slice(1).map(card => card.id);
        expected.splice(Math.min(3, expected.length), 0, 'c0');
        assert.deepEqual(session.pending, expected);
        assert.equal(engine.view(session).good_count, 0);
        assert.equal(engine.view(session).progress, 0);
        assert.equal(session.status, 'active');
    });
}
test('ratings require reveal, reject stale card/revision, and never skip a card', () => {
    const {session} = make();
    assert.equal(engine.rate(session, 'good', 'c0', 0), false);
    engine.reveal(session, 0);
    assert.equal(engine.rate(session, 'good', 'c5', 0), false);
    assert.equal(engine.rate(session, 'good', 'c0', 0), true);
    engine.reveal(session, 1);
    assert.equal(engine.rate(session, 'good', 'c0', 0), false);
    assert.equal(engine.view(session).good_count, 1);
    assert.equal(engine.view(session).progress, 1 / 6);
});
test('a one-card Again rejects duplicates even after the same card is revealed again', () => {
    const {session} = make(1);
    rate(session, 'again');
    engine.reveal(session, 1);
    assert.equal(engine.rate(session, 'good', 'c0', 0), false);
    assert.equal(session.status, 'active');
    assert.equal(engine.view(session).good_count, 0);
});
test('completion happens only when every card has received Good', () => {
    const {session} = make();
    for (let i = 0; i < 12; i++) rate(session, 'again');
    assert.equal(session.status, 'active');
    for (let i = 0; i < 6; i++) { assert.equal(rate(session, 'good'), true); }
    assert.equal(session.status, 'completed');
    assert.equal(engine.view(session).good_count, 6);
    assert.equal(engine.view(session).progress, 1);
    assert.equal(engine.view(session).current_card, null);
    assert.equal(engine.rate(session, 'good', 'c0', session.revision), false);
});
test('replacement needs exact confirmation and abandons rather than completes', () => {
    const {state, session} = make(); rate(session, 'good');
    assert.throws(() => engine.startSession(state, deck()), /Confirm/);
    assert.throws(() => engine.startSession(state, deck(), {}, 'stale'), /Confirm/);
    const replacement = engine.startSession(state, deck(), {}, session.id);
    assert.equal(session.status, 'abandoned');
    assert.equal(engine.view(session).current_card, null);
    assert.equal(engine.view(session).good_count, 1);
    assert.equal(engine.activeSession(state, 'deck').id, replacement.id);
    assert.throws(() => engine.startSession(state, deck(), {}, session.id), /Confirm/);
});
test('independent decks each allow one active session', () => {
    const {state, session} = make();
    const other = deck(); other.id = 'other';
    const second = engine.startSession(state, other);
    assert.equal(engine.activeSession(state, 'deck').id, session.id);
    assert.equal(engine.activeSession(state, 'other').id, second.id);
});
test('resume round-trips queue, counts, current card, flags, reveal and settings', () => {
    const {state, session} = make(6, {shuffle: true, reverse: true});
    rate(session, 'again'); rate(session, 'good'); engine.reveal(session, session.revision);
    engine.updateSettings(session, {auto_reveal: true, reveal_delay_seconds: 2, auto_speak: 'front_back', speech_rate: 1.8});
    const memory = new Map();
    const fake = {getItem: key => memory.get(key) ?? null, setItem: (key, value) => memory.set(key, value)};
    storage.save(state, fake);
    assert.deepEqual(storage.load(fake), state);
    assert.deepEqual(engine.view(storage.load(fake).sessions[session.id]), engine.view(session));
});
test('invalid settings never change the committed values; full allowed ranges work', () => {
    const {session} = make();
    for (const changes of [{speech_rate: 0}, {speech_rate: 10.1}, {speech_rate: NaN},
        {reveal_delay_seconds: 0}, {reveal_delay_seconds: 1.5}, {auto_speak: 'cloud'}, {auto_reveal: 1}]) {
        assert.throws(() => engine.updateSettings(session, changes), /Invalid/);
        assert.deepEqual(session.settings, engine.defaults);
    }
    engine.updateSettings(session, {speech_rate: 0.1});
    engine.updateSettings(session, {speech_rate: 10, reveal_delay_seconds: 1});
});
test('corrupted state and contradictory queues are rejected', () => {
    const {state, session} = make();
    session.pending.push(session.pending[0]);
    assert.throws(() => storage.validateState(state), /Invalid session queue/);
    assert.throws(() => storage.load({getItem: () => '{broken'}));
    assert.throws(() => storage.load({getItem: () => '{"version":2,"sessions":{}}'}), /Invalid/);
    const valid = make();
    valid.state.sessions.extra = {...valid.session, id: 'extra'};
    assert.throws(() => storage.validateState(valid.state), /Duplicate active/);
});
