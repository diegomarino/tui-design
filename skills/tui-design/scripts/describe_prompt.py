#!/usr/bin/env python3
"""Assemble the exact describer prompt for one dispatch (references/prompts/describe-tui.md, audit-protocol.md 4.1).

Prompt = Preamble + (Pass 1 | Pass 2 block) [+ live-capture addendum] + OUTPUT CONTRACT. The blocks are read from
describe-tui.md; every {{placeholder}} is filled from the facts of the image the describer actually sees
(the pass-1 image or the region crop, in that image's pixels); the contract is generated from
references/schemas/tui-description.schema.json ($defs/describer_pass1 | describer_pass2 and every enum they reach)."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
PROMPT_MD = SKILL / "references" / "prompts" / "describe-tui.md"
SCHEMA = SKILL / "references" / "schemas" / "tui-description.schema.json"

EPILOG = """\
Examples:
  python3 describe_prompt.py --pass 1 --grid prep/grid.json -o prompt.pass1.txt
  python3 describe_prompt.py --pass 2 --grid prep/grid.json --crops prep/crops.json --pass1 pass1.json \\
      --region r3 -o prompt.pass2.r3.txt
  python3 describe_prompt.py --pass 1 --grid prep/grid.json --path capture --text 120x30.skeleton.json -o p.txt
  python3 describe_prompt.py --contract 2          # print only the generated OUTPUT CONTRACT for pass 2

grid.json `advice` (prep_screenshot.py):
  ok           dispatch as is (plain image only on pass 1)
  check-ruler  the pass-1 ruler image is added; open it yourself first and confirm the labels sit on the cells
  give-size    refused (exit 3): ask the user for the terminal size, re-run prep_screenshot.py --cols C --rows R
               (--force overrides)
Pass 2 without --crops (live capture, small screens) uses the pass-1 image and names the region's cells instead.
Paths in grid.json / crops.json are relative to the file that names them; the prompt lists absolute paths.
Exit: 0 ok, 2 usage/input error, 3 grid advice is give-size."""

# Keys the describer must not fill (scripts measure them) and per-path value overrides.
OMIT = {
    "color": {"token", "token_candidates", "raw"},
    "style": {"attrs_source", "link"},
    "region": {"aria_role", "volatile"},
}
ONLY = {("color", "source"): ["vision"], ("element", "source"): ["vision"], ("uncertainty", "source"): ["vision"]}
DROP_ENUM = {("uncertainty", "kind"): {"ink_mismatch", "disagreement"}}
NOTES = {
    ("region", "children"): "full nested region objects, never id strings",
    ("region", "occludes"): "overlays only: ids of the regions drawn underneath",
    ("region", "z"): "0 = base layout; 1+ = modal, popup_menu, toast, tooltip",
    ("element", "truncated"): "never true/false; leave the key out when nothing is cut",
    ("element", "confidence"): "a word, never a number",
    ("style", "attrs_confidence"): "a word, never a number",
    ("style", "bg"): "leave the key out when there is no background colour; never null",
    ("style", "fg"): "leave the key out instead of null",
    ("uncertainty", "ref"): "id of a region or element (r3, e301); no other key names the target",
    ("uncertainty", "note"): "required",
    ("color", "name"): "black red green yellow blue magenta cyan white gray orange purple pink default",
}
DEF_ORDER = ["region", "element", "bbox", "style", "color", "state", "key_hint", "anchor_line", "uncertainty"]


class UsageError(Exception):
    pass


# ----------------------------------------------------------------------------- prompt blocks
def prompt_blocks(md: str) -> dict[str, str]:
    """First ```text block after each of the four section headings."""
    out = {}
    for key, head in (("pre", r"## 2\. Preamble"), ("p1", r"## 3\. Pass 1"), ("p2", r"## 4\. Pass 2"),
                      ("pa", r"## 5\. Live-capture addendum")):
        m = re.search(head + r".*?```text\n(.*?)```", md, re.S)
        if not m:
            raise UsageError(f"{PROMPT_MD}: no ```text block under '{head}'")
        out[key] = m.group(1)
    return out


def fill(text: str, values: dict) -> str:
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


