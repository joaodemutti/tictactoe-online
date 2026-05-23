// ── State ─────────────────────────────────────────────────────────────────────

let drawerOpen = false;
let activeContact = null;    // {user_id, username}
const contactUnread = {};    // user_id → unread count
const contactNames = {};    // user_id → username
const contactInvites = {};   // user_id → invite payloads
const contactPresence = {};
const contactOfflineTimers = {};

function getActiveWs() {
    if (typeof hubWs !== 'undefined' && hubWs && hubWs.readyState === WebSocket.OPEN) return hubWs;
    if (typeof matchWs !== 'undefined' && matchWs && matchWs.readyState === WebSocket.OPEN) return matchWs;
    return null;
}

// ── Contacts ──────────────────────────────────────────────────────────────────

async function loadContacts() {
    try {
        const res = await fetch('/messages/contacts');
        if (res.ok) {
            const list = await res.json();
            list.forEach(c => {
                contactUnread[c.user_id] = c.unread_count;
                contactNames[c.user_id] = c.username;
                if (c.avatar_url) playerAvatars[c.user_id] = c.avatar_url;
                upsertContact(c);
            });
        }
    } catch (_) { }
    seedContactsFromContext();
    if (document.getElementById('contacts-list').children.length === 0) {
        document.getElementById('no-contacts').classList.remove('hidden');
    }
    updateTotalBadge();
}

function seedContactsFromContext() {
    if (!Array.isArray(window.CHAT_CONTACTS)) return;
    window.CHAT_CONTACTS.forEach(c => {
        if (!c || !c.user_id || !c.username) return;
        contactUnread[c.user_id] = contactUnread[c.user_id] || 0;
        contactNames[c.user_id] = c.username;
        upsertContact({ user_id: c.user_id, username: c.username });
    });
}

function getPresenceMeta(userId) {
    const presence = contactPresence[userId];
    if (presence?.playing) {
        return { label: t('chat_presence_playing'), dot: 'bg-amber-400', badge: 'border-amber-700 text-amber-300' };
    }
    if (presence?.online) {
        return { label: t('chat_presence_online'), dot: 'bg-emerald-400', badge: 'border-emerald-700 text-emerald-300' };
    }
    return { label: t('chat_presence_offline'), dot: 'bg-gray-600', badge: 'border-gray-700 text-gray-500' };
}

function updateDrawerTitle() {
    const title = document.getElementById('drawer-title');
    if (!title) return;
    if (!activeContact) {
        title.textContent = t('chat_messages');
        return;
    }
    const meta = getPresenceMeta(activeContact.user_id);
    const uid = activeContact.user_id;
    title.innerHTML = `
        <span class="flex min-w-0 items-center gap-2">
            ${renderAvatar(uid, activeContact.username, { size: "w-8 h-8", textSize: "text-sm" })}
            <span class="truncate">${activeContact.username}</span>
            <span class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${meta.badge}">
                <span class="h-1.5 w-1.5 rounded-full ${meta.dot}"></span>
                ${meta.label}
            </span>
        </span>
    `;
}

function updateChatPresence(players) {
    (players || []).forEach(player => {
        if (!player?.user_id) return;
        contactPresence[player.user_id] = {
            online: true,
            playing: Boolean(player.playing),
            username: player.username,
        };
        if (player.username) contactNames[player.user_id] = player.username;
        if (player.avatar_url) playerAvatars[player.user_id] = player.avatar_url;
    });

    Object.entries(contactNames).forEach(([userId, username]) => {
        if (userId !== String(CURRENT_USER_ID) && userId in contactUnread) {
            upsertContact({ user_id: userId, username });
        }
    });
    updateDrawerTitle();
}

