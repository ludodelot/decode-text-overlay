/*!
 * <decode-text> — monospace "decoding" text overlay for photos, videos and web.
 * Zero dependencies. Same animation as scripts/decode_overlay.py.
 *
 * <div style="position:relative">
 *   <img src="photo.jpg">
 *   <decode-text texts="MIDNIGHT SESSIONS|OUT NOW" loop></decode-text>
 * </div>
 *
 * Attributes: texts ("|" separates phrases, "\n" = new line), decode (s), hold (s),
 * tick (s), seed, loop, paused, size (css length), tracking (em), color, shadow.
 * Events: "decode-end" after the last phrase resolves (when not looping).
 * Methods: restart(). Respects prefers-reduced-motion (shows final text).
 */
(function () {
  const CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789*?!/#+<>=-_$%&¡¿";

  function hash32(a, b, c) {
    let h = (Math.imul(a, 374761393) + Math.imul(b, 668265263) + Math.imul(c, 2246822519)) >>> 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177) >>> 0;
    return (h ^ (h >>> 16)) >>> 0;
  }
  const rnd = (a, b, c) => hash32(a, b, c) / 4294967296;
  function padCenter(s, n) {
    const total = n - s.length, left = Math.floor(total / 2);
    return " ".repeat(left) + s + " ".repeat(total - left);
  }

  function wrapBalanced(s, maxlen) {
    if (maxlen <= 0 || s.includes("\n") || s.length <= maxlen) return s;
    let best = -1, bd = Infinity;
    for (let i = 0; i < s.length; i++) {
      if (s[i] !== " ") continue;
      const d = Math.abs(i - s.length / 2);
      if (d < bd) { bd = d; best = i; }
    }
    return best < 0 ? s : s.slice(0, best) + "\n" + s.slice(best + 1);
  }

  // Grows from the center outward as random glyphs, then resolves in random order.
  function frameText(prev, target, t, o) {
    const grow = o.decode * 0.40;
    return target.split("\n").map((line, li) => {
      const n = line.length, c = (n - 1) / 2;
      let out = "";
      for (let i = 0; i < n; i++) {
        const ch = line[i];
        if (ch === " ") { out += " "; continue; }
        const j = rnd(o.seed, li * 97 + i, 1);
        const d = c > 0 ? Math.abs(i - c) / c : 0;
        const g = grow * d * (0.85 + 0.30 * j);
        let r = o.decode * (0.35 + 0.65 * rnd(o.seed, li * 97 + i, 2));
        r = Math.min(o.decode, Math.max(r, g + o.decode * 0.12));
        if (t >= r) out += ch;
        else if (t < g) out += " ";
        else {
          const tick = Math.floor(t / o.tick);
          out += o.charset[Math.floor(rnd(o.seed + tick, li * 97 + i, 3) * o.charset.length)];
        }
      }
      return out;
    }).join("\n");
  }

  class DecodeText extends HTMLElement {
    static get observedAttributes() { return ["texts", "decode", "hold", "tick", "seed", "loop", "paused"]; }
    constructor() {
      super();
      const r = this.attachShadow({ mode: "open" });
      r.innerHTML = `<style>
        :host{position:absolute;inset:0;display:grid;place-items:center;pointer-events:none;
          font-family:var(--dt-font,"Space Mono","SF Mono",ui-monospace,Menlo,monospace);
          font-size:var(--dt-size,clamp(12px,3.6cqw,40px));
          letter-spacing:var(--dt-tracking,.18em);text-transform:uppercase;
          color:var(--dt-color,#fff);text-align:center;line-height:1.15;
          text-shadow:var(--dt-shadow,0 0 .6em rgba(0,0,0,.35));container-type:inline-size}
        pre{margin:0;font:inherit;white-space:pre;opacity:.95;padding-left:.18em}
      </style><pre part="text" aria-hidden="true"></pre><span part="sr" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)"></span>`;
      this._pre = r.querySelector("pre");
      this._sr = r.querySelector("[part=sr]");
      this._tick = this._tick.bind(this);
    }
    get _o() {
      const n = (k, d) => (this.hasAttribute(k) ? parseFloat(this.getAttribute(k)) : d);
      return { decode: n("decode", 0.9), hold: n("hold", 1.3), tick: n("tick", 1 / 24), seed: n("seed", 7), charset: CHARSET };
    }
    get _texts() {
      return (this.getAttribute("texts") || this.textContent || "").split("|").map((s) => wrapBalanced(s.replace(/\\n/g, "\n").trim(), this.hasAttribute("wrap") ? parseInt(this.getAttribute("wrap"), 10) : 12)).filter(Boolean);
    }
    connectedCallback() { this.restart(); }
    disconnectedCallback() { cancelAnimationFrame(this._raf); }
    attributeChangedCallback() { if (this.isConnected) this.restart(); }
    restart() {
      cancelAnimationFrame(this._raf);
      this._t0 = performance.now();
      this._ended = false;
      const texts = this._texts;
      this._sr.textContent = texts.join(". ").replace(/\n/g, " ");
      if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
        this._pre.textContent = texts[texts.length - 1] || "";
        return;
      }
      this._raf = requestAnimationFrame(this._tick);
    }
    _tick(now) {
      const o = this._o, texts = this._texts;
      if (!texts.length) return;
      const cycle = o.decode + o.hold, total = cycle * texts.length;
      let t = (now - this._t0) / 1000;
      if (this.hasAttribute("paused")) { this._t0 = now - t * 1000; this._raf = requestAnimationFrame(this._tick); return; }
      if (this.hasAttribute("loop")) t %= total;
      else if (t >= total - o.hold) {
        this._pre.textContent = texts[texts.length - 1];
        if (!this._ended) { this._ended = true; this.dispatchEvent(new CustomEvent("decode-end")); }
        return;
      }
      const k = Math.min(texts.length - 1, Math.floor(t / cycle));
      this._pre.textContent = frameText(k ? texts[k - 1] : "", texts[k], t - k * cycle, o);
      this._raf = requestAnimationFrame(this._tick);
    }
  }
  if (!customElements.get("decode-text")) customElements.define("decode-text", DecodeText);
  window.DecodeText = { frameText, wrapBalanced, CHARSET };
})();