# ----------------------------------------------------------------------------- output contract
class Contract:
    def __init__(self, schema: dict):
        self.s = schema
        self.defs = schema["$defs"]
        self.queue: list[str] = []

    def ref_name(self, ref: str) -> str:
        if ref == "#/properties/uncertainties":
            return "uncertainties"
        return ref.rsplit("/", 1)[-1]

    def resolve(self, ref: str) -> dict:
        node = self.s
        for part in ref.lstrip("#/").split("/"):
            node = node[part]
        return node

    def named(self, name: str) -> str:
        if name not in self.queue:
            self.queue.append(name)
        return name.upper()

    def typ(self, node: dict, owner: str = "", prop: str = "", depth: int = 0) -> str:
        if "$ref" in node:
            name = self.ref_name(node["$ref"])
            if name == "uncertainties":
                return "[" + self.named("uncertainty") + ", …]"
            if name in ("confidence", "source", "hex", "id"):
                return self.typ(self.resolve(node["$ref"]), owner, prop, depth)
            return self.named(name)
        if "enum" in node:
            vals = [v for v in node["enum"] if v not in DROP_ENUM.get((owner, prop), set())]
            if (owner, prop) in ONLY:
                vals = ONLY[(owner, prop)]
            return " | ".join(json.dumps(v, ensure_ascii=False) for v in vals)
        if "anyOf" in node:
            return " | ".join(self.typ(n, owner, prop, depth) for n in node["anyOf"])
        t = node.get("type")
        if isinstance(t, list):
            parts = []
            for one in t:
                parts.append("true | false" if one == "boolean" else ("null" if one == "null" else one))
            return " | ".join(parts)
        if t == "array":
            inner = self.typ(node.get("items", {}), owner, prop, depth)
            extra = f" (at most {node['maxItems']})" if "maxItems" in node else ""
            return f"[{inner}, …]{extra}"
        if t == "object" and "properties" in node:
            return self.obj_inline(node, owner, depth)
        if t == "string":
            if "pattern" in node:
                return f"string matching {node['pattern']}"
            if "minLength" in node:
                return f"string (at least {node['minLength']} characters)"
            return "string"
        if t == "integer":
            return "integer" + (f" >= {node['minimum']}" if "minimum" in node else "")
        if t == "boolean":
            return "true | false"
        return t or "any"

    def obj_inline(self, node: dict, owner: str, depth: int) -> str:
        req = set(node.get("required", []))
        parts = []
        for k, v in node["properties"].items():
            parts.append(f"{k}{'*' if k in req else ''}: {self.typ(v, owner, k, depth + 1)}")
        return "{" + ", ".join(parts) + "}"

    def block(self, name: str, node: dict) -> str:
        owner = name
        req = node.get("required", [])
        props = {k: v for k, v in node.get("properties", {}).items() if k not in OMIT.get(owner, set())}
        head = f"{name.upper()}: object"
        if req:
            head += "; required: " + ", ".join(req)
        if node.get("additionalProperties") is False:
            head += "; no other keys"
        lines = [head]
        for k, v in props.items():
            note = NOTES.get((owner, k))
            lines.append(f"  {k}: {self.typ(v, owner, k)}" + (f"   ({note})" if note else ""))
        return "\n".join(lines)

    def render(self, part: str) -> str:
        top = self.defs[part]
        self.queue = []
        blocks = {"top": self.block(f"pass {part[-1]} output", top)}     # rendering queues the named shapes
        while True:
            pending = sorted((n for n in self.queue if n not in blocks), key=self.rank)
            if not pending:
                break
            n = pending[0]
            node = self.s["properties"]["uncertainties"]["items"] if n == "uncertainty" else self.defs[n]
            blocks[n] = self.block(n, node)
        head = ["OUTPUT CONTRACT (generated from the JSON schema; any other key or value fails validation)",
                "Keys marked * inside {…} are required. Leave out a key you have no value for, unless null is listed."]
        body = [blocks["top"]] + [blocks[n] for n in sorted((k for k in blocks if k != "top"), key=self.rank)]
        return "\n".join(head + body) + "\n"

    @staticmethod
    def rank(name: str) -> int:
        return DEF_ORDER.index(name) if name in DEF_ORDER else len(DEF_ORDER)


def contract_text(pass_no: int) -> str:
    schema = json.loads(SCHEMA.read_text())
    return Contract(schema).render(f"describer_pass{pass_no}")


