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
  const btnExpandAll = document.getElementById("btn-expand-all");
  const btnCollapseAll = document.getElementById("btn-collapse-all");

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
    });
  }

  function extractEmoji(name) {
    const match = name.match(
      /^(\p{Emoji_Presentation}|\p{Emoji}\uFE0F)/u
    );
    return match ? match[0] : "📌";
  }

  function stripEmoji(name) {
    return name
      .replace(/^(\p{Emoji_Presentation}|\p{Emoji}\uFE0F)\s*/u, "")
      .trim();
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ── Render Functions ──────────────────────────────────────────

  function renderMeta(data) {
    headerMeta.innerHTML = `
      <span>📰</span>
      <span>${formatDate(data.generated_at)}</span>
    `;
  }

  function renderStats(data) {
    statsBar.innerHTML = `
      <span class="stat-chip">
        <span class="stat-chip__value">${data.total_posts}</span> posts
      </span>
      <span class="stat-chip">
        <span class="stat-chip__value">${data.total_groups}</span> groups
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

    return `
      <li class="post-item${read ? " is-read" : ""}" data-url="${url}">
        <span class="post-item__index">${index}</span>
        <div class="post-item__content">
          <a class="post-item__title" href="${url}" target="_blank" rel="noopener">
            ${title}
          </a>
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
    const postCount = group.posts.length;

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
            <span class="group-card__count">${postCount} post${postCount !== 1 ? "s" : ""}</span>
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

  function renderDigest(data) {
    renderMeta(data);
    renderStats(data);

    if (!data.groups || data.groups.length === 0) {
      digestEl.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">📭</div>
          <h2 class="empty-state__title">No posts this week</h2>
          <p class="empty-state__text">Check back next week for fresh content.</p>
        </div>
      `;
      return;
    }

    digestEl.innerHTML = data.groups.map(renderGroup).join("");
    toolbarEl.style.display = "flex";
    attachListeners();
  }

  function renderError(message) {
    loadingEl.remove();
    digestEl.innerHTML = `
      <div class="error-state">
        <div class="error-state__icon">⚠️</div>
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
        const url = postItem.dataset.url;
        markAsRead(url);
        postItem.classList.add("is-read");
      });
    });
  }

  // Expand / Collapse all
  btnExpandAll.addEventListener("click", () => {
    document.querySelectorAll(".group-card:not(.is-open)").forEach((card) => {
      card.classList.add("is-open");
    });
  });

  btnCollapseAll.addEventListener("click", () => {
    document.querySelectorAll(".group-card.is-open").forEach((card) => {
      card.classList.remove("is-open");
    });
  });

  // ── Boot ──────────────────────────────────────────────────────

  async function init() {
    try {
      const resp = await fetch("digest.json");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const data = await resp.json();
      loadingEl.remove();
      renderDigest(data);
    } catch (err) {
      console.error("Failed to load digest:", err);
      renderError(
        "Could not load digest.json — the digest may not have been generated yet."
      );
    }
  }

  init();
})();
