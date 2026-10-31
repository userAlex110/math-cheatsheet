/* 数学小抄 · 交互：主题 / 章节高亮 / 背诵进度 / 自测 / 搜索 / PWA */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ------------------------------------------------------------ 主题 */
  const themeBtn = $("#themeBtn");
  const metaTheme = $('meta[name="theme-color"]');

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    if (metaTheme) metaTheme.content = theme === "dark" ? "#15161A" : "#FCFCFA";
    if (themeBtn) {
      const label = theme === "dark" ? "切换到浅色模式" : "切换到深色模式";
      themeBtn.setAttribute("aria-label", label);
      themeBtn.title = label;
    }
  }

  applyTheme(document.documentElement.dataset.theme || "light");

  themeBtn?.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(next);
    try {
      localStorage.setItem("sx.theme", next);
    } catch (_) {}
  });

  /* ------------------------------------------------------------ 提示 */
  const toastEl = $("#toast");
  let toastTimer = 0;

  function toast(message, ms = 2600) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.add("on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("on"), ms);
  }

  /* ------------------------------------------------------------ 进度 */
  const DONE_KEY = "sx.done.v1";
  const marks = $$(".mark");
  let done = new Set();

  try {
    const saved = JSON.parse(localStorage.getItem(DONE_KEY) || "[]");
    if (Array.isArray(saved)) done = new Set(saved.filter((id) => typeof id === "string"));
  } catch (_) {}

  function saveDone() {
    try {
      localStorage.setItem(DONE_KEY, JSON.stringify(Array.from(done)));
    } catch (_) {}
  }

  function renderProgress() {
    marks.forEach((btn) => {
      const on = done.has(btn.dataset.id);
      btn.classList.toggle("done", on);
      btn.setAttribute("aria-pressed", String(on));
    });
    const total = marks.length || 1;
    const pct = (done.size / total) * 100;
    const c1 = $("#doneCount");
    const c2 = $("#doneCount2");
    if (c1) c1.textContent = String(done.size);
    if (c2) c2.textContent = String(done.size);
    const b1 = $("#progressBar");
    const b2 = $("#progressBar2");
    if (b1) b1.style.width = pct + "%";
    if (b2) b2.style.width = pct + "%";
  }

  document.addEventListener("click", (event) => {
    const btn = event.target.closest(".mark");
    if (!btn) return;
    const id = btn.dataset.id;
    if (done.has(id)) done.delete(id);
    else done.add(id);
    saveDone();
    renderProgress();
    if (done.size === marks.length && marks.length > 0) {
      toast("这一遍全背完了。合上小抄，复述一遍试试。");
    }
  });

  $("#resetBtn")?.addEventListener("click", () => {
    if (!done.size) return;
    if (!confirm("清空全部背诵进度？")) return;
    done.clear();
    saveDone();
    renderProgress();
    toast("进度已清空");
  });

  renderProgress();

  /* ------------------------------------------------------------ 自测 */
  const quizBtn = $("#quizBtn");
  quizBtn?.addEventListener("click", () => {
    const on = document.body.classList.toggle("quiz");
    quizBtn.setAttribute("aria-pressed", String(on));
    if (!on) $$(".math.on").forEach((el) => el.classList.remove("on"));
    toast(on ? "自测模式：点公式揭开，再点盖回" : "已退出自测");
  });

  document.addEventListener("click", (event) => {
    if (!document.body.classList.contains("quiz")) return;
    const math = event.target.closest(".math");
    if (!math) return;
    event.preventDefault();
    math.classList.toggle("on");
  });

  /* ------------------------------------------------------------ 章节高亮 */
  const chapters = $$(".chapter");
  const navLinks = $$("[data-ch]");
  const chipWrap = $(".chips");
  let activeId = "";

  function updateActive() {
    if (!chapters.length) return;
    const line = window.scrollY + 120;
    let current = chapters[0];
    for (const ch of chapters) {
      if (ch.getBoundingClientRect().top + window.scrollY <= line) current = ch;
    }
    if (current.id === activeId) return;
    activeId = current.id;
    navLinks.forEach((a) => a.classList.toggle("on", a.dataset.ch === activeId));
    const chip = $(`.chip[data-ch="${activeId}"]`);
    if (chip && chipWrap && chipWrap.scrollWidth > chipWrap.clientWidth) {
      chipWrap.scrollTo({
        left: chip.offsetLeft - chipWrap.clientWidth / 2 + chip.offsetWidth / 2,
        behavior: reduceMotion ? "auto" : "smooth",
      });
    }
  }

  let ticking = false;
  window.addEventListener(
    "scroll",
    () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        updateActive();
        ticking = false;
      });
    },
    { passive: true }
  );
  window.addEventListener("resize", updateActive, { passive: true });
  updateActive();

  /* ------------------------------------------------------------ 搜索 */
  const layer = $("#searchLayer");
  const input = $("#searchInput");
  const results = $("#searchResults");
  const meta = $("#searchMeta");
  const searchBtn = $("#searchBtn");
  const coverSearch = $("#coverSearch");
  const closeBtn = $("#searchClose");
  let index = null;
  let indexPromise = null;
  let hits = [];
  let active = 0;
  let lastFocus = null;

  const esc = (s) =>
    String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function loadIndex() {
    if (indexPromise) return indexPromise;
    indexPromise = fetch("/assets/search.json")
      .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then((data) => {
        index = data;
        return data;
      })
      .catch((err) => {
        indexPromise = null;
        throw err;
      });
    return indexPromise;
  }

  function compact(s) {
    return String(s).toLowerCase().replace(/\s+/g, "");
  }

  function snippetFor(item, q) {
    const text = item.text || "";
    const lower = text.toLowerCase();
    let pos = lower.indexOf(q);
    let source = text;

    if (pos < 0) {
      source = String(item.tex || "")
        .replace(/\\[a-zA-Z]+/g, " ")
        .replace(/[{}]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
      pos = source.toLowerCase().indexOf(q);
      if (pos < 0) return source.slice(0, 70);
    }

    const start = Math.max(0, pos - 24);
    const end = Math.min(source.length, pos + q.length + 54);
    const raw = source.slice(start, end);
    const offset = pos - start;
    return (
      (start > 0 ? "…" : "") +
      esc(raw.slice(0, offset)) +
      "<mark>" +
      esc(raw.slice(offset, offset + q.length)) +
      "</mark>" +
      esc(raw.slice(offset + q.length)) +
      (end < source.length ? "…" : "")
    );
  }

  function renderResults(q) {
    if (!results || !meta) return;
    const query = q.trim().toLowerCase();
    if (!query) {
      results.innerHTML = "";
      meta.textContent = "输入关键词，例如「双纽线」「法线」「罗尔」";
      hits = [];
      active = 0;
      return;
    }
    if (!index) {
      meta.textContent = "搜索索引加载中…";
      return;
    }

    const nq = compact(query);
    hits = index
      .map((item, order) => {
        const title = compact(item.num + " " + item.title);
        const body = compact(item.text);
        const tex = compact(item.tex);
        let score = 0;
        if (title.includes(nq)) score += 120;
        if (item.num.toLowerCase().startsWith(query)) score += 70;
        if (body.includes(nq)) score += 45 + Math.min(25, body.split(nq).length - 1);
        if (tex.includes(nq)) score += 25;
        return { item, score, order };
      })
      .filter((hit) => hit.score > 0)
      .sort((a, b) => b.score - a.score || a.order - b.order)
      .slice(0, 24)
      .map((hit) => hit.item);

    active = 0;
    if (!hits.length) {
      results.innerHTML = '<p class="s-none">没有匹配。试试「双纽线」「法线」「罗尔」「拐点」。</p>';
      meta.textContent = "0 节";
      return;
    }

    meta.textContent = `找到 ${hits.length} 节`;
    results.innerHTML = hits
      .map(
        (item, i) =>
          `<a class="s-item${i === 0 ? " on" : ""}" href="#${item.id}" data-id="${item.id}">` +
          `<div class="s-ch">${esc(item.ch)}</div>` +
          `<div class="s-title">${item.num ? `<span class="n">${esc(item.num)}</span>` : ""}${item.titleHtml}</div>` +
          `<p class="s-snip">${snippetFor(item, query)}</p>` +
          `</a>`
      )
      .join("");
  }

  function moveActive(delta) {
    if (!hits.length) return;
    active = (active + delta + hits.length) % hits.length;
    $$(".s-item", results).forEach((el, i) => el.classList.toggle("on", i === active));
    const el = $$(".s-item", results)[active];
    el?.scrollIntoView({ block: "nearest" });
  }

  function openSearch() {
    if (!layer) return;
    lastFocus = document.activeElement;
    layer.hidden = false;
    document.documentElement.style.overflow = "hidden";
    input.value = "";
    renderResults("");
    input.focus();
    loadIndex()
      .then(() => {
        if (input.value.trim()) renderResults(input.value);
      })
      .catch(() => {
        if (meta) meta.textContent = "搜索索引加载失败，刷新页面再试。";
      });
  }

  function closeSearch() {
    if (!layer || layer.hidden) return;
    layer.hidden = true;
    document.documentElement.style.overflow = "";
    if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
  }

  function jumpTo(id) {
    const target = document.getElementById(id);
    if (!target) return;
    const head = target.querySelector(".t-head") || target;
    history.replaceState(null, "", "#" + id);
    head.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    head.classList.add("flash");
    setTimeout(() => head.classList.remove("flash"), 1400);
  }

  searchBtn?.addEventListener("click", openSearch);
  coverSearch?.addEventListener("click", openSearch);
  closeBtn?.addEventListener("click", closeSearch);
  layer?.addEventListener("click", (event) => {
    if (event.target === layer) closeSearch();
  });

  input?.addEventListener("input", () => renderResults(input.value));

  input?.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveActive(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      moveActive(-1);
    } else if (event.key === "Enter") {
      const item = hits[active];
      if (item) {
        event.preventDefault();
        closeSearch();
        jumpTo(item.id);
      }
    }
  });

  results?.addEventListener("click", (event) => {
    const link = event.target.closest(".s-item");
    if (!link) return;
    event.preventDefault();
    closeSearch();
    jumpTo(link.dataset.id);
  });

  document.addEventListener("keydown", (event) => {
    const typing =
      event.target instanceof HTMLElement &&
      (event.target.isContentEditable ||
        ["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName));

    if (layer && !layer.hidden) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeSearch();
      }
      return;
    }

    if (typing) return;
    const isSlash = event.key === "/" && !event.metaKey && !event.ctrlKey && !event.altKey;
    const isCmdK = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";
    if (isSlash || isCmdK) {
      event.preventDefault();
      openSearch();
    }
  });

  /* ------------------------------------------------------------ 表格横向提示 */
  const tableWraps = $$(".table-wrap");

  function syncTable(wrap) {
    const more = wrap.scrollWidth > wrap.clientWidth + 4;
    wrap.classList.toggle("is-scrollable", more);
    wrap.classList.toggle(
      "at-end",
      wrap.scrollLeft + wrap.clientWidth >= wrap.scrollWidth - 4
    );
  }

  if (tableWraps.length) {
    const syncAll = () => tableWraps.forEach(syncTable);
    tableWraps.forEach((wrap) =>
      wrap.addEventListener("scroll", () => syncTable(wrap), { passive: true })
    );
    window.addEventListener("resize", syncAll, { passive: true });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(syncAll);
    syncAll();
  }

  /* ------------------------------------------------------------ PWA */
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    });
  }
})();
