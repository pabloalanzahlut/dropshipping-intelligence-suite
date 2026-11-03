(function () {
  "use strict";

  var data    = window.__BRAND__ || {};
  var reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fineHover = matchMedia("(hover: hover) and (pointer: fine)").matches;

  // Helpers
  var $ = function (sel, scope) { return (scope || document).querySelector(sel); };
  var $$ = function (sel, scope) { return Array.from((scope || document).querySelectorAll(sel)); };
  var escHTML = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  };

  function safe(fn, name) {
    try { fn(); } catch (e) { console.warn("[" + name + "] failed:", e); }
  }

  // ─── Splash ───────────────────────────────────────────────────
  function initSplash() {
    var splash = $("[data-splash]");
    if (!splash) return;
    var hide = function () { splash.classList.add("is-out"); };
    if (document.readyState === "complete") setTimeout(hide, 700);
    else window.addEventListener("load", function () { setTimeout(hide, 500); });
    setTimeout(hide, 3800);
  }

  // ─── Nav ──────────────────────────────────────────────────────
  function initNav() {
    var nav    = $("[data-nav]");
    var burger = $("[data-burger]");
    var menu   = $("[data-mobile-menu]");
    if (!nav) return;

    // Solidify on scroll
    var onScroll = function () {
      nav.classList.toggle("is-scrolled", window.scrollY > 40);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    // Burger
    if (burger && menu) {
      burger.addEventListener("click", function () {
        var open = burger.classList.toggle("is-open");
        menu.classList.toggle("is-open", open);
        burger.setAttribute("aria-expanded", open);
        menu.setAttribute("aria-hidden", !open);
      });

      // Close on link click
      $$("a", menu).forEach(function (a) {
        a.addEventListener("click", function () {
          burger.classList.remove("is-open");
          menu.classList.remove("is-open");
          burger.setAttribute("aria-expanded", "false");
          menu.setAttribute("aria-hidden", "true");
        });
      });
    }
  }

  // ─── Smooth anchor scroll ─────────────────────────────────────
  function initSmoothScroll() {
    document.addEventListener("click", function (e) {
      var a = e.target.closest('a[href^="#"]');
      if (!a) return;
      var id = a.getAttribute("href");
      if (!id || id === "#") return;
      var target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      var navOffset = 84;
      window.scrollTo({
        top: target.getBoundingClientRect().top + window.scrollY - navOffset,
        behavior: reduced ? "auto" : "smooth",
      });
    });
  }

  // ─── Reveal on scroll (IntersectionObserver) ──────────────────
  function initReveals() {
    var items = $$(".reveal");
    if (!items.length) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.04, rootMargin: "0px 0px -2% 0px" });

    items.forEach(function (el) { observer.observe(el); });

    // 6s safety net
    setTimeout(function () {
      $$(".reveal:not(.is-visible)").forEach(function (el) {
        if (el.getBoundingClientRect().top < window.innerHeight + 200) {
          el.classList.add("is-visible");
        }
      });
    }, 6000);
  }

  // ─── Hero title word split animation ──────────────────────────
  function initHeroTitle() {
    var title = $(".hero-title[data-split]");
    if (!title) return;

    // Preserve childNodes (BR, EM)
    var ariaLabel = title.textContent.trim().replace(/\s+/g, " ");
    title.setAttribute("aria-label", ariaLabel);

    var wrapWords = function (text) {
      return text.split(/(\s+)/).map(function (w) {
        if (/^\s+$/.test(w)) return w;
        return '<span class="split-word" aria-hidden="true">' + escHTML(w) + "</span>";
      }).join("");
    };

    var html = Array.from(title.childNodes).map(function (node) {
      if (node.nodeType === 3) return wrapWords(node.textContent);
      if (node.nodeName === "BR") return "<br>";
      if (node.nodeType === 1) {
        var tag = node.tagName.toLowerCase();
        return "<" + tag + ">" + wrapWords(node.textContent) + "</" + tag + ">";
      }
      return "";
    }).join("");
    title.innerHTML = html;

    // Animate words in staggered
    $$(".split-word", title).forEach(function (word, i) {
      setTimeout(function () {
        word.classList.add("is-visible");
      }, 800 + i * 60);
    });
  }

  // ─── Cursor ───────────────────────────────────────────────────
  function initCursor() {
    if (!fineHover) return;
    var root = $("[data-cursor-root]");
    if (!root) return;
    document.documentElement.classList.add("has-cursor");

    var ring = $(".cursor-ring", root);
    var dot  = $(".cursor-dot", root);
    var tx = 0, ty = 0, rx = 0, ry = 0;
    var firstMove = false;

    window.addEventListener("mousemove", function (e) {
      tx = e.clientX; ty = e.clientY;
      if (dot) dot.style.transform = "translate3d(" + tx + "px," + ty + "px,0)";
      if (!firstMove) {
        firstMove = true;
        rx = tx; ry = ty;
        if (ring) ring.style.transform = "translate3d(" + rx + "px," + ry + "px,0)";
        root.classList.add("is-ready");
      }
    });

    // Lag ring
    if (ring) {
      (function lerpRing() {
        rx += (tx - rx) * 0.14;
        ry += (ty - ry) * 0.14;
        ring.style.transform = "translate3d(" + rx + "px," + ry + "px,0)";
        requestAnimationFrame(lerpRing);
      })();
    }

    // Interactive state on links/buttons
    var HOVERABLES = "a, button, [data-tilt], .feat-card, .plan-card, .testi-card, .faq-q, .commands-grid code";
    document.addEventListener("mouseover", function (e) {
      if (e.target.closest(HOVERABLES)) root.classList.add("is-interactive");
    });
    document.addEventListener("mouseout", function (e) {
      if (!e.target.closest(HOVERABLES)) root.classList.remove("is-interactive");
    });
  }

  // ─── Card tilt ────────────────────────────────────────────────
  function initTilt() {
    if (!fineHover) return;
    $$("[data-tilt]").forEach(function (card) {
      card.addEventListener("mousemove", function (e) {
        var rect = card.getBoundingClientRect();
        var cx   = (e.clientX - rect.left) / rect.width  - 0.5;
        var cy   = (e.clientY - rect.top)  / rect.height - 0.5;
        card.style.transform = "perspective(900px) rotateY(" + (cx * 8) + "deg) rotateX(" + (-cy * 8) + "deg) translateY(-4px)";
      });
      card.addEventListener("mouseleave", function () {
        card.style.transform = "";
      });
    });
  }

  // ─── Count-up animations ──────────────────────────────────────
  function initCountUp() {
    $$("[data-count]").forEach(function (el) {
      var target = parseInt(el.dataset.count, 10);
      var suffix = el.nextElementSibling && el.nextElementSibling.classList.contains("stat-suffix")
        ? el.nextElementSibling.textContent : "";
      var start  = null;
      var duration = 1600;
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          observer.unobserve(el);
          function step(ts) {
            if (!start) start = ts;
            var progress = Math.min((ts - start) / duration, 1);
            var ease = 1 - Math.pow(1 - progress, 3);
            var val = Math.round(ease * target);
            el.textContent = val >= 1000 ? (val / 1000).toFixed(0) + "K" : val;
            if (progress < 1) requestAnimationFrame(step);
            else el.textContent = target >= 1000 ? (target / 1000).toFixed(0) + "K" : target;
          }
          requestAnimationFrame(step);
        });
      }, { threshold: 0.1 });
      observer.observe(el);
    });
  }

  // ─── Marquee duplicate for seamless loop ──────────────────────
  function initMarquee() {
    var track = $("[data-marquee]");
    if (!track) return;
    // already duplicated in HTML — just ensure animation is running
    track.style.animationPlayState = "running";
    track.addEventListener("mouseenter", function () {
      track.style.animationPlayState = "paused";
    });
    track.addEventListener("mouseleave", function () {
      track.style.animationPlayState = "running";
    });
  }

  // ─── FAQ keyboard accessibility ───────────────────────────────
  function initFaq() {
    $$(".faq-item").forEach(function (item) {
      var summary = $("summary", item);
      if (!summary) return;
      summary.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          item.toggleAttribute("open");
        }
      });
    });
  }

  // ─── GSAP / ScrollTrigger enhancements ────────────────────────
  function initGsap() {
    if (!window.gsap || !window.ScrollTrigger) return;

    gsap.registerPlugin(ScrollTrigger);

    // Hero mesh parallax
    $$(".mesh-blob").forEach(function (blob, i) {
      gsap.to(blob, {
        yPercent: -30 - i * 10,
        ease: "none",
        scrollTrigger: {
          trigger: ".hero",
          start: "top top",
          end: "bottom top",
          scrub: 1.2 + i * 0.3,
        },
      });
    });

    // Pipeline steps stagger
    gsap.from(".pipeline-step", {
      opacity: 0,
      x: -30,
      duration: 0.7,
      stagger: 0.12,
      ease: "power3.out",
      scrollTrigger: {
        trigger: ".pipeline-steps",
        start: "top 95%",
        toggleActions: "play none none none",
      },
    });

    // Pricing cards stagger
    gsap.from(".plan-card", {
      opacity: 0,
      y: 40,
      duration: 0.7,
      stagger: 0.15,
      ease: "power3.out",
      scrollTrigger: {
        trigger: ".pricing-grid",
        start: "top 95%",
        toggleActions: "play none none none",
      },
    });
  }

  // ─── Boot ─────────────────────────────────────────────────────
  function boot() {
    safe(initSplash,      "initSplash");
    safe(initNav,         "initNav");
    safe(initSmoothScroll,"initSmoothScroll");
    safe(initReveals,     "initReveals");
    safe(initHeroTitle,   "initHeroTitle");
    safe(initCursor,      "initCursor");
    safe(initTilt,        "initTilt");
    safe(initCountUp,     "initCountUp");
    safe(initMarquee,     "initMarquee");
    safe(initFaq,         "initFaq");
    safe(initGsap,        "initGsap");

    document.documentElement.classList.add("is-ready");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

})();