function applyPresenceSnapshot(players, onChange) {
    const nowPresent = new Map();
    (players || []).forEach(player => {
        if (player?.user_id) nowPresent.set(player.user_id, player);
    });

    Object.keys(contactPresence).forEach(userId => {
        if (nowPresent.has(userId) || contactOfflineTimers[userId]) return;
        contactOfflineTimers[userId] = setTimeout(() => {
            if (!contactPresence[userId]) return;
            contactPresence[userId] = { online: false, playing: false };
            delete contactOfflineTimers[userId];
            updateChatPresence(getStablePresencePlayers());
            if (typeof onChange === 'function') onChange(getStablePresencePlayers());
        }, 3000);
    });

    nowPresent.forEach((player, userId) => {
        if (contactOfflineTimers[userId]) {
            clearTimeout(contactOfflineTimers[userId]);
            delete contactOfflineTimers[userId];
        }
        contactPresence[userId] = {
            online: true,
            playing: Boolean(player.playing),
            username: player.username,
            avatar_url: player.avatar_url || undefined,
        };
        if (player.username) contactNames[userId] = player.username;
        if (player.avatar_url) playerAvatars[userId] = player.avatar_url;
    });

    const stablePlayers = getStablePresencePlayers();
    updateChatPresence(stablePlayers);
    if (typeof onChange === 'function') onChange(stablePlayers);
}

function getStablePresencePlayers() {
    return Object.entries(contactPresence)
        .filter(([, presence]) => presence.online)
        .map(([userId, presence]) => ({
            user_id: userId,
            username: presence.username || contactNames[userId] || 'Player',
            playing: Boolean(presence.playing),
        }));
}

function contactAvatarHtml(userId, username, presenceDot) {
    return renderAvatar(userId, username, { presenceDot });
}

function upsertContact(c) {
    const list = document.getElementById('contacts-list');
    document.getElementById('no-contacts').classList.add('hidden');
    let el = document.getElementById(`contact-${c.user_id}`);
    if (!el) {
        el = document.createElement('div');
        el.id = `contact-${c.user_id}`;
        el.className = 'flex items-center gap-3 px-4 py-3 hover:bg-gray-800 cursor-pointer transition-colors';
        el.addEventListener('click', () => openThread(c.user_id, contactNames[c.user_id] || c.username));
        list.prepend(el);
    }
    contactNames[c.user_id] = c.username;
    const unread = contactUnread[c.user_id] || 0;
    const presence = getPresenceMeta(c.user_id);
    el.innerHTML = `
        ${contactAvatarHtml(c.user_id, c.username, presence.dot)}
        <div class="min-w-0 flex-1">
            <div class="truncate text-sm font-medium">${c.username}</div>
            <div class="mt-0.5 text-[11px] leading-none ${presence.badge.split(' ').find(c => c.startsWith('text-'))}">
                ${presence.label}
            </div>
        </div>
        ${unread > 0
            ? `<span class="min-w-5 h-5 px-1 bg-red-500 rounded-full text-xs
                           flex items-center justify-center font-bold leading-none">
                   ${unread > 99 ? '99+' : unread}
               </span>`
            : ''}
    `;
}