# ----------------------------------------------------------------------------- facts from grid / crops
def num(v: float) -> str:
    return f"{round(float(v), 2):g}"


def load_json(path: str | Path, what: str):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise UsageError(f"cannot read {what} {path}: {e}")


def pass1_facts(grid: dict, gdir: Path, tile: int) -> dict:
    """-> {file, ruler, cell(w,h), origin(x,y), first(x,y), cols(c0,c1)} in pass-1 image pixels."""
    p1 = grid.get("pass1")
    if not isinstance(p1, dict):
        raise UsageError("grid.json has no `pass1` entry (run prep_screenshot.py first)")
    tiles = p1.get("tiles") or []
    if "cell_px" in p1 or (tiles and "cell_px" in tiles[0]):  # current format: facts of the pass-1 image itself
        if tiles and not 1 <= tile <= len(tiles):
            raise UsageError(f"--tile {tile}: grid.json has {len(tiles)} pass-1 tile(s)")
        cur = tiles[tile - 1] if tiles else p1
        cell = list(cur.get("cell_px", p1.get("cell_px")))
        sc = float(cur.get("scale", p1.get("scale", 1.0)))
        if sc != 1.0 and all(abs(a - b) < 1e-6 for a, b in zip(cell, grid["cell_px"])):
            cell = [v * sc for v in cell]                    # given in original pixels: convert to the image's
        cols = cur.get("cols", [0, grid["cols"]])
        name = cur.get("file", p1.get("file"))
        ruler = cur.get("ruler") or Path(name).stem.replace("pass1", "pass1-ruler", 1) + ".png"
        return {"file": gdir / name, "ruler": gdir / ruler, "cell": cell,
                "origin": cur.get("origin_px", p1.get("origin_px", [0, 0])),
                "first": cur.get("origin_cell", [cols[0], 0]), "cols": cols}
    # earlier format: tiles + cell_px_scaled
    if not tiles:
        raise UsageError("grid.json `pass1` has neither `file` nor `tiles`")
    if not 1 <= tile <= len(tiles):
        raise UsageError(f"--tile {tile}: grid.json has {len(tiles)} pass-1 tile(s)")
    t, s = tiles[tile - 1], float(p1.get("scale", 1.0))
    ox, oy = grid["origin_px"]
    # the pass-1 image starts at floor(origin) of the first cell: only the fractional part remains (x scale)
    c0 = t.get("cols", [0, grid["cols"]])[0]
    fx = ox + c0 * grid["cell_px"][0]
    return {"file": gdir / t["file"], "ruler": gdir / t.get("ruler", Path(t["file"]).stem + "-ruler.png"),
            "cell": p1["cell_px_scaled"], "origin": [(fx - math.floor(fx)) * s, (oy - math.floor(oy)) * s],
            "first": [c0, 0], "cols": t.get("cols", [0, grid["cols"]])}


def crop_entries(doc) -> list[dict]:
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        for k in ("crops", "regions"):
            if isinstance(doc.get(k), list):
                return doc[k]
    raise UsageError("crops file: expected a list of {id, file, bbox, scale, cell_px, origin_px} or {\"crops\": [...]}")


def crop_facts(entry: dict, base: Path, grid: dict) -> dict:
    """-> {file, ruler, cell, origin, first, extent{x,y,w,h}} in crop-image pixels."""
    rid = str(entry["id"])
    # the crop's extent in cells: crops.json `bbox` (region + 1-cell margin), or grid.json regions[] `crop_cells`
    ext = entry.get("crop_cells") or entry["bbox"]
    if "cell_px" in entry and "origin_px" in entry:          # current format: already in crop pixels
        cell, origin = entry["cell_px"], entry["origin_px"]
        first = entry.get("origin_cell", [ext["x"], ext["y"]])
    elif "cell_px_scaled" in entry:                          # earlier format (grid.json regions[])
        s = float(entry.get("scale", 1.0))
        ox, oy = grid["origin_px"]
        fx, fy = ox + ext["x"] * grid["cell_px"][0], oy + ext["y"] * grid["cell_px"][1]
        cell, origin, first = entry["cell_px_scaled"], [(fx - math.floor(fx)) * s, (fy - math.floor(fy)) * s], \
            [ext["x"], ext["y"]]
    else:
        raise UsageError(f"crop {rid}: needs cell_px + origin_px (or cell_px_scaled)")
    ruler = entry.get("ruler") or f"region-{rid}-ruler.png"
    return {"file": base / entry["file"], "ruler": base / ruler, "cell": cell, "origin": origin,
            "first": first, "extent": ext}


