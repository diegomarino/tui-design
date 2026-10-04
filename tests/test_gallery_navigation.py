"""Run the gallery's navigation JavaScript in Node, without a browser or rendering."""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/tui-design/scripts"))
import gallery

DRIVER = r"""
const vm = require('vm');
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const elements = {}, listeners = {};
const context = {
  F: input.frames, ORD: input.order, DATA: {title: 'Test'},
  document: {
    getElementById(id) {
      return elements[id] ||= {value: '', blur() {}, addEventListener(k, fn) {this[k] = fn;}};
    },
    addEventListener(k, fn) {listeners[k] = fn;}
  },
  render() {}
};
vm.createContext(context);
vm.runInContext(input.script, context);
const observations = [];
for (const action of input.actions) {
  if (action.key) listeners.keydown({key: action.key, target: {tagName: 'BODY'}, preventDefault() {}});
  else {
    const el = elements['sel-' + action.dim];
    el.value = action.value; el.change({target: el});
  }
  observations.push({...context.cur});
}
console.log(JSON.stringify(observations));
"""


@unittest.skipUnless(shutil.which("node"), "Node is needed to run navigation JavaScript")
class GalleryNavigationTests(unittest.TestCase):
    def run_actions(self, actions):
        # Sparse matrix: alpha has an error state only at the smaller size;
        # gamma has no error state and no larger size.
        frames = [dict(d="tiny", v=v, s=s, z=z, t="mocha") for v, s, z in (
            ("alpha", "normal", "20x3"), ("alpha", "normal", "30x4"),
            ("alpha", "error", "20x3"), ("beta", "normal", "20x3"),
            ("beta", "normal", "30x4"), ("gamma", "normal", "20x3"),
        )]
        # Execute the actual navigation and event handlers; rendering is outside
        # this test's scope and remains covered by the optional browser suite.
        script = "var DIMS=" + gallery.PAGE.split("var DIMS=", 1)[1].split("function chip", 1)[0]
        script += "DIMS.forEach" + gallery.PAGE.split("DIMS.forEach", 1)[1].split("render();\n})();", 1)[0]
        payload = dict(script=script, frames=frames, actions=actions, order=dict(
            d=["tiny"], v=["alpha", "beta", "gamma"], s=["normal", "error"],
            z=["20x3", "30x4"], t=["mocha"]))
        r = subprocess.run(["node", "-e", DRIVER], input=json.dumps(payload), text=True, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_state_arrows_stay_in_variant_without_that_state(self):
        obs = self.run_actions([dict(dim="v", value="gamma"), dict(key="ArrowDown"), dict(key="ArrowUp")])
        self.assertEqual([(o["v"], o["s"]) for o in obs], [("gamma", "normal")] * 3)

    def test_state_selector_cannot_pull_in_another_variant(self):
        obs = self.run_actions([dict(dim="v", value="gamma"), dict(dim="s", value="error")])
        self.assertEqual((obs[-1]["v"], obs[-1]["s"]), ("gamma", "normal"))

    def test_size_restored_after_variant_fallback(self):
        obs = self.run_actions([dict(dim="z", value="30x4"), dict(key="ArrowRight"),
                                dict(key="ArrowRight"), dict(key="ArrowLeft"), dict(key="ArrowLeft")])
        self.assertEqual([o["z"] for o in obs], ["30x4", "30x4", "20x3", "30x4", "30x4"])

    def test_size_restored_after_state_fallback(self):
        obs = self.run_actions([dict(dim="z", value="30x4"), dict(key="ArrowDown"), dict(key="ArrowUp")])
        self.assertEqual([o["z"] for o in obs], ["30x4", "20x3", "30x4"])
        self.assertTrue(all(o["v"] == "alpha" for o in obs))

    def test_explicit_size_replaces_preference(self):
        obs = self.run_actions([dict(dim="z", value="30x4"), dict(dim="v", value="gamma"),
                                dict(dim="z", value="20x3"), dict(dim="v", value="alpha")])
        self.assertEqual(obs[-1]["z"], "20x3")

    def test_z_replaces_preference(self):
        obs = self.run_actions([dict(dim="z", value="30x4"), dict(key="z"),
                                dict(dim="v", value="gamma"), dict(dim="v", value="alpha")])
        self.assertEqual(obs[-1]["z"], "20x3")
