// ── WebSocket ─────────────────────────────────────────────────────────────────

const matchWs = createReconnectingWs(`/ws/match/${MATCH_ID}`, {
    onmessage(data) {
        if (data.type === "board_state")    onBoardState(data);
        if (data.type === "player_joined")  onPlayerJoined(data);
        if (data.type === "role_selected")  onRoleSelected(data);
        if (data.type === "game_start")     onGameStart(data);
        if (data.type === "move")           onMove(data);
        if (data.type === "game_over")      onGameOver(data);
        if (data.type === "message")        { onNewMessage(data); showMatchMessageBubble(data); }
        if (data.type === "message_read")   onMessageRead(data);
        if (data.type === "invite")         onInviteReceived(data);
        if (data.type === "players_online") onPlayersOnline(data);
    },
});

// Seed avatar cache from match player list so the chat drawer can show photos
MATCH_PLAYERS.forEach(p => { if (p.avatar_url) playerAvatars[p.user_id] = p.avatar_url; });

// ── Game state ────────────────────────────────────────────────────────────────

let board       = Array(9).fill(null);   // "X" | "O" | null per cell
let myRole      = null;                  // "x" | "o"
let currentRoles = {};                   // user_id → "x" | "o"
let currentTurn = null;                  // user_id whose turn it is
let gameOver    = typeof MATCH_STATUS !== "undefined" && MATCH_STATUS === "finished";
let countdownInterval = null;
let waitingOfflineTimer = null;
let waitingOfflineCheckReady = false;
let selectedRole = null;
let pendingRoleSelections = {};
const onlinePlayerIds = new Set();
const playingPlayerIds = new Set();
const msgBubbleTimers = {};              // role → timeout id

// ── Player slots ─────────────────────────────────────────────────────────────

function setupPlayerPanels(roles) {
    currentRoles = roles;
    document.getElementById("match-chat-row")?.classList.remove("hidden");
    for (const [userId, role] of Object.entries(roles)) {
        const player = MATCH_PLAYERS.find(p => p.user_id === userId);
        if (!player) continue;
        const avatarEl = document.getElementById(`avatar-${role}`);
        if (avatarEl) {
            if (player.avatar_url) {
                avatarEl.innerHTML = `<img src="${player.avatar_url}" alt="" class="w-full h-full object-cover">`;
            } else {
                avatarEl.textContent = player.username.charAt(0).toUpperCase();
            }
        }
        const nameEl = document.getElementById(`name-${role}`);
        if (nameEl) nameEl.textContent = player.username;
        document.getElementById(`player-slot-${role}`)?.classList.remove("invisible");
    }
}

function showMatchMessageBubble(data) {
    const role = currentRoles[data.sender_id];
    if (!role) return;
    const bubble = document.getElementById(`msg-bubble-${role}`);
    const textEl = document.getElementById(`msg-bubble-${role}-text`);
    if (!bubble || !textEl) return;

    textEl.textContent = data.content;

    if (msgBubbleTimers[role]) {
        clearTimeout(msgBubbleTimers[role]);
        msgBubbleTimers[role] = null;
    }

    const wasHidden = bubble.classList.contains("hidden");
    bubble.classList.remove("hidden");

    if (typeof gsap !== "undefined") {
        gsap.killTweensOf(bubble);
        gsap.fromTo(
            bubble,
            { xPercent: -50, opacity: wasHidden ? 0 : 1, scale: wasHidden ? 0.82 : 1, y: wasHidden ? 10 : 0 },
            { xPercent: -50, opacity: 1, scale: 1, y: 0, duration: 0.32, ease: "back.out(1.7)" }
        );
    } else {
        bubble.style.transform = "translateX(-50%)";
    }

    msgBubbleTimers[role] = setTimeout(() => {
        msgBubbleTimers[role] = null;
        if (typeof gsap !== "undefined") {
            gsap.to(bubble, {
                xPercent: -50, opacity: 0, scale: 0.88, y: 6, duration: 0.22, ease: "power2.in",
                onComplete: () => bubble.classList.add("hidden"),
            });
        } else {
            bubble.classList.add("hidden");
        }
    }, 7000);
}

// ── Board ─────────────────────────────────────────────────────────────────────