def geometry(f: dict) -> str:
    fx, fy = f["first"]
    return (f"cell ({fx},{fy}) has its top-left corner at pixel ({num(f['origin'][0])},{num(f['origin'][1])}); "
            f"each cell is {num(f['cell'][0])} x {num(f['cell'][1])} px")


def find_region(regs: list, rid: str):
    for r in regs or []:
        if r.get("id") == rid:
            return r
        hit = find_region(r.get("children"), rid)
        if hit:
            return hit
    return None


def numbered_text(path: str) -> str:
    doc = load_json(path, "--text")
    st = doc.get("screen_text") if isinstance(doc, dict) else None
    if st is None:
        raise UsageError(f"--text {path}: no `screen_text` (use ansi_grid.py --describe output)")
    lines = st if isinstance(st, list) else st.split("\n")
    return "\n".join(f"{i:02d}|{line}" for i, line in enumerate(lines))


# ----------------------------------------------------------------------------- build
def build(a) -> str:
    blocks = prompt_blocks(PROMPT_MD.read_text())
    gpath = Path(a.grid).resolve()
    grid = load_json(gpath, "--grid")
    for k in ("cols", "rows"):
        if k not in grid:
            raise UsageError(f"--grid {a.grid}: no `{k}` (expected prep_screenshot.py grid.json)")
    advice = grid.get("advice", "ok")
    if advice == "give-size" and not a.force:
        print("grid.json advice=give-size: the grid is not reliable. Ask the user for the terminal size and re-run "
              "prep_screenshot.py --cols C --rows R (or --force).", file=sys.stderr)
        raise SystemExit(3)
    conf = grid.get("grid_confidence", grid.get("confidence", "unknown"))
    gdir = gpath.parent
    imgs: list[str] = []
    values = {"cols": grid["cols"], "rows": grid["rows"], "grid_confidence": f"{conf} (advice: {advice})"}

    p1f = pass1_facts(grid, gdir, a.tile)
    if a.pass_no == 1:
        f = p1f
        c0, c1 = f["cols"]
        label = "plain full screen" if (c0, c1) == (0, grid["cols"]) else f"plain, columns {c0}..{c1 - 1}"
        imgs.append(f"  {f['file']}  ({label})")
        if a.ruler or advice == "check-ruler":
            if not f["ruler"].exists():
                raise UsageError(f"ruler image not found: {f['ruler']}")
            imgs.append(f"  {f['ruler']}  (same image with margin ruler)")
            if advice == "check-ruler" and not a.ruler:
                print("advice=check-ruler: ruler image added. Open it yourself first and confirm the labels sit on "
                      "the cells (audit-protocol.md 4, step 1).", file=sys.stderr)
        body = blocks["pre"] + "\n" + blocks["p1"]
    else:
        if not a.region or not a.pass1:
            raise UsageError("--pass 2 needs --region ID and --pass1 PASS1.json")
        p1doc = load_json(a.pass1, "--pass1")
        reg = find_region(p1doc.get("regions") if isinstance(p1doc, dict) else p1doc, a.region)
        if reg is None:
            raise UsageError(f"region {a.region} not found in {a.pass1}")
        if reg.get("children"):
            raise UsageError(f"region {a.region} has children: pass 2 runs on leaf regions only "
                             f"(its border and title come from pass 1)")
        record = {k: v for k, v in reg.items() if k != "children"}
        entry = None
        if a.crops:
            cpath = Path(a.crops).resolve()
            entry = next((e for e in crop_entries(load_json(cpath, "--crops")) if str(e.get("id")) == a.region), None)
            if entry is None:
                raise UsageError(f"region {a.region} not in {a.crops} (re-run prep_screenshot.py --regions pass1.json)")
            f = crop_facts(entry, cpath.parent, grid)
        elif isinstance(grid.get("regions"), list) and any(str(e.get("id")) == a.region for e in grid["regions"]):
            entry = next(e for e in grid["regions"] if str(e.get("id")) == a.region)
            f = crop_facts(entry, gdir, grid)
        if entry is not None:
            e = f["extent"]
            span = f"cells x={e['x']}..{e['x'] + e['w'] - 1}, y={e['y']}..{e['y'] + e['h'] - 1}"
            if f["ruler"].exists():
                imgs.append(f"  {f['ruler']}  (crop of {span} with absolute margin ruler)")
            imgs.append(f"  {f['file']}  (same crop, no ruler)")
            crop_note = f"The images show {span}: region {a.region} plus a 1-cell margin where the screen allows."
        else:
            f = p1f
            b = reg["bbox"]
            imgs.append(f"  {f['file']}  (plain full screen)")
            if a.ruler and f["ruler"].exists():
                imgs.append(f"  {f['ruler']}  (same image with margin ruler)")
            crop_note = (f"The image is the full screen; describe only region {a.region}: cells "
                         f"x={b['x']}..{b['x'] + b['w'] - 1}, y={b['y']}..{b['y'] + b['h'] - 1}.")
        n = int(re.sub(r"\D", "", a.region) or 0)
        values.update({"region_id": a.region, "n": n, "crop_note": crop_note,
                       "region_record": json.dumps(record, ensure_ascii=False)})
        body = blocks["pre"] + "\n" + blocks["p2"]
    for fpath in [line.strip().split("  (")[0] for line in imgs]:
        if not Path(fpath).exists():
            raise UsageError(f"image not found: {fpath}")
    values.update({"image_list": "\n".join(imgs), "geometry": geometry(f)})
    out = fill(body, values)
    if a.path == "capture":
        if not a.text:
            raise UsageError("--path capture needs --text SKELETON.json (ansi_grid.py --describe output)")
        out += "\n" + fill(blocks["pa"], {"screen_text_numbered": numbered_text(a.text)})
    out += "\n" + contract_text(a.pass_no)
    left = sorted(set(re.findall(r"\{\{[a-z_]+\}\}", out)))
    if left:
        raise UsageError(f"unfilled placeholders: {', '.join(left)}")
    return out


