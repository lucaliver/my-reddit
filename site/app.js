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

  // ── State ─────────────────────────────────────────────────────
  let currentView = "grouped"; // 'grouped' | 'feed'
  let activeFilters = new Set();
  let digestData = null;
  let entranceDone = false; // after first reveal, skip entrance animations

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

  function isRead(url) {
    return getReadSet().has(url);
  }

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
      <span>my-reddit</span>
    `;
    const footerTime = document.getElementById("footer-time");
    if (footerTime) {
      footerTime.textContent = " — " + formatDate(data.generated_at);
    }
  }

  function renderStats(data) {
    statsBar.innerHTML = `
      <span class="stat-text">
        <span class="stat-text__value" id="global-unread-count">0</span> unread
      </span>
    `;
  }

  function renderPost(post, index) {
    const title = escapeHtml(post.title);
    const sub = escapeHtml(post.subreddit);
    const age = timeAgo(post.created_utc);
    const comments = post.num_comments || 0;
    const url = escapeHtml(post.url);
    const read = isRead(post.url);
    
    let previewHtml = "";
    if (post.thumbnail) {
      previewHtml = `<div class="post-item__thumb"><img src="${escapeHtml(post.thumbnail)}" alt="Thumbnail" loading="lazy"></div>`;
    } else if (post.excerpt) {
      previewHtml = `<p class="post-item__excerpt">${escapeHtml(post.excerpt)}</p>`;
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
            ${comments > 0
              ? `<span class="post-item__separator">·</span>
                 <span>${comments} comment${comments !== 1 ? "s" : ""}</span>`
              : ""}
            ${age
              ? `<span class="post-item__separator">·</span>
                 <span>${age}</span>`
              : ""}
          </div>
        </div>
        <span class="post-item__check">✓</span>
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
        <div class="group-card__header" role="button" tabindex="0" aria-expanded="false">
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
    digestEl.innerHTML = digestData.groups.map(renderGroup).join("");
    toolbarEl.style.display = "flex";
    filterCarousel.style.display = "none";

    // After initial entrance, reveal cards immediately
    if (entranceDone) {
      digestEl.querySelectorAll(".group-card").forEach(c => c.classList.add("is-revealed"));
    }

    updateUnreadCounts();
    attachListeners();
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
      btn.addEventListener("click", () => {
        const grp = btn.dataset.group;
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
          } else {
            countEl.textContent = `${unreadCount} unread`;
            countEl.classList.remove("is-empty");
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

  function attachListeners() {
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
  }

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

  // ── Boot ──────────────────────────────────────────────────────

  async function init() {
    try {
      const resp = await fetch(`digest.json?t=${new Date().getTime()}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      digestData = await resp.json();
      
      // Smooth crossfade: loading → content
      loadingEl.classList.add("is-leaving");
      await new Promise(r => setTimeout(r, 250));
      loadingEl.remove();
      
      // Init filters
      if (digestData.groups) {
        digestData.groups.forEach(g => activeFilters.add(g.name));
      }
      
      renderMeta(digestData);
      renderStats(digestData);
      renderFilters();
      renderActiveView();

      // Trigger entrance animation sequence
      requestAnimationFrame(() => {
        revealEntrance();
        // Mark entrance as done after animations settle
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
