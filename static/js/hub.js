let playersOnline = [];
const ongoingMatches = {};
let currentUsername = CURRENT_USERNAME;
let currentEmail = CURRENT_EMAIL;

const hubWs = createReconnectingWs('/ws/hub', {
    terminalCloseCodes: [1000, 1008, 4001, 4403],
    onterminal(code) { onHubTerminalClose(code); },
    onopen() { seenInvites.clear(); loadOngoingMatches(); },
    onmessage(data) {
        if (data.type === "players_online")  onPlayersOnline(data);
        if (data.type === "invite")          renderInvite(data);
        if (data.type === "message")         onNewMessage(data);
        if (data.type === "message_read")    onMessageRead(data);
        if (data.type === "session_replaced") onSessionReplaced();
    },
});

// ── Player grid ───────────────────────────────────────────────────────────────

function onPlayersOnline(data) {
    applyPresenceSnapshot(data.players, players => {
        playersOnline = players;
        renderPlayersOnline();
    });
}

function onHubTerminalClose(code) {
    if (code === 1000) return;     // clean server-side close — nothing to recover
    location.href = "/login";      // auth/origin/policy — session is gone, re-authenticate
}

function onSessionReplaced() {
    hubWs.stop();
    document.body.innerHTML = `
        <div class="min-h-screen flex items-center justify-center bg-gray-950 px-4">
            <div class="text-center">
                <p class="text-white text-lg font-semibold mb-2">${t('session_replaced_title')}</p>
                <p class="text-gray-400 text-sm mb-6">${t('session_replaced_body')}</p>
                <button onclick="location.reload()"
                        class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg
                               text-sm font-semibold text-white transition-colors">
                    ${t('btn_reload')}
                </button>
            </div>
        </div>`;
}

function avatarHtml(userId, username, size = "w-14 h-14", textSize = "text-2xl") {
    return renderAvatar(userId, username, { size, textSize });
}

function openProfileModal() {
    document.getElementById("profile-username").value = currentUsername;
    document.getElementById("profile-email").value = currentEmail;
    document.getElementById("profile-password").value = "";
    const feedback = document.getElementById("profile-feedback");
    feedback.textContent = "";
    feedback.className = "min-h-5 text-sm text-gray-500";
    const avatarFeedback = document.getElementById("avatar-feedback");
    if (avatarFeedback) {
        avatarFeedback.textContent = t('profile_avatar_change') || "Change photo";
        avatarFeedback.className = "text-xs text-gray-500";
    }
    document.getElementById("profile-modal").classList.remove("hidden");
}

function closeProfileModal() {
    resetAvatarPicker();
    document.getElementById("profile-modal").classList.add("hidden");
}