LEGACY_PATHS = {"A": "capture", "B": "screenshot"}   # hidden aliases for old command lines


def norm_path_arg(v: str) -> str:
    v = LEGACY_PATHS.get(v, v)
    if v not in ("capture", "screenshot"):
        raise argparse.ArgumentTypeError(f"invalid choice: {v!r} (choose from 'capture', 'screenshot')")
    return v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=EPILOG,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pass", dest="pass_no", type=int, choices=(1, 2), help="describer pass")
    ap.add_argument("--grid", help="prep_screenshot.py grid.json")
    ap.add_argument("--crops", help="prep_screenshot.py crops.json (pass 2)")
    ap.add_argument("--region", help="leaf region id for pass 2 (e.g. r3)")
    ap.add_argument("--pass1", help="reconciled pass-1 JSON (pass 2: the region record)")
    ap.add_argument("--path", type=norm_path_arg, default="screenshot", metavar="{capture,screenshot}",
                    help="capture appends the given-text addendum (live capture, needs --text); screenshot is the default")
    ap.add_argument("--text", help="live capture: ansi_grid.py --describe JSON with screen_text")
    ap.add_argument("--ruler", action="store_true", help="also list the ruler image (pass 1 / pass 2 without crops)")
    ap.add_argument("--tile", type=int, default=1, help="pass-1 tile number when prep tiled the screen (default 1)")
    ap.add_argument("--force", action="store_true", help="build the prompt even when advice is give-size")
    ap.add_argument("--contract", type=int, choices=(1, 2), help="print only the generated output contract")
    ap.add_argument("-o", "--out", help="write the prompt here (default stdout)")
    a = ap.parse_args(argv)
    try:
        if a.contract:
            text = contract_text(a.contract)
        else:
            if not a.pass_no or not a.grid:
                raise UsageError("--pass and --grid are required (or --contract N)")
            text = build(a)
    except UsageError as e:
        print(f"describe_prompt.py: {e}", file=sys.stderr)
        return 2
    except (KeyError, TypeError, ValueError) as e:
        print(f"describe_prompt.py: unexpected input shape: {e!r}", file=sys.stderr)
        return 2
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"prompt ({len(text)} chars, pass {a.pass_no or a.contract}, path {a.path}) -> {a.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
