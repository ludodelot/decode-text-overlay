// Prints frames for the shared scenarios as JSON lines. tests/test_decode.py compares them with Python.
global.HTMLElement = class {}; global.customElements = { get() { return 1; }, define() {} }; global.window = {};
require("../web/decode-text.js");
const D = window.DecodeText;
const scenarios = JSON.parse(process.argv[2]);
const out = scenarios.map((sc) => {
  const o = { decode: sc.decode, hold: sc.hold, exit: sc.exit, delay: sc.delay || 0, order: sc.order, tick: 1 / 24, seed: sc.seed, charset: sc.charset || null };
  const texts = sc.texts.map((t) => D.wrapBalanced(t, 12));
  return sc.times.map((t) => D.textAt(texts, t, o, sc.loop).text);
});
console.log(JSON.stringify(out));