async function saveProfile(event) {
    event.preventDefault();
    const feedback = document.getElementById("profile-feedback");
    feedback.textContent = t('status_saving');
    feedback.className = "min-h-5 text-sm text-gray-500";

    try {
        const [profileRes, avatarRes] = await Promise.all([
            fetch("/profile", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    username: document.getElementById("profile-username").value.trim(),
                    email: document.getElementById("profile-email").value.trim(),
                    password: document.getElementById("profile-password").value,
                    language_code: typeof selectedProfileLang !== "undefined" ? selectedProfileLang : LANG,
                }),
            }),
            pendingAvatarFile ? (() => {
                const fd = new FormData();
                fd.append("file", pendingAvatarFile);
                return fetch("/profile/avatar", { method: "POST", body: fd });
            })() : Promise.resolve(null),
        ]);

        const profileData = await profileRes.json();
        if (!profileRes.ok) {
            feedback.textContent = profileData.error || t('error_could_not_update');
            feedback.className = "min-h-5 text-sm text-red-400";
            return;
        }

        if (avatarRes) {
            let avatarData;
            try { avatarData = await avatarRes.json(); } catch (_) { avatarData = {}; }
            if (!avatarRes.ok) {
                feedback.textContent = avatarData.error || t('error_could_not_update');
                feedback.className = "min-h-5 text-sm text-red-400";
                return;
            }
            playerAvatars[CURRENT_USER_ID] = avatarData.avatar_url;
            playerAvatarBust[CURRENT_USER_ID] = Date.now();
        }

        currentUsername = profileData.username;
        currentEmail = profileData.email;
        pendingAvatarFile = null;
        originalAvatarHTML = null;
        feedback.textContent = t('status_saved');
        feedback.className = "min-h-5 text-sm text-emerald-400";
        setTimeout(() => location.reload(), 300);
    } catch (_) {
        feedback.textContent = t('error_could_not_update');
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
        grid.innerHTML = `<p class="col-span-full text-center text-gray-600 py-16">${t('hub_no_players')}</p>`;
        return;
    }

    players.forEach(p => {
        if (p.avatar_url) playerAvatars[p.user_id] = p.avatar_url;
    });

    grid.innerHTML = players.map(p => `
        <div class="bg-gray-900 rounded-2xl p-5 flex flex-col items-center gap-3
                    hover:bg-gray-800 cursor-pointer transition-colors player-card"
             data-user-id="${p.user_id}"
             data-username="${p.username}">
            ${avatarHtml(p.user_id, p.username)}
            <span class="text-sm font-medium">${p.username}</span>
            ${p.user_id === CURRENT_USER_ID
                ? `<span class="mt-1 px-3 py-1.5 rounded-lg border border-sky-600 text-sky-400
                           text-xs font-semibold">
                       ${t('hub_you')}
                   </span>`
                : ongoingMatches[p.user_id]
                ? `<a href="/match/${ongoingMatches[p.user_id]}"
                      class="join-match mt-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg
                             text-xs font-semibold transition-colors"
                      data-match-id="${ongoingMatches[p.user_id]}">
                       ${t('btn_join_game')}
                   </a>`
                : p.playing
                ? `<span class="mt-1 px-3 py-1.5 rounded-lg border border-amber-600 text-amber-400
                           text-xs font-semibold">
                       ${t('hub_playing')}
                   </span>`
                : `<button type="button"
                           class="invite-btn mt-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded-lg
                                  text-xs font-semibold transition-colors"
                           data-user-id="${p.user_id}">
                       ${t('btn_invite')}
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
    const inviteBtn = e.target.closest(".invite-btn");
    if (inviteBtn) {
        sendInvite(inviteBtn.dataset.userId);
        return;
    }

    // Let links and other buttons handle themselves without opening the chat
    if (e.target.closest("a, button")) return;

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
                ${t('chat_challenged', { name: `<strong class="text-indigo-400">${data.from_username}</strong>` })}
            </p>
            <a href="/match/${data.match_id}"
               class="block w-full text-center py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg
                      text-sm font-semibold transition-colors">
                ${t('btn_join_game')}
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
    dismissInviteLocally(matchId);

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

let pendingAvatarFile = null;
let originalAvatarHTML = null;

function resetAvatarPicker() {
    pendingAvatarFile = null;
    document.getElementById("avatar-input").value = "";
    const feedback = document.getElementById("avatar-feedback");
    feedback.textContent = t('profile_avatar_change') || "Change photo";
    feedback.className = "text-xs text-gray-500";
    if (originalAvatarHTML !== null) {
        document.getElementById("avatar-preview").innerHTML = originalAvatarHTML;
        originalAvatarHTML = null;
    }
}

document.getElementById("avatar-input").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    pendingAvatarFile = file;

    const preview = document.getElementById("avatar-preview");
    if (originalAvatarHTML === null) originalAvatarHTML = preview.innerHTML;
    const objectUrl = URL.createObjectURL(file);
    preview.innerHTML = `<img src="${objectUrl}" alt="" class="w-full h-full object-cover"
                              onload="URL.revokeObjectURL(this.src)">`;
    document.getElementById("avatar-feedback").textContent = "";
});
