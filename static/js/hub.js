const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

let hubWs = null;
let reconnectDelay = RECONNECT_BASE_MS;
let playersOnline = [];
const ongoingMatches = {};
let currentUsername = CURRENT_USERNAME;
let currentEmail = CURRENT_EMAIL;

function connectHub() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    hubWs = new WebSocket(`${proto}//${location.host}/ws/hub`);

    hubWs.onopen = () => {
        reconnectDelay = RECONNECT_BASE_MS;
        loadOngoingMatches();
    };

    hubWs.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "players_online") onPlayersOnline(data);
        if (data.type === "invite")         renderInvite(data);
        if (data.type === "message")        onNewMessage(data);
        if (data.type === "message_read")   onMessageRead(data);
    };

    hubWs.onclose = () => {
        setTimeout(connectHub, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS);
    };

    hubWs.onerror = () => {
        hubWs.close();
    };
}

connectHub();

// ── Player grid ───────────────────────────────────────────────────────────────

function onPlayersOnline(data) {
    const apply = typeof applyPresenceSnapshot === "function" ? applyPresenceSnapshot : null;
    if (apply) {
        apply(data.players, players => {
            playersOnline = players;
            renderPlayersOnline();
        });
        return;
    }
    playersOnline = data.players;
    renderPlayersOnline();
    if (typeof updateChatPresence === "function") updateChatPresence(data.players);
}

function openProfileModal() {
    document.getElementById("profile-username").value = currentUsername;
    document.getElementById("profile-email").value = currentEmail;
    document.getElementById("profile-password").value = "";
    const feedback = document.getElementById("profile-feedback");
    feedback.textContent = "";
    feedback.className = "min-h-5 text-sm text-gray-500";
    document.getElementById("profile-modal").classList.remove("hidden");
}

function closeProfileModal() {
    document.getElementById("profile-modal").classList.add("hidden");
}

async function saveProfile(event) {
    event.preventDefault();
    const feedback = document.getElementById("profile-feedback");
    feedback.textContent = "Saving...";
    feedback.className = "min-h-5 text-sm text-gray-500";

    try {
        const res = await fetch("/profile", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: document.getElementById("profile-username").value.trim(),
                email: document.getElementById("profile-email").value.trim(),
                password: document.getElementById("profile-password").value,
            }),
        });
        const data = await res.json();
        if (!res.ok) {
            feedback.textContent = data.error || "Could not update profile.";
            feedback.className = "min-h-5 text-sm text-red-400";
            return;
        }

        currentUsername = data.username;
        currentEmail = data.email;
        feedback.textContent = "Saved.";
        feedback.className = "min-h-5 text-sm text-emerald-400";
        setTimeout(() => location.reload(), 300);
    } catch (_) {
        feedback.textContent = "Could not update profile.";
        feedback.className = "min-h-5 text-sm text-red-400";
    }
}

function signOut() {
    const form = document.createElement("form");
    form.method = "post";
    form.action = "/logout";
    document.body.appendChild(form);
    form.submit();
}

function renderPlayersOnline() {
    const grid = document.getElementById("players-grid");
    const players = [...playersOnline].sort((a, b) => {
        if (a.user_id === CURRENT_USER_ID) return -1;
        if (b.user_id === CURRENT_USER_ID) return 1;
        return 0;
    });

    if (players.length === 0) {
        grid.innerHTML = '<p class="col-span-full text-center text-gray-600 py-16">No players online right now.</p>';
        return;
    }

    grid.innerHTML = players.map(p => `
        <div class="bg-gray-900 rounded-2xl p-5 flex flex-col items-center gap-3
                    hover:bg-gray-800 cursor-pointer transition-colors player-card"
             data-user-id="${p.user_id}"
             data-username="${p.username}">
            <div class="w-14 h-14 rounded-full bg-indigo-600 flex items-center justify-center
                        text-2xl font-bold select-none">
                ${p.username.charAt(0).toUpperCase()}
            </div>
            <span class="text-sm font-medium">${p.username}</span>
            ${p.user_id === CURRENT_USER_ID
                ? `<span class="mt-1 px-3 py-1.5 rounded-lg border border-sky-600 text-sky-400
                           text-xs font-semibold">
                       You
                   </span>`
                : ongoingMatches[p.user_id]
                ? `<a href="/match/${ongoingMatches[p.user_id]}"
                      class="join-match mt-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg
                             text-xs font-semibold transition-colors"
                      data-match-id="${ongoingMatches[p.user_id]}">
                       Join game
                   </a>`
                : p.playing
                ? `<span class="mt-1 px-3 py-1.5 rounded-lg border border-amber-600 text-amber-400
                           text-xs font-semibold">
                       Playing...
                   </span>`
                : `<button type="button"
                           class="invite-btn mt-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg
                                  text-xs font-semibold transition-colors"
                           data-user-id="${p.user_id}">
                       Invite
                   </button>`
            }
        </div>
    `).join("");
}

