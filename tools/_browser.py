"""Find a Playwright that is already installed, with a browser that launches. Never installs anything.

Used by tools/make_screenshots.py (page screenshots) and tests/test_gallery_browser.py (skipped without one).

Lookup order:
  1. Python: `import playwright` works in this interpreter.
  2. Node: the `playwright` package in $PLAYWRIGHT_NODE_PATH (a node_modules directory), in the global npm root,
     or in the npx cache (~/.npm/_npx/*/node_modules), newest first.
A candidate counts only if `chromium.launch()` succeeds with the browsers it already has.

    python3 tools/_browser.py        # prints what was found, exit 1 if nothing
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Playwright:
    kind: str                 # "python" | "node"
    node_path: str = ""       # node_modules directory holding `playwright` (node only)

    def describe(self) -> str:
        return "Python playwright" if self.kind == "python" else f"Node playwright ({self.node_path})"


def _python_ok() -> bool:
    if importlib.util.find_spec("playwright") is None:
        return False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


def _node_candidates() -> list[Path]:
    out: list[Path] = []
    env = os.environ.get("PLAYWRIGHT_NODE_PATH")
    if env:
        out.append(Path(env))
    npm = shutil.which("npm")
    if npm:
        try:
            root = subprocess.run([npm, "root", "-g"], capture_output=True, text=True, timeout=20).stdout.strip()
            if root:
                out.append(Path(root))
        except (OSError, subprocess.SubprocessError):
            pass
    cache = Path.home() / ".npm" / "_npx"
    if cache.is_dir():
        mods = [d for d in cache.glob("*/node_modules") if (d / "playwright" / "package.json").is_file()]
        out += sorted(mods, key=lambda d: (d / "playwright" / "package.json").stat().st_mtime, reverse=True)
    return [d for d in out if (d / "playwright" / "package.json").is_file()]


def run_node(nm: str, script: str, args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a CommonJS script that does `require("playwright")`, resolved from the node_modules dir `nm`."""
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "drive.cjs"
        f.write_text(script, encoding="utf-8")
        env = dict(os.environ, NODE_PATH=nm)
        return subprocess.run(["node", str(f), *args], capture_output=True, text=True, env=env, timeout=timeout)


_PROBE = 'const {chromium}=require("playwright");chromium.launch().then(b=>b.close()).then(()=>process.exit(0),()=>process.exit(1));'


@lru_cache(maxsize=1)
def find() -> Playwright | None:
    if _python_ok():
        return Playwright("python")
    if shutil.which("node"):
        for nm in _node_candidates():
            try:
                if run_node(str(nm), _PROBE, [], timeout=60).returncode == 0:
                    return Playwright("node", str(nm))
            except subprocess.TimeoutExpired:
                continue
    return None


# Screenshot driver shared by both backends: a JSON list of jobs.
#   {"url", "out", "width", "height", "dark": bool, "keys": ["s", ...], "full_page": bool, "selector": optional}
NODE_SHOTS = r"""
const {chromium}=require("playwright");const fs=require("fs");
(async()=>{const jobs=JSON.parse(fs.readFileSync(process.argv[2],"utf8"));const b=await chromium.launch();
 for(const j of jobs){const c=await b.newContext({viewport:{width:j.width,height:j.height},deviceScaleFactor:j.scale||1,
   colorScheme:j.dark?"dark":"light",reducedMotion:"reduce"});const p=await c.newPage();await p.goto(j.url);
   await p.waitForLoadState("load");for(const k of (j.keys||[])){await p.keyboard.press(k);}
   for(const [sel,val] of (j.select||[])){await p.selectOption(sel,val);}
   await p.waitForTimeout(j.wait||300);
   if(j.selector){await p.locator(j.selector).first().screenshot({path:j.out});}
   else{await p.screenshot({path:j.out,fullPage:!!j.full_page});}
   await c.close();}
 await b.close();})().catch(e=>{console.error(e);process.exit(1);});
"""


def screenshots(pw: Playwright, jobs: list[dict]) -> None:
    """Take every page screenshot in `jobs` (see NODE_SHOTS for the fields)."""
    if pw.kind == "node":
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(jobs, f)
        try:
            r = run_node(pw.node_path, NODE_SHOTS, [f.name], timeout=300)
        finally:
            os.unlink(f.name)
        if r.returncode:
            raise RuntimeError(f"page screenshots failed:\n{r.stderr}")
        return
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        for j in jobs:
            c = b.new_context(viewport={"width": j["width"], "height": j["height"]}, device_scale_factor=j.get("scale", 1),
                              color_scheme="dark" if j.get("dark") else "light", reduced_motion="reduce")
            pg = c.new_page()
            pg.goto(j["url"])
            pg.wait_for_load_state("load")
            for k in j.get("keys", []):
                pg.keyboard.press(k)
            for sel, val in j.get("select", []):
                pg.select_option(sel, val)
            pg.wait_for_timeout(j.get("wait", 300))
            if j.get("selector"):
                pg.locator(j["selector"]).first.screenshot(path=j["out"])
            else:
                pg.screenshot(path=j["out"], full_page=bool(j.get("full_page")))
            c.close()
        b.close()


if __name__ == "__main__":
    found = find()
    print(found.describe() if found else "no Playwright with a launchable browser found")
    sys.exit(0 if found else 1)