function buildBoard() {
    const el = document.getElementById("board");
    el.innerHTML = Array.from({ length: 9 }, (_, i) => {
        const bR = i % 3 < 2 ? "border-r-2 border-gray-700" : "";
        const bB = i < 6     ? "border-b-2 border-gray-700" : "";
        return `<div class="cell relative flex items-center justify-center cursor-pointer
                            aspect-square ${bR} ${bB}" data-index="${i}">
                    <svg id="cell-${i}" class="w-3/4 h-3/4" viewBox="0 0 100 100"></svg>
                </div>`;
    }).join("");

    el.addEventListener("click", onCellClick);
}

function restoreBoard() {
    board.forEach((mark, i) => { if (mark) renderMark(i, mark, false); });
}

function renderMark(index, mark, animate = true) {
    const svg = document.getElementById(`cell-${index}`);
    if (!svg || svg.children.length > 0) return;

    const ns = "http://www.w3.org/2000/svg";

    if (mark === "X") {
        const len = Math.hypot(60, 60);   // ≈ 84.85 — length of (20,20)→(80,80)
        [
            { x1: 20, y1: 20, x2: 80, y2: 80 },
            { x1: 80, y1: 20, x2: 20, y2: 80 },
        ].forEach(({ x1, y1, x2, y2 }, idx) => {
            const line = document.createElementNS(ns, "line");
            Object.entries({
                x1, y1, x2, y2,
                stroke: "#ef4444", "stroke-width": "10",
                "stroke-linecap": "round",
                "stroke-dasharray": len,
                "stroke-dashoffset": animate ? len : 0,
            }).forEach(([k, v]) => line.setAttribute(k, v));
            if (animate) gsap.set(line, { strokeDashoffset: len });
            svg.appendChild(line);
            if (animate) {
                gsap.to(line, { strokeDashoffset: 0, duration: 0.3, ease: "power2.out", delay: idx * 0.12 });
            }
        });

    } else if (mark === "O") {
        const r    = 32;
        const circ = 2 * Math.PI * r;
        const circle = document.createElementNS(ns, "circle");
        Object.entries({
            cx: 50, cy: 50, r,
            stroke: "#3b82f6", "stroke-width": "10",
            "stroke-linecap": "round", fill: "none",
            "stroke-dasharray": circ,
            "stroke-dashoffset": animate ? circ : 0,
        }).forEach(([k, v]) => circle.setAttribute(k, v));
        svg.appendChild(circle);
        if (animate) {
            gsap.to(circle, { strokeDashoffset: 0, duration: 0.4, ease: "power2.out" });
        }
    }
}

function onCellClick(e) {
    const cell = e.target.closest(".cell");
    if (!cell) return;
    const index = parseInt(cell.dataset.index, 10);
    if (board[index] !== null || gameOver) return;
    if (currentTurn !== CURRENT_USER_ID) return;
    if (!myRole) return;

    if (matchWs && matchWs.readyState === WebSocket.OPEN) {
        matchWs.send(JSON.stringify({ type: "move", position: index }));
    }
}

function updateTurnIndicator() {
    const el   = document.getElementById("turn-indicator");
    const text = document.getElementById("turn-text");
    if (!el || !currentTurn || gameOver) { el?.classList.add("hidden"); return; }
    el.classList.remove("hidden");
    if (currentTurn === CURRENT_USER_ID) {
        text.textContent = t('match_your_turn');
        return;
    }
    const player = MATCH_PLAYERS.find(p => p.user_id === currentTurn);
    text.textContent = t('match_opponent_turn', { name: player?.username || '' });
}

// ── WS message handlers ───────────────────────────────────────────────────────

function getOpponent() {
    return MATCH_PLAYERS.find(p => p.user_id !== CURRENT_USER_ID);
}

function isOpponentReallyOffline() {
    const opponent = getOpponent();
    return Boolean(opponent && waitingOfflineCheckReady && !onlinePlayerIds.has(opponent.user_id));
}

function getMatchPresenceLabel(userId) {
    const player = MATCH_PLAYERS.find(p => p.user_id === userId);
    if (!player || userId === CURRENT_USER_ID || !waitingOfflineCheckReady) {
        return "";
    }
    if (!onlinePlayerIds.has(userId)) return t('presence_offline', { name: player.username });
    if (!playingPlayerIds.has(userId)) return t('presence_left', { name: player.username });
    return "";
}

function getMatchOfflineLabel(userId) {
    return getMatchPresenceLabel(userId);
}

