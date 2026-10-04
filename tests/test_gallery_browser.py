"""Browser test for the gallery page's JavaScript (gallery.py): keys, side by side, and real file downloads.

Runs only when a Playwright with a launchable browser is already installed (Python or Node; see tools/_browser.py);
otherwise every test is skipped. Nothing is installed. Run: python3 -m unittest tests.test_gallery_browser -v
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "tui-design" / "scripts"
sys.path.insert(0, str(ROOT / "tools"))
import _browser  # noqa: E402

MOCK = "#! tui-mockup 1\n#! size: 20x3\n#! title: Tiny {}\n#! state: {}\n{{accent.primary bold}}Hello{{/}} world\n{{status.error}}err{{/}}\n"
THEMES = "catppuccin-mocha,dracula-classic"

# The scenario, once per backend. It reports observations as JSON; the assertions live in Python.
NODE_SCENARIO = r"""
const {chromium}=require("playwright");const fs=require("fs");
(async()=>{const [url,dir]=process.argv.slice(2);const b=await chromium.launch();
 const c=await b.newContext({acceptDownloads:true});const p=await c.newPage();await p.goto(url);
 const val=s=>p.$eval(s,e=>e.value);const o={url_before:p.url()};
 o.theme0=await val("#sel-t");await p.keyboard.press("t");o.theme1=await val("#sel-t");
 o.cap_theme=await p.textContent("#cap-a .m");
 o.state0=await val("#sel-s");await p.keyboard.press("ArrowDown");o.state1=await val("#sel-s");
 o.variant0=await val("#sel-v");await p.keyboard.press("ArrowRight");o.variant1=await val("#sel-v");
 o.sizes=[];
 await p.selectOption("#sel-v","alpha");await p.selectOption("#sel-s","normal");await p.selectOption("#sel-z","30x4");
 for(const key of ["ArrowRight","ArrowRight","ArrowLeft","ArrowLeft"]){await p.keyboard.press(key);o.sizes.push(await val("#sel-z"));}
 await p.selectOption("#sel-s","error");o.state_size=await val("#sel-z");
 await p.selectOption("#sel-s","normal");o.restored_state_size=await val("#sel-z");
 await p.selectOption("#sel-v","gamma");await p.keyboard.press("ArrowDown");await p.keyboard.press("ArrowUp");
 o.state_variant=await val("#sel-v");await p.selectOption("#sel-v","alpha");await p.selectOption("#sel-z","20x3");
 o.explicit_size=await val("#sel-z");
 await p.selectOption("#sel-v","beta");
 await p.keyboard.press("s");o.split_hidden=await p.$eval("#pane-b",e=>e.hidden);
 o.split_pressed=await p.getAttribute("#btn-split","aria-pressed");
 o.downloads=[];
 for(const kind of ["txt","png"]){
   const [d]=await Promise.all([p.waitForEvent("download",{timeout:10000}),p.click(`#exports-a button[data-x="${kind}"]`)]);
   const path=dir+"/"+d.suggestedFilename();await d.saveAs(path);
   o.downloads.push({name:d.suggestedFilename(),path});}
 o.url_after=p.url();o.pages=c.pages().length;
 console.log(JSON.stringify(o));await b.close();})().catch(e=>{console.error(e);process.exit(1);});
