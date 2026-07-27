/**
 * my-reddit — Digest Renderer
 *
 * Fetches digest.json and renders the grouped posts.
 * Tracks clicked posts in localStorage and marks them as read.
 */

(function () {
  "use strict";

  // ── DOM refs ──────────────────────────────────────────────────
  const digestEl     = document.getElementById("digest-content");
  const loadingEl    = document.getElementById("loading-state");
  const headerMeta   = document.getElementById("header-meta");
  const statsBar     = document.getElementById("stats-bar");
  const toolbarEl    = document.getElementById("toolbar");
  const btnToggleAll = document.getElementById("btn-toggle-all");
  const topBar       = document.getElementById("top-bar");
  const viewControls = document.getElementById("view-controls");
  const siteFooter   = document.querySelector(".site-footer");

  const filterCarousel = document.getElementById("filter-carousel");
  const btnViewGrouped = document.getElementById("btn-view-grouped");
  const btnViewFeed = document.getElementById("btn-view-feed");
  const btnHideRead = document.getElementById("btn-hide-read");

  const archiveContainer = document.getElementById("archive-container");
  const archiveSelect = document.getElementById("archive-select");
  
  const lightboxModal = document.getElementById("lightbox-modal");
  const lightboxImg = document.getElementById("lightbox-img");
  const lightboxLink = document.getElementById("lightbox-link");
  const lightboxClose = document.getElementById("lightbox-close");
  const lightboxBackdrop = document.getElementById("lightbox-backdrop");
  
  const statsModal = document.getElementById("stats-modal");
  const statsBody = document.getElementById("stats-body");
  const statsClose = document.getElementById("stats-close");
  const statsBackdrop = document.getElementById("stats-backdrop");

  // ── State ─────────────────────────────────────────────────────
  let currentView = "grouped"; // 'grouped' | 'feed'
  let activeFilters = new Set();
  let digestData = null;
  let entranceDone = false; // after first reveal, skip entrance animations
  let hideReadState = false;

  // ── Read-tracking (localStorage) ──────────────────────────────
  const STORAGE_KEY = "myreddit_read";

  function getReadSet() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? new Set(JSON.parse(raw)) : new Set();
    } catch {
      return new Set();
    }
  }

  function markAsRead(url) {
    const readSet = getReadSet();
    readSet.add(url);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...readSet]));
    } catch { /* storage full — ignore */ }
  }

  function unmarkAsRead(url) {
    const readSet = getReadSet();
    readSet.delete(url);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...readSet]));
    } catch { /* storage full — ignore */ }
  }

  function isRead(url) {
    return getReadSet().has(url);
  }

  function getSavedGroupOrder() {
    try {
      const saved = localStorage.getItem("myreddit_group_order");
      return saved ? JSON.parse(saved) : null;
    } catch { return null; }
  }
  
  function saveGroupOrder(order) {
    try { localStorage.setItem("myreddit_group_order", JSON.stringify(order)); } catch {}
  }
  let groupOrder = getSavedGroupOrder();

  // ── Helpers ───────────────────────────────────────────────────

  function timeAgo(isoString) {
    if (!isoString) return "";
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffH = Math.floor(diffMs / 3600000);

    if (diffH < 1) return "just now";
    if (diffH < 24) return diffH + "h ago";
    const diffD = Math.floor(diffH / 24);
    if (diffD === 1) return "1 day ago";
    if (diffD < 7) return diffD + " days ago";
    const diffW = Math.floor(diffD / 7);
    return diffW === 1 ? "1 week ago" : diffW + " weeks ago";
  }

  function formatDate(isoString) {
    if (!isoString) return "—";
    const d = new Date(isoString);
    return d.toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function extractEmoji(name) {
    const match = name.match(/^(\S+)\s+(.+)/);
    // If the first word contains no ASCII letters, treat it as an emoji prefix
    if (match && !/[a-zA-Z]/.test(match[1])) {
      return match[1];
    }
    return "📌";
  }

  function stripEmoji(name) {
    const match = name.match(/^(\S+)\s+(.+)/);
    if (match && !/[a-zA-Z]/.test(match[1])) {
      return match[2];
    }
    return name;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ── Entrance Animation ────────────────────────────────────────

  function revealEntrance() {
    // Choreographed sequence: header → controls → cards → footer
    topBar.classList.add("is-revealed");

    setTimeout(() => {
      viewControls.classList.add("is-revealed");
    }, 120);

    // Stagger each card dynamically
    const cards = digestEl.querySelectorAll(".group-card");
    cards.forEach((card, i) => {
      card.style.animationDelay = `${200 + i * 30}ms`;
      card.classList.add("is-revealed");
    });

    // Footer appears last
    const footerDelay = 200 + cards.length * 30 + 100;
    setTimeout(() => {
      siteFooter.classList.add("is-revealed");
    }, footerDelay);
  }

  function revealFeedPosts() {
    const items = digestEl.querySelectorAll(".feed-list .post-item");
    items.forEach((item, i) => {
      item.style.animationDelay = `${i * 20}ms`;
      item.classList.add("is-revealed");
    });
  }

  // ── Render Functions ──────────────────────────────────────────

  function renderMeta(data) {
    headerMeta.innerHTML = `
      <a href="https://github.com/lucaliver/my-reddit" target="_blank" rel="noopener" class="site-logo">my-reddit</a>
    `;
    const footerTime = document.getElementById("footer-time");
    if (footerTime) {
      footerTime.textContent = " — " + formatDate(data.generated_at);
    }
  }

  function renderStats(data) {
    statsBar.innerHTML = `
      <div style="display: flex; gap: 12px; align-items: center;">
        <span class="stat-text">
          <span class="stat-text__value" id="global-unread-count">0</span> unread
        </span>
        <button class="toolbar__btn" id="btn-show-stats" style="margin: 0;">Stats 📊</button>
      </div>
    `;
    const btn = document.getElementById("btn-show-stats");
    if (btn) btn.addEventListener("click", showStatsModal);
  }

  function renderPost(post, index) {
    const title = escapeHtml(post.title);
    const sub = escapeHtml(post.subreddit);
    const age = timeAgo(post.created_utc);
    const url = escapeHtml(post.url);
    const read = isRead(post.url);
    
    let previewHtml = "";
    if (post.thumbnail) {
      let badgeHtml = "";
      if (post.media_type === "video") badgeHtml = '<span class="media-badge">▶ Video</span>';
      else if (post.media_type === "gallery") badgeHtml = '<span class="media-badge">🖼 Gallery</span>';
      
      previewHtml = `
        <div class="post-item__thumb is-clickable" data-img="${escapeHtml(post.thumbnail)}" data-link="${url}">
          <img src="${escapeHtml(post.thumbnail)}" alt="Thumbnail" loading="lazy" onerror="this.parentElement.style.display='none'">
          ${badgeHtml}
        </div>`;
    }

    return `
      <li class="post-item${read ? " is-read" : ""}" data-url="${url}">
        <span class="post-item__index">${index}</span>
        <div class="post-item__content">
          <a class="post-item__title" href="${url}" target="_blank" rel="noopener">
            ${title}
          </a>
          ${previewHtml}
          <div class="post-item__meta">
            <span class="post-item__sub">r/${sub}</span>
            ${age
              ? `<span class="post-item__separator">·</span>
                 <span>${age}</span>`
              : ""}
          </div>
        </div>
        <button class="post-item__check" aria-label="Toggle read status" title="Mark as read">✓</button>
      </li>
    `;
  }

  function renderGroup(group) {
    const emoji = extractEmoji(group.name);
    const name = escapeHtml(stripEmoji(group.name));
    const subsLabel = escapeHtml(group.subreddits_label);

    const postsHtml = group.posts
      .map((p, i) => renderPost(p, i + 1))
      .join("");

    return `
      <article class="group-card" data-group-name="${escapeHtml(group.name).toLowerCase()}">
        <div class="group-card__header" role="button" tabindex="0" aria-expanded="false" draggable="true" data-group="${escapeHtml(group.name)}">
          <div class="group-card__left">
            <span class="group-card__emoji">${emoji}</span>
            <div class="group-card__info">
              <h2 class="group-card__name">${name}</h2>
              <p class="group-card__subs">${subsLabel}</p>
            </div>
          </div>
          <div class="group-card__right">
            <span class="group-card__count"></span>
            <span class="group-card__chevron">▼</span>
          </div>
        </div>
        <div class="group-card__body">
          <ul class="posts-list">
            ${postsHtml}
          </ul>
        </div>
      </article>
    `;
  }

  function renderGroupedView() {
    let sortedGroups = digestData.groups.slice();
    if (groupOrder) {
      sortedGroups.sort((a, b) => {
        let ia = groupOrder.indexOf(a.name);
        let ib = groupOrder.indexOf(b.name);
        if (ia === -1) ia = 999;
        if (ib === -1) ib = 999;
        return ia - ib;
      });
    }
    digestEl.innerHTML = sortedGroups.map(renderGroup).join("");
    toolbarEl.style.display = "flex";
    filterCarousel.style.display = "none";

    // After initial entrance, reveal cards immediately
    if (entranceDone) {
      digestEl.querySelectorAll(".group-card").forEach(c => c.classList.add("is-revealed"));
    }

    updateUnreadCounts();
    attachListeners();
    attachDragAndDrop();
    updateToggleAllButton();
  }

  function renderFeedView() {
    toolbarEl.style.display = "none";
    filterCarousel.style.display = "flex";

    // Flatten posts and filter by active groups
    let feedPosts = [];
    digestData.groups.forEach(group => {
      if (activeFilters.has(group.name)) {
        feedPosts = feedPosts.concat(group.posts);
      }
    });

    // Sort chronologically (newest first)
    feedPosts.sort((a, b) => new Date(b.created_utc) - new Date(a.created_utc));

    if (feedPosts.length === 0) {
      digestEl.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">📭</div>
          <h2 class="empty-state__title">No posts match your filters</h2>
          <p class="empty-state__text">Try selecting more groups above.</p>
        </div>
      `;
      return;
    }

    const postsHtml = feedPosts.map((p, i) => renderPost(p, i + 1)).join("");
    digestEl.innerHTML = `<ul class="posts-list feed-list">${postsHtml}</ul>`;

    // After initial entrance, reveal posts immediately
    if (entranceDone) {
      digestEl.querySelectorAll(".post-item").forEach(p => p.classList.add("is-revealed"));
    } else {
      revealFeedPosts();
    }

    updateUnreadCounts();
    attachListeners();
  }

  function renderActiveView() {
    if (!digestData || !digestData.groups || digestData.groups.length === 0) {
      digestEl.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">📭</div>
          <h2 class="empty-state__title">No posts this week</h2>
          <p class="empty-state__text">Check back next week for fresh content.</p>
        </div>
      `;
      return;
    }

    if (currentView === "grouped") {
      renderGroupedView();
    } else {
      renderFeedView();
    }
  }

  function renderFilters() {
    if (!digestData || !digestData.groups) return;
    
    filterCarousel.innerHTML = digestData.groups.map(g => {
      const isActive = activeFilters.has(g.name);
      return `<button class="filter-tile ${isActive ? 'is-active' : ''}" data-group="${escapeHtml(g.name)}">${escapeHtml(stripEmoji(g.name))}</button>`;
    }).join("");

    filterCarousel.querySelectorAll(".filter-tile").forEach(btn => {
      let pressTimer = null;
      let isLongPress = false;
      const grp = btn.dataset.group;

      // Handle long press
      btn.addEventListener("pointerdown", (e) => {
        isLongPress = false;
        if (e.pointerType === "mouse" && e.button !== 0) return;
        
        pressTimer = setTimeout(() => {
          isLongPress = true;
          activeFilters.clear();
          activeFilters.add(grp);
          try { if (navigator.vibrate) navigator.vibrate(30); } catch(err){}
          
          renderFilters();
          if (currentView === "feed") {
            renderFeedView();
          }
        }, 400); // 400ms per un long press reattivo
      });

      btn.addEventListener("pointerup", () => {
        if (pressTimer) clearTimeout(pressTimer);
      });
      
      btn.addEventListener("pointerleave", () => {
        if (pressTimer) clearTimeout(pressTimer);
      });
      
      // Prevent default context menu on mobile long press
      btn.addEventListener("contextmenu", (e) => {
        e.preventDefault();
      });

      btn.addEventListener("click", () => {
        if (isLongPress) return; // ignore click if long press fired

        if (activeFilters.has(grp)) {
          activeFilters.delete(grp);
        } else {
          activeFilters.add(grp);
        }
        renderFilters();
        if (currentView === "feed") {
          renderFeedView();
        }
      });
    });
  }

  function updateUnreadCounts() {
    let globalUnread = 0;
    
    if (currentView === "grouped") {
      document.querySelectorAll(".group-card").forEach(card => {
        const unreadCount = card.querySelectorAll(".post-item:not(.is-read)").length;
        globalUnread += unreadCount;
        
        const countEl = card.querySelector(".group-card__count");
        if (countEl) {
          if (unreadCount === 0) {
            countEl.textContent = "All read";
            countEl.classList.add("is-empty");
            if (hideReadState) card.style.display = "none";
            else card.style.display = "";
          } else {
            countEl.textContent = `${unreadCount} unread`;
            countEl.classList.remove("is-empty");
            card.style.display = "";
          }
        }
      });
    } else {
      // Feed view
      globalUnread = document.querySelectorAll(".post-item:not(.is-read)").length;
    }

    const globalCountEl = document.getElementById("global-unread-count");
    if (globalCountEl) {
      globalCountEl.textContent = globalUnread;
    }
  }

  function renderError(message) {
    loadingEl.remove();
    digestEl.innerHTML = `
      <div class="error-state">
        <h2 class="error-state__title">Failed to load digest</h2>
        <p class="error-state__text">${escapeHtml(message)}</p>
      </div>
    `;
  }

  // ── Interactions ──────────────────────────────────────────────

  function toggleCard(card) {
    const isOpen = card.classList.toggle("is-open");
    const header = card.querySelector(".group-card__header");
    if (header) header.setAttribute("aria-expanded", isOpen ? "true" : "false");
    updateToggleAllButton();
  }

  function updateToggleAllButton() {
    if (!btnToggleAll || currentView !== "grouped") return;
    const cards = document.querySelectorAll(".group-card");
    const openCards = document.querySelectorAll(".group-card.is-open");
    if (openCards.length === cards.length && cards.length > 0) {
      btnToggleAll.textContent = "Collapse all";
    } else {
      btnToggleAll.textContent = "Expand all";
    }
  }

  function attachDragAndDrop() {
    let draggedCard = null;
    document.querySelectorAll(".group-card").forEach(card => {
      const header = card.querySelector(".group-card__header");
      header.addEventListener("dragstart", (e) => {
        draggedCard = card;
        card.classList.add("is-dragging");
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", "");
      });
      header.addEventListener("dragend", () => {
        card.classList.remove("is-dragging");
        draggedCard = null;
        const newOrder = Array.from(digestEl.querySelectorAll(".group-card")).map(c => c.querySelector(".group-card__header").dataset.group);
        saveGroupOrder(newOrder);
        groupOrder = newOrder;
      });
      card.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        if (draggedCard && draggedCard !== card) {
          const rect = card.getBoundingClientRect();
          const next = (e.clientY - rect.top)/(rect.bottom - rect.top) > 0.5;
          digestEl.insertBefore(draggedCard, next ? card.nextSibling : card);
        }
      });
    });
  }

  function attachListeners() {
    // Lightbox
    document.querySelectorAll(".post-item__thumb.is-clickable").forEach(thumb => {
      thumb.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        lightboxImg.src = thumb.dataset.img;
        lightboxLink.href = thumb.dataset.link;
        lightboxModal.showModal();
      });
    });

    // Card expand/collapse
    document.querySelectorAll(".group-card__header").forEach((header) => {
      header.addEventListener("click", () => {
        toggleCard(header.closest(".group-card"));
      });
      header.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggleCard(header.closest(".group-card"));
        }
      });
    });

    // Track clicked posts
    document.querySelectorAll(".post-item__title").forEach((link) => {
      link.addEventListener("click", () => {
        const postItem = link.closest(".post-item");
        if (!postItem.classList.contains("is-read")) {
          const url = postItem.dataset.url;
          markAsRead(url);
          postItem.classList.add("is-read");
          updateUnreadCounts();
        }
      });
    });

    // Manual mark read toggle
    document.querySelectorAll(".post-item__check").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        const postItem = btn.closest(".post-item");
        const url = postItem.dataset.url;
        
        if (postItem.classList.contains("is-read")) {
          unmarkAsRead(url);
          postItem.classList.remove("is-read");
        } else {
          markAsRead(url);
          postItem.classList.add("is-read");
        }
        
        updateUnreadCounts();
      });
    });
  }

  function showStatsModal() {
    if (!digestData) return;
    let stats = digestData.stats || {};
    let droppedAge = stats.dropped_age || 0;
    let droppedDup = stats.dropped_duplicates || 0;
    let droppedKw = stats.dropped_keywords || {};
    
    let kwRows = Object.entries(droppedKw)
        .sort((a,b) => b[1] - a[1])
        .map(([kw, c]) => `<tr><td>${escapeHtml(kw)}</td><td>${c}</td></tr>`).join("");
    
    let readSet = getReadSet();
    let groupCounts = {};
    if (digestData.groups) {
      digestData.groups.forEach(g => {
        let readInGroup = g.posts.filter(p => readSet.has(p.url)).length;
        if (readInGroup > 0) groupCounts[g.name] = readInGroup;
      });
    }
    let readRows = Object.entries(groupCounts)
        .sort((a,b) => b[1] - a[1])
        .map(([g, c]) => `<tr><td>${escapeHtml(stripEmoji(g))}</td><td>${c}</td></tr>`).join("");

    statsBody.innerHTML = `
      <h3 style="margin-bottom:8px">Dropped Posts</h3>
      <table class="stats-table">
        <tr><th>Reason</th><th>Count</th></tr>
        <tr><td>Too Old / Too New</td><td>${droppedAge}</td></tr>
        <tr><td>Duplicates (Crossposts)</td><td>${droppedDup}</td></tr>
      </table>
      
      ${kwRows ? `
      <h3 style="margin-bottom:8px">Dropped by Keyword</h3>
      <table class="stats-table">
        <tr><th>Keyword</th><th>Count</th></tr>
        ${kwRows}
      </table>` : ""}
      
      ${readRows ? `
      <h3 style="margin-bottom:8px">Read Links by Group</h3>
      <table class="stats-table">
        <tr><th>Group</th><th>Read Count</th></tr>
        ${readRows}
      </table>` : ""}
    `;
    statsModal.showModal();
  }
  
  if (statsClose) statsClose.addEventListener("click", () => statsModal.close());
  if (statsBackdrop) statsBackdrop.addEventListener("click", () => statsModal.close());
  
  if (lightboxClose) lightboxClose.addEventListener("click", () => lightboxModal.close());
  if (lightboxBackdrop) lightboxBackdrop.addEventListener("click", () => lightboxModal.close());

  // Smart Toggle All (Grouped View only)
  if (btnToggleAll) {
    btnToggleAll.addEventListener("click", () => {
      const cards = document.querySelectorAll(".group-card");
      const openCards = document.querySelectorAll(".group-card.is-open");
      
      if (openCards.length === cards.length && cards.length > 0) {
        cards.forEach(card => card.classList.remove("is-open"));
      } else {
        cards.forEach(card => card.classList.add("is-open"));
      }
      updateToggleAllButton();
    });
  }

  // View Switcher
  btnViewGrouped.addEventListener("click", () => {
    currentView = "grouped";
    btnViewGrouped.classList.add("is-active");
    btnViewFeed.classList.remove("is-active");
    renderActiveView();
  });

  btnViewFeed.addEventListener("click", () => {
    currentView = "feed";
    btnViewFeed.classList.add("is-active");
    btnViewGrouped.classList.remove("is-active");
    renderActiveView();
  });

  if (btnHideRead) {
    btnHideRead.addEventListener("click", () => {
      hideReadState = !hideReadState;
      if (hideReadState) {
        document.body.classList.add("hide-read");
        btnHideRead.classList.add("is-active");
        btnHideRead.setAttribute("aria-checked", "true");
      } else {
        document.body.classList.remove("hide-read");
        btnHideRead.classList.remove("is-active");
        btnHideRead.setAttribute("aria-checked", "false");
      }
      try {
        localStorage.setItem("myreddit_hide_read", hideReadState ? "1" : "0");
      } catch {}
      updateUnreadCounts();
    });
  }

  // ── Boot ──────────────────────────────────────────────────────

  async function loadDigest(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    digestData = await resp.json();
    
    activeFilters.clear();
    if (digestData.groups) {
      digestData.groups.forEach(g => activeFilters.add(g.name));
    }
    
    renderMeta(digestData);
    renderStats(digestData);
    renderFilters();
    renderActiveView();
  }

  async function init() {
    try {
      // 1. Fetch Archive index
      let archiveList = [];
      try {
        const archResp = await fetch(`archive/index.json?t=${new Date().getTime()}`);
        if (archResp.ok) {
          archiveList = await archResp.json();
        }
      } catch {}
      
      if (archiveList.length > 0) {
        archiveContainer.style.display = "block";
        archiveSelect.innerHTML = `<option value="digest.json">Latest Digest</option>` + 
          archiveList.map(a => `<option value="archive/${a.filename}">${a.date}</option>`).join("");
          
        archiveSelect.addEventListener("change", (e) => {
          entranceDone = false;
          topBar.classList.remove("is-revealed");
          viewControls.classList.remove("is-revealed");
          siteFooter.classList.remove("is-revealed");
          
          digestEl.innerHTML = "";
          digestEl.appendChild(loadingEl);
          loadingEl.classList.remove("is-leaving");
          
          loadDigest(e.target.value + `?t=${new Date().getTime()}`).then(() => {
            loadingEl.remove();
            requestAnimationFrame(() => {
              revealEntrance();
              setTimeout(() => { entranceDone = true; }, 600);
            });
          }).catch(err => {
            console.error(err);
            renderError("Could not load selected archive.");
          });
        });
      }

      // Smooth crossfade: loading → content
      loadingEl.classList.add("is-leaving");
      await new Promise(r => setTimeout(r, 250));
      loadingEl.remove();

      // Init hide read state
      try {
        if (localStorage.getItem("myreddit_hide_read") === "1") {
          hideReadState = true;
          document.body.classList.add("hide-read");
          if (btnHideRead) {
            btnHideRead.classList.add("is-active");
            btnHideRead.setAttribute("aria-checked", "true");
          }
        }
      } catch {}

      await loadDigest(`digest.json?t=${new Date().getTime()}`);
      
      requestAnimationFrame(() => {
        revealEntrance();
        setTimeout(() => { entranceDone = true; }, 600);
      });
      
    } catch (err) {
      console.error("Failed to load digest:", err);
      renderError(
        "Could not load digest.json — the digest may not have been generated yet."
      );
    }
  }

  init();
})();