function updateMatchPresenceLabels() {
    const opponent = getOpponent();
    const text = opponent ? getMatchPresenceLabel(opponent.user_id) : "";
    const topLabel = document.getElementById("match-status-label");
    if (topLabel) {
        const waitingVisible = Boolean(document.getElementById("waiting-status"));
        topLabel.textContent = waitingVisible ? "" : text;
        topLabel.classList.toggle("hidden", waitingVisible || !text);
    }

    const roleLabel = document.getElementById("role-status-label");
    if (roleLabel) {
        const roleText = opponent ? getMatchOfflineLabel(opponent.user_id) : "";
        roleLabel.textContent = roleText;
        roleLabel.classList.toggle("hidden", !roleText);
    }
}

function updateWaitingOfflineLabel() {
    const label = document.getElementById("waiting-offline-label");
    if (!label) return;

    if (!isOpponentReallyOffline()) {
        label.classList.add("hidden");
        label.textContent = "";
        return;
    }

    const opponent = getOpponent();
    label.textContent = t('presence_currently_offline', { name: opponent.username });
    label.classList.remove("hidden");
}

function startWaitingOfflineTimer() {
    if (waitingOfflineTimer) clearTimeout(waitingOfflineTimer);
    waitingOfflineTimer = setTimeout(() => {
        const status = document.getElementById("waiting-status");
        const label = document.getElementById("waiting-offline-label");
        if (!status || !label || !isOpponentReallyOffline()) return;
        updateWaitingOfflineLabel();
        if (typeof gsap !== "undefined" && !label.classList.contains("hidden")) {
            gsap.fromTo(label, { y: 8, opacity: 0 }, { y: 0, opacity: 1, duration: 0.25, ease: "power2.out" });
        }
    }, 3000);
}

function clearWaitingOfflineTimer() {
    if (waitingOfflineTimer) {
        clearTimeout(waitingOfflineTimer);
        waitingOfflineTimer = null;
    }
}

function onPlayersOnline(data) {
    applyPresenceSnapshot(data.players, players => {
        onlinePlayerIds.clear();
        playingPlayerIds.clear();
        (players || []).forEach(player => {
            if (!player?.user_id) return;
            onlinePlayerIds.add(player.user_id);
            if (player.playing) playingPlayerIds.add(player.user_id);
        });
        waitingOfflineCheckReady = true;
        updateWaitingOfflineLabel();
        updateMatchPresenceLabels();
    });
}

function onBoardState(data) {
    board = data.board;
    pendingRoleSelections = data.selections || {};
    const rolesSet = data.roles && Object.values(data.roles).some(r => r !== null);
    if (!rolesSet) startWaitingOfflineTimer();
    if (rolesSet) {
        clearWaitingOfflineTimer();
        myRole      = data.roles[CURRENT_USER_ID];
        currentTurn = data.current_turn;
        const modal = document.getElementById("role-modal");
        if (modal) modal.classList.add("hidden");
        setupPlayerPanels(data.roles);
        buildBoard();
        restoreBoard();
        updateTurnIndicator();
    }
    if (data.countdown_ms) startCountdown(data.countdown_ms);
}

function onPlayerJoined(data) {
    if (data.both_present) {
        clearWaitingOfflineTimer();
        const status = document.getElementById("waiting-status");
        if (status) status.remove();

        if (data.roles_needed) showRoleModal();
    }
}

function onRoleSelected(data) {
    pendingRoleSelections = data.selections || {};
    updateModalSelections(data.selections);
    if (data.countdown_ms) {
        startCountdown(data.countdown_ms);
    } else {
        clearCountdown();
    }
}

function onGameStart(data) {
    clearCountdown();
    myRole      = data.roles[CURRENT_USER_ID];
    currentTurn = data.current_turn;

    const modal = document.getElementById("role-modal");
    if (modal) modal.classList.add("hidden");

    setupPlayerPanels(data.roles);
    buildBoard();
    updateTurnIndicator();
}

function onMove(data) {
    board[data.position] = data.mark;
    renderMark(data.position, data.mark);
    currentTurn = data.next_turn;
    updateTurnIndicator();
}

function onGameOver(data) {
    gameOver = true;
    updateTurnIndicator();

    let message;
    let winner = null;
    if (data.result === "win") {
        winner = MATCH_PLAYERS.find(p => p.user_id === data.winner_id);
        message = winner ? t('match_winner', { name: winner.username }) : t('match_winner_fallback');
    } else {
        message = t('match_draw');
    }

    const overlay   = document.getElementById("gameover-overlay");
    const text      = document.getElementById("gameover-text");
    const avatarEl  = document.getElementById("gameover-avatar");

    text.textContent = message;

    if (winner && avatarEl) {
        avatarEl.innerHTML = renderAvatar(winner.user_id, winner.username, { noWrapper: true, textSize: "text-4xl" });
        avatarEl.classList.remove("hidden");
        gsap.fromTo(avatarEl, { scale: 0.5, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.5, ease: "back.out(1.7)" });
    }

    overlay.classList.remove("hidden");

    gsap.fromTo(overlay, { opacity: 0 }, { opacity: 1, duration: 0.35, ease: "power2.out" });
    gsap.fromTo(text,    { y: 24, opacity: 0 }, { y: 0, opacity: 1, duration: 0.45, ease: "back.out(1.5)", delay: 0.1 });

    setTimeout(() => { location.href = "/"; }, 4000);
}

