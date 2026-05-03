#!/usr/bin/env python3
"""
Run this from your project root:  python3 fix_scrolly.py
It patches static/index.html in-place.
"""
import re, os, sys

path = os.path.join("static", "index.html")
if not os.path.exists(path):
    sys.exit(f"ERROR: {path} not found. Run from project root.")

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

original = html
changes = []

# ── Fix 1: correct video filename ───────────────────────────────────────────
if 'src="clay-intro.mp4"' in html:
    html = html.replace('src="clay-intro.mp4"', 'src="scrolly.mp4"')
    changes.append("✓ Fixed video src: clay-intro.mp4 → scrolly.mp4")
elif 'src="scrolly.mp4"' in html:
    changes.append("  Video src already correct (scrolly.mp4)")
else:
    changes.append("⚠ Could not find video src attribute — check manually")

# ── Fix 2: robust scroll-scrub JS ───────────────────────────────────────────
OLD = """      video.pause();
      video.currentTime = 0;

      function lerp(a, b, t) { return a + (b - a) * t }
      function clamp(v, a, b) { return Math.max(a, Math.min(b, v)) }
      function fadeEl(el, p, i0, i1, o0, o1) {
        var op = 0, ty = 14;
        if (p >= i0 && p < i1) { var t = (p - i0) / (i1 - i0); op = t; ty = lerp(14, 0, t); }
        else if (p >= i1 && (!o0 || p < o0)) { op = 1; ty = 0; }
        else if (o0 && p >= o0 && p <= o1) { var t = (p - o0) / (o1 - o0); op = 1 - t; ty = lerp(0, -14, t); }
        else if (o1 && p > o1) { op = 0; ty = -14; }
        el.style.opacity = op;
        el.style.transform = 'translateY(' + ty + 'px)';
      }

      var raf = null, done = false;
      function update() {
        if (done) return;
        var st = window.scrollY;
        var top = section.offsetTop;
        var height = section.offsetHeight;
        var prog = clamp((st - top) / (height - window.innerHeight), 0, 1);

        // Scrub video — only update if meaningful change
        if (video.readyState >= 1) {
          var target = prog * video.duration;
          if (Math.abs(video.currentTime - target) > 0.04) {
            video.currentTime = target;
          }
        }

        // Text overlays
        fadeEl(ov1, prog, 0.05, 0.20, 0.38, 0.50);
        fadeEl(ov2, prog, 0.63, 0.75, 0.86, 0.94);

        // Hint
        hint.style.opacity = prog < 0.06 ? 1 : 0;

        // White bloom
        var bloomP = clamp((prog - 0.88) / 0.12, 0, 1);
        wol.style.opacity = bloomP;

        // Done — hide section
        if (prog >= 1 && !done) {
          done = true;
          section.style.pointerEvents = 'none';
        }
      }

      window.addEventListener('scroll', function () {
        if (raf) return;
        raf = requestAnimationFrame(function () { raf = null; update(); });
      }, { passive: true });

      // Trigger on load too
      video.addEventListener('loadedmetadata', update);
      update();"""

NEW = """      video.pause();
      video.currentTime = 0;

      function lerp(a, b, t) { return a + (b - a) * t; }
      function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
      function fadeEl(el, p, i0, i1, o0, o1) {
        var op = 0, ty = 14;
        if (p >= i0 && p < i1) { var t = (p - i0) / (i1 - i0); op = t; ty = lerp(14, 0, t); }
        else if (p >= i1 && (!o0 || p < o0)) { op = 1; ty = 0; }
        else if (o0 && p >= o0 && p <= o1) { var t2 = (p - o0) / (o1 - o0); op = 1 - t2; ty = lerp(0, -14, t2); }
        else if (o1 && p > o1) { op = 0; ty = -14; }
        el.style.opacity = op;
        el.style.transform = 'translateY(' + ty + 'px)';
      }

      var raf = null, done = false, videoReady = false;

      // Force buffer — some browsers skip buffering until explicit load()
      video.load();

      video.addEventListener('canplay', function () { videoReady = true; update(); });
      video.addEventListener('loadedmetadata', function () { videoReady = true; update(); });
      // Fallback: mark ready after 3 s regardless of network speed
      setTimeout(function () { videoReady = true; update(); }, 3000);

      function update() {
        if (done) return;
        var st = window.scrollY;
        var top = section.offsetTop;
        var height = section.offsetHeight;
        var scrollable = height - window.innerHeight;
        if (scrollable <= 0) return;
        var prog = clamp((st - top) / scrollable, 0, 1);

        // Scrub video — requires HAVE_METADATA + finite duration
        if (videoReady && video.readyState >= 1 && video.duration && isFinite(video.duration)) {
          var target = prog * video.duration;
          if (Math.abs(video.currentTime - target) > 0.033) {
            try { video.currentTime = target; } catch (e) {}
          }
        }

        fadeEl(ov1, prog, 0.05, 0.20, 0.38, 0.50);
        fadeEl(ov2, prog, 0.63, 0.75, 0.86, 0.94);

        hint.style.opacity = prog < 0.06 ? 1 : 0;

        var bloomP = clamp((prog - 0.88) / 0.12, 0, 1);
        wol.style.opacity = bloomP;

        if (prog >= 1 && !done) {
          done = true;
          section.style.pointerEvents = 'none';
        }
      }

      window.addEventListener('scroll', function () {
        if (raf) return;
        raf = requestAnimationFrame(function () { raf = null; update(); });
      }, { passive: true });

      update();"""

if OLD in html:
    html = html.replace(OLD, NEW)
    changes.append("✓ Upgraded scroll-scrub JS (added canplay listener + video.load())")
else:
    changes.append("  Scroll script not found verbatim — skipping (filename fix is the critical one)")

if html != original:
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print("\n".join(changes))
    print(f"\n✅ Saved: {path}")
else:
    print("\n".join(changes))
    print("\nNo changes written (file already up to date).")