"""


def python_scenario(url: str, out: str) -> dict:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        c = b.new_context(accept_downloads=True)
        p = c.new_page()
        p.goto(url)
        val = lambda s: p.eval_on_selector(s, "e => e.value")  # noqa: E731
        o = {"url_before": p.url, "theme0": val("#sel-t")}
        p.keyboard.press("t")
        o["theme1"] = val("#sel-t")
        o["cap_theme"] = p.text_content("#cap-a .m")
        o["state0"] = val("#sel-s")
        p.keyboard.press("ArrowDown")
        o["state1"] = val("#sel-s")
        o["variant0"] = val("#sel-v")
        p.keyboard.press("ArrowRight")
        o["variant1"] = val("#sel-v")
        o["sizes"] = []
        p.select_option("#sel-v", "alpha")
        p.select_option("#sel-s", "normal")
        p.select_option("#sel-z", "30x4")
        for key in ("ArrowRight", "ArrowRight", "ArrowLeft", "ArrowLeft"):
            p.keyboard.press(key)
            o["sizes"].append(val("#sel-z"))
        p.select_option("#sel-s", "error")
        o["state_size"] = val("#sel-z")
        p.select_option("#sel-s", "normal")
        o["restored_state_size"] = val("#sel-z")
        p.select_option("#sel-v", "gamma")
        p.keyboard.press("ArrowDown")
        p.keyboard.press("ArrowUp")
        o["state_variant"] = val("#sel-v")
        p.select_option("#sel-v", "alpha")
        p.select_option("#sel-z", "20x3")
        o["explicit_size"] = val("#sel-z")
        p.select_option("#sel-v", "beta")
        p.keyboard.press("s")
        o["split_hidden"] = p.eval_on_selector("#pane-b", "e => e.hidden")
        o["split_pressed"] = p.get_attribute("#btn-split", "aria-pressed")
        o["downloads"] = []
        for kind in ("txt", "png"):
            with p.expect_download(timeout=10000) as info:
                p.click(f'#exports-a button[data-x="{kind}"]')
            d = info.value
            path = str(Path(out) / d.suggested_filename)
            d.save_as(path)
            o["downloads"].append({"name": d.suggested_filename, "path": path})
        o["url_after"] = p.url
        o["pages"] = len(c.pages)
        b.close()
        return o


class GalleryBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = _browser.find()
        if cls.pw is None:
            raise unittest.SkipTest("no Playwright with a launchable browser installed (tools/_browser.py)")
        cls.tmp = Path(tempfile.mkdtemp())
        d = cls.tmp / "tiny"
        d.mkdir()
        (d / "alpha--normal--20x3.mock").write_text(MOCK.format("A", "normal"))
        (d / "alpha--error--20x3.mock").write_text(MOCK.format("A", "error"))
        (d / "beta--normal--20x3.mock").write_text(MOCK.format("B", "normal"))
        (d / "beta--error--20x3.mock").write_text(MOCK.format("B", "error"))
        for variant in ("alpha", "beta"):
            (d / f"{variant}--normal--30x4.mock").write_text(MOCK.format(variant, "normal").replace("20x3", "30x4"))
        (d / "gamma--normal--20x3.mock").write_text(MOCK.format("G", "normal"))
        page = cls.tmp / "gallery.html"
        r = subprocess.run([sys.executable, str(SCRIPTS / "gallery.py"), str(d), "--themes", THEMES, "-o", str(page)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        out = cls.tmp / "downloads"
        out.mkdir()
        if cls.pw.kind == "node":
            r = _browser.run_node(cls.pw.node_path, NODE_SCENARIO, [page.as_uri(), str(out)])
            assert r.returncode == 0, r.stderr
            cls.obs = json.loads(r.stdout.strip().splitlines()[-1])
        else:
            cls.obs = python_scenario(page.as_uri(), str(out))

    def test_t_switches_theme(self):
        self.assertEqual(self.obs["theme0"], "catppuccin-mocha")
        self.assertEqual(self.obs["theme1"], "dracula-classic")
        self.assertIn("dracula-classic", self.obs["cap_theme"])

    def test_arrows_switch_state_and_variant(self):
        self.assertNotEqual(self.obs["state0"], self.obs["state1"])
        self.assertEqual({self.obs["state0"], self.obs["state1"]}, {"normal", "error"})
        self.assertEqual((self.obs["variant0"], self.obs["variant1"]), ("alpha", "beta"))

    def test_state_arrows_do_not_switch_variant(self):
        self.assertEqual(self.obs["state_variant"], "gamma")

    def test_size_survives_variants_without_the_selected_size(self):
        self.assertEqual(self.obs["sizes"], ["30x4", "20x3", "30x4", "30x4"])

    def test_size_survives_states_without_the_selected_size(self):
        self.assertEqual(self.obs["state_size"], "20x3")
        self.assertEqual(self.obs["restored_state_size"], "30x4")

    def test_explicit_size_replaces_the_remembered_preference(self):
        self.assertEqual(self.obs["explicit_size"], "20x3")

    def test_s_toggles_side_by_side(self):
        self.assertFalse(self.obs["split_hidden"])
        self.assertEqual(self.obs["split_pressed"], "true")

    def test_exports_are_real_downloads(self):
        names = [d["name"] for d in self.obs["downloads"]]
        self.assertTrue(names[0].endswith(".txt") and names[1].endswith(".png"), names)
        self.assertTrue(all(n.startswith("tiny--beta--") and "dracula-classic" in n for n in names), names)
        txt = Path(self.obs["downloads"][0]["path"]).read_text(encoding="utf-8")
        self.assertIn("Hello world", txt)
        self.assertEqual(Path(self.obs["downloads"][1]["path"]).read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        # A download, not a navigation to the blob: URL, and no extra tab.
        self.assertEqual(self.obs["url_after"], self.obs["url_before"])
        self.assertTrue(self.obs["url_after"].startswith("file:"))
        self.assertEqual(self.obs["pages"], 1)


if __name__ == "__main__":
    unittest.main()