// ── Role modal ────────────────────────────────────────────────────────────────

let roleModalInitialised = false;

function showRoleModal() {
    const modal = document.getElementById("role-modal");
    modal.classList.remove("hidden");

    if (!roleModalInitialised) {
        const orderedPlayers = [
            ...MATCH_PLAYERS.filter(p => p.user_id !== CURRENT_USER_ID),
            ...MATCH_PLAYERS.filter(p => p.user_id === CURRENT_USER_ID),
        ];

        document.getElementById("players-row").innerHTML = orderedPlayers.map((p, index) => `
            <div class="flex flex-col items-center gap-2 w-28">
                <div class="relative h-14 w-full">
                    <div id="bubble-${p.user_id}"
                         data-bubble-side="${index === 0 ? "left" : "right"}"
                         class="hidden absolute bottom-1 left-1/2
                                min-w-max max-w-[10rem] whitespace-nowrap rounded-2xl bg-white px-3 py-2 text-center text-xs font-semibold
                                text-gray-900 shadow-xl origin-bottom">
                        <span id="bubble-text-${p.user_id}"></span>
                        <span class="absolute top-full left-1/2 h-0 w-0 -translate-x-1/2
                                     border-l-[7px] border-r-[7px] border-t-[8px]
                                     border-l-transparent border-r-transparent border-t-white"></span>
                    </div>
                </div>
                ${p.avatar_url
                    ? `<img src="${p.avatar_url}" alt=""
                            class="w-14 h-14 rounded-full object-cover select-none">`
                    : `<div class="w-14 h-14 rounded-full bg-indigo-600 flex items-center justify-center
                                  text-2xl font-bold select-none">
                           ${p.username.charAt(0).toUpperCase()}
                       </div>`
                }
                <span class="text-sm text-gray-300">${p.username}</span>
                <span class="text-xs font-bold min-h-4" id="badge-${p.user_id}">-</span>
            </div>
        `).join("");

        // Attach click listeners exactly once — re-calling showRoleModal must not stack them
        document.querySelectorAll(".role-btn").forEach(btn => {
            btn.addEventListener("click", () => selectRole(btn.dataset.role));
        });

        roleModalInitialised = true;
    }

    updateMatchPresenceLabels();
    updateModalSelections(pendingRoleSelections);
}

const ROLE_STYLES = {
    x:      ["border-red-500",    "text-red-400"],
    o:      ["border-blue-500",   "text-blue-400"],
    random: ["border-emerald-500", "text-emerald-400"],
};
function getRoleBubbleText(role) {
    return { x: t('role_i_start'), o: t('role_you_start'), random: t('role_lets_draw') }[role] || '';
}
const BADGE_LABELS = { x: "X", o: "O", random: "?" };

function selectRole(role) {
    if (!matchWs || matchWs.readyState !== WebSocket.OPEN) return;
    const unselect = selectedRole === role;
    selectedRole = unselect ? null : role;
    matchWs.send(JSON.stringify({ type: "role_select", role, unselect }));

    // Optimistic button highlight
    document.querySelectorAll(".role-btn").forEach(b => {
        b.classList.remove(...Object.values(ROLE_STYLES).flat(), "border-gray-700");
        b.classList.add("border-gray-700");
    });
    if (unselect) return;
    const active = document.querySelector(`.role-btn[data-role="${role}"]`);
    if (active) {
        active.classList.remove("border-gray-700");
        active.classList.add(...(ROLE_STYLES[role] ?? []));
    }
}

function showRoleBubble(bubble, wasHidden) {
    bubble.dataset.visible = "true";
    bubble.classList.remove("hidden");

    if (typeof gsap === "undefined") return;
    const side = bubble.dataset.bubbleSide === "left" ? 1 : -1;
    gsap.killTweensOf(bubble);
    gsap.fromTo(
        bubble,
        { xPercent: -50, y: wasHidden ? 14 : 6, x: side * (wasHidden ? 8 : 3), opacity: wasHidden ? 0 : 0.82, scale: wasHidden ? 0.86 : 0.94, rotate: side * (wasHidden ? 3 : 1.5) },
        { xPercent: -50, y: 0, x: 0, opacity: 1, scale: 1, rotate: 0, duration: 0.34, ease: "back.out(1.7)" }
    );
}