function updateTotalBadge() {
    const total = Object.values(contactUnread).reduce((s, n) => s + n, 0);
    const badge = document.getElementById('drawer-badge');
    if (total > 0) {
        badge.textContent = total > 99 ? '99+' : String(total);
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

// ── Drawer open / close ───────────────────────────────────────────────────────

function dismissInviteLocally(matchId) {
    Object.keys(contactInvites).forEach(userId => {
        const hasInvite = contactInvites[userId].some(invite => invite.match_id === matchId);
        if (hasInvite && contactUnread[userId] > 0) {
            contactUnread[userId] -= 1;
            upsertContact({ user_id: userId, username: contactNames[userId] || 'Player' });
        }
    });
    updateTotalBadge();
    updateThreadInviteButton();
}

function toggleDrawer() {
    if (drawerOpen) closeDrawer(); else openDrawer();
}

function openDrawer() {
    drawerOpen = true;
    const drawer = document.getElementById('chat-drawer');
    gsap.set(drawer, { x: '100%' });
    drawer.classList.remove('hidden');
    gsap.to(drawer, { x: 0, duration: 0.3, ease: 'power2.out' });
}

function closeDrawer() {
    drawerOpen = false;
    const drawer = document.getElementById('chat-drawer');
    gsap.to(drawer, {
        x: '100%', duration: 0.25, ease: 'power2.in',
        onComplete: () => drawer.classList.add('hidden'),
    });
}

function showContactsView() {
    activeContact = null;
    document.getElementById('contacts-view').classList.remove('hidden');
    document.getElementById('thread-view').classList.add('hidden');
    updateDrawerTitle();
    document.getElementById('drawer-back').classList.add('hidden');
    updateThreadInviteButton();
}

// ── Thread ────────────────────────────────────────────────────────────────────

async function openThread(userId, username) {
    activeContact = { user_id: userId, username };
    contactNames[userId] = username;

    contactUnread[userId] = 0;
    upsertContact({ user_id: userId, username });
    updateTotalBadge();

    document.getElementById('contacts-view').classList.add('hidden');
    document.getElementById('thread-view').classList.remove('hidden');
    updateDrawerTitle();
    document.getElementById('drawer-back').classList.remove('hidden');

    const thread = document.getElementById('thread-messages');
    thread.innerHTML = '';

    let threadGames = [];
    try {
        const res = await fetch(`/messages/${userId}`);
        if (res.ok) {
            const data = await res.json();
            const msgs = Array.isArray(data) ? data : (data.messages || []);
            const invites = Array.isArray(data?.invites) ? data.invites : [];
            threadGames = Array.isArray(data?.games) ? data.games : [];
            contactInvites[userId] = invites.map(invite => ({
                ...invite,
                from_user_id: invite.from_user_id || userId,
                from_username: invite.from_username || username,
            }));
            const items = [
                ...msgs.map(m => ({ ...m, _type: 'message' })),
                ...threadGames.map(g => ({ ...g, _type: 'game' })),
            ].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
            items.forEach(item => {
                if (item._type === 'message') appendMessage(item.sender_id, item.content, false);
                else appendGameResult(item, false);
            });
        }
    } catch (_) { }
    renderInviteCards(userId, false);
    appendGameSummary(threadGames);
    updateThreadInviteButton();

    requestAnimationFrame(scrollThreadToBottom);

    const ws = getActiveWs();
    if (ws) ws.send(JSON.stringify({ type: 'mark_read', sender_id: userId }));
}

function appendMessage(senderId, content, animate = true) {
    const thread = document.getElementById('thread-messages');
    const isMine = senderId === CURRENT_USER_ID;
    const tmpl = document.getElementById('message-template');
    const row = tmpl.content.cloneNode(true).querySelector('.msg-row');
    const bubble = row.querySelector('.msg-bubble');

    row.classList.add(isMine ? 'justify-end' : 'justify-start');
    bubble.textContent = content;
    bubble.classList.add(
        isMine ? 'bg-indigo-600' : 'bg-gray-700',
        isMine ? 'text-white' : 'text-gray-100',
    );

    thread.appendChild(row);
    thread.scrollTop = thread.scrollHeight;

    if (animate) {
        gsap.from(row, { x: isMine ? 40 : -40, opacity: 0, duration: 0.4, ease: 'back.out(1.7)' });
    }
}

function appendGameResult(game, animate = true) {
    const thread = document.getElementById('thread-messages');
    const el = document.createElement('div');
    el.className = 'flex justify-center my-2';

    let label, color;
    if (!game.winner_id) {
        label = t('game_draw'); color = 'text-gray-400';
    } else if (game.winner_id === String(CURRENT_USER_ID)) {
        label = t('game_you_won'); color = 'text-emerald-400';
    } else {
        label = t('game_you_lost'); color = 'text-red-400';
    }

    const role = game.my_role
        ? `<span class="text-gray-500">· ${game.my_role.toUpperCase()}</span>`
        : '';

    el.innerHTML = `
        <a href="/match/${game.match_id}"
           class="inline-flex items-center gap-1.5 px-3 py-1 bg-gray-800
                  rounded-full border border-gray-700 text-xs select-none
                  hover:border-gray-500 transition-colors cursor-pointer">
            <span class="font-semibold ${color}">${label}</span>
            ${role}
        </a>
    `;

    thread.appendChild(el);
    if (animate) {
        gsap.from(el, { y: 10, opacity: 0, duration: 0.3, ease: 'power2.out' });
    }
}

function appendGameSummary(games) {
    if (!games.length) return;
    const thread = document.getElementById('thread-messages');
    let wins = 0, losses = 0, draws = 0;
    games.forEach(g => {
        if (!g.winner_id) draws++;
        else if (g.winner_id === String(CURRENT_USER_ID)) wins++;
        else losses++;
    });
    const parts = [];
    if (wins) parts.push(wins === 1 ? t('stat_win') : t('stat_wins', { n: wins }));
    if (losses) parts.push(losses === 1 ? t('stat_loss') : t('stat_losses', { n: losses }));
    if (draws) parts.push(draws === 1 ? t('stat_draw') : t('stat_draws', { n: draws }));
    const el = document.createElement('div');
    el.id = 'game-summary';
    el.className = 'flex justify-center mt-3 mb-1';
    el.innerHTML = `
        <span class="text-[11px] text-gray-600 select-none">${parts.join(' · ')}</span>
    `;
    thread.appendChild(el);
}

function appendInviteCard(invite, userId, animate = true) {
    const thread = document.getElementById('thread-messages');
    const isMine = invite.from_user_id === CURRENT_USER_ID;
    const tmpl = document.getElementById('invite-template');
    const el = tmpl.content.cloneNode(true).firstElementChild;
    el.id = `invite-${invite.match_id}`;

    el.querySelector('p').textContent = isMine
        ? t('chat_you_invited', {
            name: contactNames[userId] || activeContact?.username || '?'
        })
        : t('chat_invited_you', {
            name: contactNames[invite.from_user_id] || '?'
        })

    el.querySelector('.invite-join').href = `/match/${invite.match_id}`;
    thread.appendChild(el);
    thread.scrollTop = thread.scrollHeight;
    if (animate) {
        gsap.from(el, { y: 20, opacity: 0, duration: 0.4, ease: 'back.out(1.7)' });
    }
}

function isCurrentMatchInvite(invite) {
    return typeof MATCH_ID !== 'undefined' && invite?.match_id === MATCH_ID;
}

function isCurrentMatchContact(userId) {
    return typeof MATCH_PLAYERS !== 'undefined'
        && typeof MATCH_ID !== 'undefined'
        && Array.isArray(MATCH_PLAYERS)
        && MATCH_PLAYERS.some(p => p.user_id === userId);
}

function visibleInvitesFor(userId) {
    return (contactInvites[userId] || []).filter(invite => !isCurrentMatchInvite(invite));
}

function renderInviteCards(userId, animate = true) {
    visibleInvitesFor(userId).forEach(invite => {
        if (document.getElementById(`invite-${invite.match_id}`)) return;
        appendInviteCard(invite, userId, animate);
    });
}

function showThreadInviteButton(btn) {
    if (btn.dataset.visible === 'true') return;
    btn.dataset.visible = 'true';
    btn.classList.remove('hidden');
    document.getElementById('thread-messages')?.classList.add('pb-14');

    if (typeof gsap === 'undefined') return;
    gsap.killTweensOf(btn);
    gsap.fromTo(
        btn,
        { y: 48, opacity: 0, scale: 0.96 },
        { y: 0, opacity: 1, scale: 1, duration: 0.32, ease: 'back.out(1.35)' },
    );
}

function hideThreadInviteButton(btn) {
    if (btn.dataset.visible !== 'true') {
        btn.classList.add('hidden');
        document.getElementById('thread-messages')?.classList.remove('pb-14');
        return;
    }
    btn.dataset.visible = 'false';

    if (typeof gsap === 'undefined') {
        btn.classList.add('hidden');
        document.getElementById('thread-messages')?.classList.remove('pb-14');
        return;
    }

    gsap.killTweensOf(btn);
    gsap.to(btn, {
        y: 48,
        opacity: 0,
        scale: 0.96,
        duration: 0.24,
        ease: 'power2.in',
        onComplete: () => {
            btn.classList.add('hidden');
            document.getElementById('thread-messages')?.classList.remove('pb-14');
        },
    });
}

function updateThreadInviteButton() {
    const btn = document.getElementById('thread-invite-btn');
    if (!btn) return;
    if (!activeContact || activeContact.user_id === CURRENT_USER_ID) {
        hideThreadInviteButton(btn);
        requestAnimationFrame(scrollThreadToBottom);
        return;
    }
    if (isCurrentMatchContact(activeContact.user_id)) {
        hideThreadInviteButton(btn);
        requestAnimationFrame(scrollThreadToBottom);
        return;
    }
    const hasInvite = visibleInvitesFor(activeContact.user_id).length > 0;
    if (hasInvite) {
        hideThreadInviteButton(btn);
    } else {
        showThreadInviteButton(btn);
    }
    requestAnimationFrame(scrollThreadToBottom);
}

function scrollThreadToBottom() {
    const thread = document.getElementById('thread-messages');
    if (thread) thread.scrollTop = thread.scrollHeight;
}

async function sendThreadInvite() {
    if (!activeContact || activeContact.user_id === CURRENT_USER_ID) return;
    const res = await fetch('/match/invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_user_id: activeContact.user_id }),
    });
    const data = await res.json();
    if (!res.ok || !data.match_id) return;

    contactInvites[activeContact.user_id] ||= [];
    if (!contactInvites[activeContact.user_id].some(invite => invite.match_id === data.match_id)) {
        contactInvites[activeContact.user_id].push({
            match_id: data.match_id,
            from_user_id: data.from_user_id || CURRENT_USER_ID,
            from_username: data.from_user_id && data.from_user_id !== CURRENT_USER_ID
                ? activeContact.username
                : CURRENT_USERNAME,
        });
    }
    renderInviteCards(activeContact.user_id);
    updateThreadInviteButton();
    location.href = `/match/${data.match_id}`;
}

function toggleChatEmojiPicker() {
    document.getElementById('chat-emoji-picker').classList.toggle('hidden');
}

function appendChatEmoji(emoji) {
    const input = document.getElementById('chat-input');
    input.value += emoji;
    input.focus();
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('#chat-emoji-btn') && !e.target.closest('#chat-emoji-picker')) {
        document.getElementById('chat-emoji-picker')?.classList.add('hidden');
    }
});

