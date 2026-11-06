"""Run: python -m unittest discover -s tests   (needs Pillow; ffmpeg + node for the full set)."""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "decode-text-overlay" / "scripts" / "decode_overlay.py"
spec = importlib.util.spec_from_file_location("decode_overlay", SCRIPT)
d = importlib.util.module_from_spec(spec)
sys.modules["decode_overlay"] = d
spec.loader.exec_module(d)

SCENARIOS = [
    dict(texts=["MIDNIGHT SESSIONS", "OUT NOW"], decode=0.9, hold=1.3, exit=0.0, order="random", seed=7, loop=True,
         times=[0, 0.05, 0.2, 0.45, 0.7, 1.0, 2.3, 2.5, 3.1, 4.4]),
    dict(texts=["STUDIO ONE\nLIVE SET", "A"], decode=1.1, hold=1.0, exit=0.6, order="ltr", seed=3, loop=True,
         times=[0.1, 0.5, 1.0, 2.2, 2.4, 2.7, 3.0, 4.0, 5.5]),
    dict(texts=["THE QUICK BROWN FOX JUMPS"], decode=1.4, hold=1.8, exit=0.8, order="center", seed=99, loop=False,
         times=[0.0, 0.3, 0.9, 1.5, 3.3, 3.8, 4.0, 5.0]),
]


def opts(sc):
    return dict(decode=sc["decode"], hold=sc["hold"], exit=sc["exit"], order=sc["order"], tick=1 / 24,
                seed=sc["seed"], charset=d.CHARSET)


class Core(unittest.TestCase):
    def test_wrap_balanced(self):
        self.assertEqual(d.wrap_balanced("MIDNIGHT SESSIONS", 12), "MIDNIGHT\nSESSIONS")
        self.assertEqual(d.wrap_balanced("OUT NOW", 12), "OUT NOW")
        self.assertEqual(d.wrap_balanced("A\nB LONG LONG LONG", 12), "A\nB LONG LONG LONG")
        self.assertEqual(d.wrap_balanced("NOSPACESATALLHERE", 12), "NOSPACESATALLHERE")

    def test_deterministic(self):
        o = opts(SCENARIOS[0])
        self.assertEqual(d.frame_text("", "HELLO", 0.3, o), d.frame_text("", "HELLO", 0.3, o))

    def test_grows_from_center_then_resolves(self):
        o = opts(SCENARIOS[0])
        early = d.frame_text("", "MIDNIGHT", 0.12, o)
        shown = [i for i, c in enumerate(early) if c != " "]
        self.assertTrue(shown, "something is visible")
        self.assertGreater(shown[0], 0)       # the left edge is still empty
        self.assertLess(shown[-1], 7)         # so is the right edge
        self.assertEqual(d.frame_text("", "MIDNIGHT", o["decode"], o), "MIDNIGHT")

    def test_exit_empties_layer(self):
        sc = SCENARIOS[1]
        segs, total = d.timeline([t for t in sc["texts"]], opts(sc))
        self.assertNotEqual(d.text_at(segs, total, 0.5, opts(sc), True), "")
        sc2 = SCENARIOS[2]
        segs, total = d.timeline(sc2["texts"], opts(sc2))
        self.assertEqual(d.text_at(segs, total, total + 1, opts(sc2), False), "")

    def test_orders_differ(self):
        o = opts(SCENARIOS[0])
        frames = {k: d.frame_text("", "ABCDEFGHIJKL", 0.5, dict(o, order=k)) for k in ("random", "ltr", "center")}
        self.assertEqual(len(set(frames.values())), 3)


@unittest.skipUnless(shutil.which("node"), "node not installed")
class Parity(unittest.TestCase):
    def test_js_equals_python(self):
        res = subprocess.run(["node", str(ROOT / "tests" / "parity.js"), json.dumps(SCENARIOS)],
                             capture_output=True, text=True, check=True)
        js = json.loads(res.stdout)
        for sc, js_frames in zip(SCENARIOS, js):
            o = opts(sc)
            texts = [d.wrap_balanced(t, 12) for t in sc["texts"]]
            segs, total = d.timeline(texts, o)
            py = [d.text_at(segs, total, t, o, sc["loop"]) for t in sc["times"]]
            self.assertEqual(js_frames, py)


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class Outputs(unittest.TestCase):
    def run_cli(self, *args):
        subprocess.run([sys.executable, str(SCRIPT), "--size-px", "270x480", "--fps", "8", *args], check=True,
                       capture_output=True)

    def test_formats(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            for name in ("a.mov", "a.webm", "a.gif", "a.svg"):
                self.run_cli("-t", "HELLO WORLD", "-o", str(t / name))
                self.assertGreater((t / name).stat().st_size, 500, name)
            self.run_cli("-t", "HELLO", "-o", str(t / "frames"))
            self.assertTrue(list((t / "frames").glob("frame_*.png")))
            ET.parse(t / "a.svg")  # well-formed

    def test_composite_and_auto_color(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            bg = t / "bg.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=white:s=270x480", "-frames:v", "1", str(bg)], check=True)
            r = subprocess.run([sys.executable, str(SCRIPT), "-t", "HI", "--bg", str(bg), "--color", "auto", "-o", str(t / "o.mp4")],
                               capture_output=True, text=True, check=True)
            self.assertIn("#111111", r.stderr)
            self.assertGreater((t / "o.mp4").stat().st_size, 500)

    def test_presets_run(self):
        with tempfile.TemporaryDirectory() as t:
            for name in d.PRESETS:
                self.run_cli("-t", "PRESET CHECK", "--preset", name, "-o", str(Path(t) / f"{name}.gif"))


if __name__ == "__main__":
    unittest.main()