function hideRoleBubble(bubble) {
    delete bubble.dataset.role;
    if (bubble.dataset.visible !== "true") {
        bubble.classList.add("hidden");
        return;
    }
    bubble.dataset.visible = "false";

    if (typeof gsap === "undefined") {
        bubble.classList.add("hidden");
        return;
    }

    const side = bubble.dataset.bubbleSide === "left" ? 1 : -1;
    gsap.killTweensOf(bubble);
    gsap.to(bubble, {
        xPercent: -50,
        y: 12,
        x: side * 6,
        opacity: 0,
        scale: 0.9,
        rotate: side * 2,
        duration: 0.18,
        ease: "power2.in",
        onComplete: () => bubble.classList.add("hidden"),
    });
}

function updateModalSelections(selections) {
    selectedRole = selections[CURRENT_USER_ID] || null;
    document.querySelectorAll(".role-btn").forEach(b => {
        b.classList.remove(...Object.values(ROLE_STYLES).flat(), "border-gray-700");
        b.classList.add("border-gray-700");
    });
    if (selectedRole) {
        const active = document.querySelector(`.role-btn[data-role="${selectedRole}"]`);
        if (active) {
            active.classList.remove("border-gray-700");
            active.classList.add(...(ROLE_STYLES[selectedRole] ?? []));
        }
    }

    MATCH_PLAYERS.forEach(player => {
        const bubble = document.getElementById(`bubble-${player.user_id}`);
        if (bubble && !selections[player.user_id]) hideRoleBubble(bubble);
        const badge = document.getElementById(`badge-${player.user_id}`);
        if (badge && !selections[player.user_id]) badge.textContent = "-";
    });

    Object.entries(selections).forEach(([uid, role]) => {
        const badge = document.getElementById(`badge-${uid}`);
        if (badge) badge.textContent = BADGE_LABELS[role] ?? "-";

        const bubble = document.getElementById(`bubble-${uid}`);
        const text = document.getElementById(`bubble-text-${uid}`);
        if (bubble && text && getRoleBubbleText(role)) {
            const wasHidden = bubble.classList.contains("hidden");
            const changed = bubble.dataset.role !== role;
            text.textContent = getRoleBubbleText(role);
            bubble.dataset.role = role;
            if (wasHidden || changed) showRoleBubble(bubble, wasHidden);
        }
    });
}

// ── Inline chat ──────────────────────────────────────────────────────────────

function toggleEmojiPicker() {
    const picker = document.getElementById("emoji-picker");
    picker.classList.toggle("hidden");
}

function appendEmoji(emoji) {
    const input = document.getElementById("match-chat-input");
    input.value += emoji;
    input.focus();
}

document.addEventListener("click", (e) => {
    if (!e.target.closest("#emoji-btn") && !e.target.closest("#emoji-picker")) {
        document.getElementById("emoji-picker")?.classList.add("hidden");
    }
});

function sendMatchChatMessage() {
    const opponent = MATCH_PLAYERS.find(p => p.user_id !== CURRENT_USER_ID);
    if (!opponent) return;
    const input = document.getElementById("match-chat-input");
    const content = input.value.trim();
    if (!content) return;
    if (!matchWs || matchWs.readyState !== WebSocket.OPEN) return;
    matchWs.send(JSON.stringify({ type: "send_message", receiver_id: opponent.user_id, content }));
    input.value = "";
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("match-chat-input").addEventListener("keydown", e => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMatchChatMessage(); }
    });
});

// ── Countdown ─────────────────────────────────────────────────────────────────

function startCountdown(durationMs) {
    clearCountdown();
    document.getElementById("countdown-wrap").classList.remove("hidden");
    const deadline = Date.now() + durationMs;

    const tick = () => {
        const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
        const el = document.getElementById("countdown-num");
        if (el) el.textContent = remaining;
        if (remaining <= 0) clearCountdown();
    };

    tick();
    countdownInterval = setInterval(tick, 250);
}

function clearCountdown() {
    if (countdownInterval) { clearInterval(countdownInterval); countdownInterval = null; }
    const wrap = document.getElementById("countdown-wrap");
    if (wrap) wrap.classList.add("hidden");
}