function sendChatMessage() {
    if (!activeContact) return;
    const input = document.getElementById('chat-input');
    const content = input.value.trim();
    if (!content) return;
    const ws = getActiveWs();
    if (!ws) return;
    ws.send(JSON.stringify({ type: 'send_message', receiver_id: activeContact.user_id, content }));
    input.value = '';
}

// ── WS handlers (called from hub.js / match.js) ───────────────────────────────

function onNewMessage(data) {
    const isFromMe = data.sender_id === CURRENT_USER_ID;
    const otherId = isFromMe ? data.receiver_id : data.sender_id;
    const otherName = isFromMe ? data.receiver_username : data.sender_username;

    contactNames[otherId] = otherName;
    if (!isFromMe) playNotificationSound();

    if (activeContact && activeContact.user_id === otherId && drawerOpen) {
        appendMessage(data.sender_id, data.content);
        if (!isFromMe) {
            const ws = getActiveWs();
            if (ws) ws.send(JSON.stringify({ type: 'mark_read', sender_id: data.sender_id }));
        }
    } else if (!isFromMe) {
        contactUnread[otherId] = (contactUnread[otherId] || 0) + 1;
    }

    upsertContact({ user_id: otherId, username: otherName });
    updateTotalBadge();
}

function onMessageRead(_data) {
    // Sender's messages were read — no visual update needed on sender side
}

function onInviteReceived(data, playSound = true) {
    const userId = data.from_user_id;
    const username = data.from_username;
    if (isCurrentMatchInvite(data)) {
        contactNames[userId] = username;
        contactInvites[userId] ||= [];
        if (!contactInvites[userId].some(invite => invite.match_id === data.match_id)) {
            contactInvites[userId].push(data);
        }
        updateThreadInviteButton();
        return;
    }
    if (playSound) playNotificationSound();

    contactNames[userId] = username;
    contactInvites[userId] ||= [];
    if (!contactInvites[userId].some(invite => invite.match_id === data.match_id)) {
        contactInvites[userId].push(data);
    }

    if (activeContact && drawerOpen && activeContact.user_id === userId) {
        renderInviteCards(userId);
    } else {
        contactUnread[userId] = (contactUnread[userId] || 0) + 1;
    }

    upsertContact({ user_id: userId, username });
    updateTotalBadge();
    updateThreadInviteButton();
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    loadContacts();
    document.getElementById('chat-input').addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
    });
});