async function loadOngoingMatches() {
    try {
        const res = await fetch("/match/ongoing");
        if (!res.ok) return;
        const data = await res.json();
        Object.keys(ongoingMatches).forEach(userId => delete ongoingMatches[userId]);
        Object.assign(ongoingMatches, data.matches || {});
        if (playersOnline.length > 0) renderPlayersOnline();
    } catch (_) {}
}

document.getElementById("players-grid").addEventListener("click", (e) => {
    const action = e.target.closest("button, a");
    if (action) {
        e.stopPropagation();
    }

    const inviteBtn = e.target.closest(".invite-btn");
    if (inviteBtn) {
        sendInvite(inviteBtn.dataset.userId);
        return;
    }

    const card = e.target.closest(".player-card");
    if (!card) return;
    if (card.dataset.userId === CURRENT_USER_ID) {
        openProfileModal();
        return;
    }
    openDrawer();
    openThread(card.dataset.userId, card.dataset.username);
});

async function sendInvite(targetUserId) {
    const res = await fetch("/match/invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_user_id: targetUserId }),
    });
    const data = await res.json();
    if (data.match_id) {
        location.href = `/match/${data.match_id}`;
    }
}

// ── Invite notifications ──────────────────────────────────────────────────────

const seenInvites = new Set();

function renderInvite(data) {
    // Deduplicate: pending invites are re-sent on every hub connect
    if (seenInvites.has(data.match_id)) return;
    seenInvites.add(data.match_id);
    ongoingMatches[data.from_user_id] = data.match_id;
    if (playersOnline.length > 0) renderPlayersOnline();

    const container = document.getElementById("invites-container");
    if (container) {
        const card = document.createElement("div");
        card.className = "relative bg-gray-900 border border-indigo-700 rounded-xl p-4 pr-10 shadow-2xl";
        card.dataset.matchId = data.match_id;
        card.innerHTML = `
            <button type="button"
                    class="invite-close absolute top-2 right-2 w-7 h-7 rounded-lg text-gray-500
                           hover:text-white hover:bg-gray-800 transition-colors"
                    aria-label="Dismiss invite"
                    data-match-id="${data.match_id}">
                &times;
            </button>
            <p class="text-sm text-white mb-3">
                <strong class="text-indigo-400">${data.from_username}</strong> challenged you to a game!
            </p>
            <a href="/match/${data.match_id}"
               class="block w-full text-center py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg
                      text-sm font-semibold transition-colors">
                Join game
            </a>
        `;
        container.prepend(card);
        if (typeof gsap !== "undefined") {
            gsap.from(card, {
                y: -20,
                x: 20,
                opacity: 0,
                duration: 0.35,
                ease: "back.out(1.4)",
            });
        }
    }

    onInviteReceived(data);
}

async function dismissInvite(matchId) {
    seenInvites.add(matchId);
    try {
        await fetch(`/match/invite/${matchId}/read`, { method: "POST" });
    } catch (_) {}
    if (typeof dismissInviteLocally === "function") {
        dismissInviteLocally(matchId);
    }

    const card = document
        .getElementById("invites-container")
        ?.querySelector(`[data-match-id="${matchId}"]`);
    if (!card) return;
    if (typeof gsap !== "undefined") {
        gsap.to(card, {
            x: 24,
            opacity: 0,
            height: 0,
            marginTop: 0,
            marginBottom: 0,
            paddingTop: 0,
            paddingBottom: 0,
            duration: 0.24,
            ease: "power2.in",
            onComplete: () => card.remove(),
        });
    } else {
        card.remove();
    }
}

document.getElementById("invites-container").addEventListener("click", (e) => {
    const close = e.target.closest(".invite-close");
    if (!close) return;
    e.preventDefault();
    e.stopPropagation();
    dismissInvite(close.dataset.matchId);
});

document.getElementById("profile-form").addEventListener("submit", saveProfile);
