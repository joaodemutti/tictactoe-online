let searchCurrentPage = 1;
let searchTotalPages = 1;
let searchQuery = '';
let searchDebounce = null;

function openSearchModal() {
    const modal = document.getElementById('search-modal');
    const card = document.getElementById('search-modal-card');
    modal.classList.remove('hidden');
    gsap.fromTo(modal, { opacity: 0 }, { opacity: 1, duration: 0.18, ease: 'power2.out' });
    gsap.fromTo(card, { opacity: 0, scale: 0.93, y: -12 }, { opacity: 1, scale: 1, y: 0, duration: 0.22, ease: 'back.out(1.5)' });
    document.getElementById('search-input').value = '';
    searchCurrentPage = 1;
    runSearch('', 1);
    setTimeout(() => document.getElementById('search-input').focus(), 50);
}

function closeSearchModal() {
    const modal = document.getElementById('search-modal');
    const card = document.getElementById('search-modal-card');
    gsap.to(card, { opacity: 0, scale: 0.93, y: -10, duration: 0.16, ease: 'power2.in' });
    gsap.to(modal, {
        opacity: 0, duration: 0.18, ease: 'power2.in',
        onComplete: () => modal.classList.add('hidden')
    });
}

function searchPage(dir) {
    const next = searchCurrentPage + dir;
    if (next < 1 || next > searchTotalPages) return;
    runSearch(searchQuery, next);
}

async function runSearch(q, page) {
    searchQuery = q;
    const results = document.getElementById('search-results');
    results.innerHTML = `<p class="text-center text-gray-600 text-sm py-4">…</p>`;
    try {
        const res = await fetch(`/players/search?q=${encodeURIComponent(q)}&page=${page}&limit=10`);
        const data = await res.json();
        searchCurrentPage = data.page;
        searchTotalPages = data.pages;

        if (!data.results.length) {
            results.innerHTML = `<p class="text-center text-gray-600 text-sm py-4">${t('search_no_results')}</p>`;
            document.getElementById('search-pagination').classList.add('hidden');
            return;
        }

        results.innerHTML = data.results.map(p => `
            <div class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-800
                        transition-colors cursor-pointer search-player-row"
                 data-user-id="${p.user_id}" data-username="${p.username}">
                ${renderAvatar(p.user_id, p.username, { size: 'w-9 h-9', textSize: 'text-base' })}
                <span class="text-sm font-medium">${p.username}</span>
            </div>
        `).join('');

        data.results.forEach(p => { if (p.avatar_url) playerAvatars[p.user_id] = p.avatar_url; });

        results.querySelectorAll('.search-player-row').forEach(row => {
            row.addEventListener('click', () => {
                closeSearchModal();
                openDrawer();
                openThread(row.dataset.userId, row.dataset.username);
            });
        });

        const pagination = document.getElementById('search-pagination');
        if (data.pages > 1) {
            pagination.classList.remove('hidden');
            document.getElementById('search-page-label').textContent =
                t('search_page', { page: data.page, pages: data.pages });
            document.getElementById('search-prev').disabled = data.page <= 1;
            document.getElementById('search-next').disabled = data.page >= data.pages;
        } else {
            pagination.classList.add('hidden');
        }
    } catch (_) {
        results.innerHTML = `<p class="text-center text-red-400 text-sm py-4">${t('error_could_not_update')}</p>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('search-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeSearchModal();
    });
    document.getElementById('search-input').addEventListener('input', e => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => {
            searchCurrentPage = 1;
            runSearch(e.target.value.trim(), 1);
        }, 300);
    });
});
