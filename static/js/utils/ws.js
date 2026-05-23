const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS  = 30000;

function createReconnectingWs(url, { onopen, onmessage } = {}) {
    let _ws = null;
    let reconnectDelay = RECONNECT_BASE_MS;
    let _stopped = false;

    function connect() {
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        _ws = new WebSocket(`${proto}//${location.host}${url}`);
        _ws.onopen = () => {
            reconnectDelay = RECONNECT_BASE_MS;
            onopen?.();
        };
        _ws.onclose = () => {
            if (_stopped) return;
            setTimeout(connect, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS);
        };
        _ws.onerror = () => { _ws.close(); };
        _ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            onmessage?.(data);
        };
    }

    connect();

    return {
        get readyState() { return _ws ? _ws.readyState : WebSocket.CLOSED; },
        send(data) { _ws?.send(data); },
        stop() { _stopped = true; _ws?.close(); },
    };
}
