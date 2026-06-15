const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS  = 30000;

// ── Shared connection UI (generic, one page = one reconnecting socket) ─────────
let _wsDownCount = 0;            // how many sockets are currently disconnected

function _ensureReconnectBanner() {
    let el = document.getElementById("ws-reconnect-banner");
    if (!el) {
        el = document.createElement("div");
        el.id = "ws-reconnect-banner";
        el.className = "fixed bottom-4 left-1/2 -translate-x-1/2 z-[60] hidden items-center gap-2 " +
            "rounded-full bg-gray-800/95 px-4 py-2 text-sm text-gray-200 shadow-xl border border-gray-700";
        el.innerHTML =
            '<span class="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>' +
            '<span id="ws-reconnect-banner-text"></span>';
        document.body.appendChild(el);
    }
    return el;
}

function _refreshReconnectBanner() {
    const el = _ensureReconnectBanner();
    const show = _wsDownCount > 0;
    if (show) {
        const txt = document.getElementById("ws-reconnect-banner-text");
        if (txt) txt.textContent = (typeof t === "function" ? t("ws_reconnecting") : "Reconnecting…");
    }
    el.classList.toggle("hidden", !show);
    el.classList.toggle("flex", show);
}

// Transient toast so blocked actions (send while offline) never fail silently.
let _wsToastTimer = null;
function wsToast(message) {
    let el = document.getElementById("ws-toast");
    if (!el) {
        el = document.createElement("div");
        el.id = "ws-toast";
        el.className = "fixed bottom-16 left-1/2 -translate-x-1/2 z-[60] hidden " +
            "rounded-lg bg-gray-800/95 px-4 py-2 text-sm text-gray-100 shadow-xl border border-gray-700";
        document.body.appendChild(el);
    }
    el.textContent = message;
    el.classList.remove("hidden");
    if (typeof gsap !== "undefined") gsap.fromTo(el, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.2 });
    if (_wsToastTimer) clearTimeout(_wsToastTimer);
    _wsToastTimer = setTimeout(() => { el.classList.add("hidden"); }, 2200);
}

// terminalCloseCodes: close codes after which reconnecting is pointless (auth/origin/
//   match gone). onterminal(code) is invoked once instead of reconnecting.
// onopen fires on every (re)open — consumers use it to re-sync authoritative state.
function createReconnectingWs(url, { onopen, onmessage, terminalCloseCodes = [], onterminal } = {}) {
    let _ws = null;
    let reconnectDelay = RECONNECT_BASE_MS;
    let _stopped = false;
    let _connecting = false;       // a socket attempt is in flight (CONNECTING/OPEN)
    let _reconnectTimer = null;    // single-flight: pending reconnect, or null
    let _down = false;             // this instance currently lost its connection

    function _markDown() {
        if (_down) return;
        _down = true;
        _wsDownCount += 1;
        _refreshReconnectBanner();
    }
    function _markUp() {
        if (!_down) return;
        _down = false;
        _wsDownCount = Math.max(0, _wsDownCount - 1);
        _refreshReconnectBanner();
    }

    function _scheduleReconnect() {
        // Single-flight guard: never stack a second pending reconnect, and never
        // schedule while a socket attempt is already in flight.
        if (_stopped || _connecting || _reconnectTimer !== null) return;
        const jitter = 0.5 + Math.random();                 // 0.5×–1.5× — avoid thundering herd
        const delay  = Math.min(reconnectDelay, RECONNECT_MAX_MS) * jitter;
        reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS);
        _reconnectTimer = setTimeout(() => {
            _reconnectTimer = null;
            connect();
        }, delay);
    }

    function connect() {
        if (_stopped || _connecting) return;
        _connecting = true;
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        _ws = new WebSocket(`${proto}//${location.host}${url}`);
        _ws.onopen = () => {
            _connecting = false;
            reconnectDelay = RECONNECT_BASE_MS;
            _markUp();
            onopen?.();
        };
        _ws.onclose = (event) => {
            _connecting = false;
            if (_stopped) return;
            if (terminalCloseCodes.includes(event.code)) {
                _stopped = true;
                _markUp();
                onterminal?.(event.code);
                return;
            }
            _markDown();
            _scheduleReconnect();
        };
        _ws.onerror = () => { try { _ws.close(); } catch (_) {} };
        _ws.onmessage = (event) => {
            let data;
            try { data = JSON.parse(event.data); } catch (_) { return; }
            onmessage?.(data);
        };
    }

    // Fast resume: when the network returns or a suspended tab becomes visible,
    // the dead socket's onclose can take a long time to fire. Drop the backoff and
    // any half-dead socket and reconnect immediately.
    function reconnectNow() {
        if (_stopped) return;
        if (_ws && _ws.readyState === WebSocket.OPEN) return;
        if (_reconnectTimer !== null) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
        reconnectDelay = RECONNECT_BASE_MS;
        if (_ws && _connecting) {
            // Possibly-dead socket stuck CONNECTING: detach so it can't double-fire, then close.
            const dead = _ws;
            dead.onopen = dead.onclose = dead.onerror = dead.onmessage = null;
            try { dead.close(); } catch (_) {}
            _ws = null;
            _connecting = false;
            _markDown();
        }
        connect();
    }

    const _onWake    = () => reconnectNow();
    const _onVisible = () => { if (document.visibilityState === "visible") reconnectNow(); };
    window.addEventListener("online", _onWake);
    document.addEventListener("visibilitychange", _onVisible);

    connect();

    return {
        get readyState() { return _ws ? _ws.readyState : WebSocket.CLOSED; },
        // Returns true if the message was actually handed to an OPEN socket.
        send(data) {
            if (_ws && _ws.readyState === WebSocket.OPEN) { _ws.send(data); return true; }
            return false;
        },
        stop() {
            _stopped = true;
            if (_reconnectTimer !== null) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
            window.removeEventListener("online", _onWake);
            document.removeEventListener("visibilitychange", _onVisible);
            _markUp();
            _ws?.close();
        },
    };
}
