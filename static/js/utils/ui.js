// ── Avatar cache ──────────────────────────────────────────────────────────────
const playerAvatars = {};
const playerAvatarBust = {};

function renderAvatar(userId, username, opts) {
    const { size = "w-10 h-10", textSize = "text-lg", presenceDot = null, noWrapper = false } = opts || {};
    const url = playerAvatars[userId];
    const bust = playerAvatarBust[userId] ? `?t=${playerAvatarBust[userId]}` : "";
    const initial = (username || "?").charAt(0).toUpperCase();
    const fallback = `<div class="w-full h-full rounded-full bg-indigo-600 flex items-center justify-center ${textSize} font-bold select-none">${initial}</div>`;
    const inner = url
        ? `<img src="${url}${bust}" alt="" class="w-full h-full rounded-full object-cover select-none" onerror='this.outerHTML=\`${fallback.replace(/`/g, "\\`")}\`'>`
        : fallback;
    if (noWrapper) return inner;
    const dot = presenceDot
        ? `<span class="absolute -right-0.5 -bottom-0.5 h-3 w-3 rounded-full border-2 border-gray-900 ${presenceDot}"></span>`
        : "";
    return `<div class="relative ${size} shrink-0">${inner}${dot}</div>`;
}

// ── Notification sound ────────────────────────────────────────────────────────
let notificationAudioCtx = null;
let soundMuted = false;

function toggleNotificationSound() {
    soundMuted = !soundMuted;
    document.getElementById('bell-on').classList.toggle('hidden', soundMuted);
    document.getElementById('bell-off').classList.toggle('hidden', !soundMuted);
}

function ensureNotificationAudio() {
    if (notificationAudioCtx) return notificationAudioCtx;
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return null;
    notificationAudioCtx = new AudioCtx();
    return notificationAudioCtx;
}

function primeNotificationAudio() {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    // iOS: route to the 'playback' category so the chime is NOT muted by the
    // physical ring/silent switch (Web Audio defaults to 'ambient', which is).
    if (navigator.audioSession) {
        try { navigator.audioSession.type = 'playback'; } catch (_) {}
    }
    if (!notificationAudioCtx) notificationAudioCtx = new AudioCtx();
    const ctx = notificationAudioCtx;
    const playSilence = () => {
        try {
            const buf = ctx.createBuffer(1, 1, 22050);
            const src = ctx.createBufferSource();
            src.buffer = buf;
            src.connect(ctx.destination);
            src.start(0);
        } catch (_) {}
    };
    if (ctx.state === 'suspended') {
        ctx.resume().then(playSilence).catch(() => {});
    }
    playSilence();
}

// Attach as early as possible — do not wait for DOMContentLoaded
(function attachAudioUnlock() {
    const opts = { passive: true, capture: true };
    document.addEventListener('touchstart', primeNotificationAudio, opts);
    document.addEventListener('pointerdown', primeNotificationAudio, opts);
    document.addEventListener('keydown', primeNotificationAudio, opts);
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') primeNotificationAudio();
    });
})();

function playNotificationSound() {
    if (soundMuted) return;
    const ctx = ensureNotificationAudio();
    if (!ctx) return;
    if (ctx.state === 'suspended') {
        ctx.resume()
            .then(() => {
                if (ctx.state === 'running') playNotificationChime(ctx);
            })
            .catch(() => { });
        return;
    }
    playNotificationChime(ctx);
}

function playNotificationChime(ctx) {
    const playTone = (start, freq, duration, peak) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, start);
        osc.frequency.exponentialRampToValueAtTime(freq * 0.985, start + duration);

        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.linearRampToValueAtTime(peak, start + 0.012);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(start);
        osc.stop(start + duration + 0.02);
    };

    const now = ctx.currentTime;
    playTone(now, 659.25, 0.16, 0.12);
    playTone(now + 0.09, 987.77, 0.22, 0.09);
}
