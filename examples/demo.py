#!/usr/bin/env python3
"""Execute a real offline fixture and export a labelled, self-contained replay."""
import argparse
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "deep_native.py"
BUGGY = "def attempts(retries):\n    return max(1, retries)\n"
FIXED = '''def attempts(retries):
    if type(retries) is not int:
        raise TypeError("retries must be an integer")
    if retries < 0:
        raise ValueError("retries must be nonnegative")
    return retries + 1
'''
TESTS = '''import unittest
from budget import attempts

class BudgetTests(unittest.TestCase):
    def test_initial_attempt_plus_retries(self):
        self.assertEqual(attempts(2), 3)
        self.assertEqual(attempts(0), 1)
    def test_negative_rejected(self):
        with self.assertRaises(ValueError): attempts(-1)
    def test_bool_rejected(self):
        with self.assertRaises(TypeError): attempts(True)
'''


def render(report):
    steps = []
    for i, step in enumerate(report["steps"], 1):
        color = "ok" if step["expected"] else "bad"
        text = "$ " + " ".join(step["argv"]) + "\n" + step["output"]
        steps.append(f'<section id="step-{i}"><header><span>{i:02}</span><h2>{html.escape(step["title"])}</h2>'
                     f'<b class="{color}">exit {step["exit_code"]}</b></header><pre>{html.escape(text)}</pre></section>')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Deep Native | Executed offline demo</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#101216;color:#e4e7ed;font:16px/1.6 system-ui,sans-serif}
main{max-width:1080px;margin:auto;padding:64px 24px}h1{font-size:clamp(40px,7vw,76px);line-height:1.1;letter-spacing:-.055em;margin:12px 0 24px}
.lead{max-width:800px;color:#adb5c1;font-size:19px}.tag{font-size:12px;letter-spacing:.12em;color:#9cddbb;text-transform:uppercase}
.banner{border-left:3px solid #d9b870;background:#242117;padding:16px 20px;margin:28px 0 40px}.flow{padding:22px;background:#1b2028;border-radius:12px;margin-bottom:44px}
section{border:1px solid #313640;border-radius:12px;margin:20px 0;overflow:hidden}header{display:flex;align-items:center;gap:16px;padding:18px 22px;background:#191d24}
header span{color:#939da9}h2{font-size:17px;margin:0;flex:1}b{font-size:12px;white-space:nowrap}.ok{color:#9cddbb}.bad{color:#ffabab}
pre{padding:20px;margin:0;overflow:auto;max-height:430px;font:12px/1.7 ui-monospace,monospace;background:#11151b;white-space:pre-wrap;overflow-wrap:anywhere}
a{color:#b8d5ff}footer{color:#929ca9;margin-top:40px}code{font-family:ui-monospace,monospace}</style>
<main><div class="tag">Deep Native / v0.1.0 / evidence replay</div><h1>No evidence.<br>No done.</h1>
<p class="lead">A failing check cannot become a success message. A passing check cannot certify code that changed afterwards.</p>
<div class="banner"><strong>OFFLINE SCRIPTED EXPERIMENT, NOT A MODEL BENCHMARK.</strong><br>
Every command below was executed. The source repair is explicitly scripted. No DeepSeek or Claude model was called.</div>
<div class="flow">Reproduce failure &rarr; reject premature completion &rarr; scripted repair &rarr; restore checkpoint &rarr; verify &rarr; reject stale evidence &rarr; re-verify &rarr; finish</div>
''' + "\n".join(steps) + '''<footer>Regenerate: <code>python3 examples/demo.py --output artifacts/demo</code><br>
The adjacent <a href="demo.json">demo.json</a> contains the machine-readable transcript. Paths are normalized to &lt;workspace&gt; and &lt;deep-native&gt;.
This replay proves the fixture and local gate behavior, not model parity or general correctness.</footer></main></html>'''


def run_demo(output: Path):
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Output directory is nonempty; choose a fresh destination.")
    output.mkdir(parents=True, exist_ok=True)
    steps = []
    with tempfile.TemporaryDirectory(prefix="deep-native-demo-") as tmp:
        root = Path(tmp)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / ".gitignore").write_text("__pycache__/\n.deep-native/\n")
        (root / "budget.py").write_text(BUGGY)
        (root / "test_budget.py").write_text(TESTS)
        def command(title, argv, expected=0, input_text=None):
            result = subprocess.run(argv, cwd=root, input=input_text, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
                                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            clean = lambda s: s.replace(str(root), "<workspace>").replace(str(ROOT), "<deep-native>")
            step = {"title": title, "argv": [clean(str(a)) for a in argv], "exit_code": result.returncode,
                    "expected": result.returncode == expected, "output": clean(result.stdout)}
            steps.append(step)
            print(f"{len(steps):02}. {title}: exit={result.returncode}, expected={expected}")
            if not step["expected"]: raise RuntimeError(f"Demo failed at {title}: {result.stdout}")
            return result
        def cli(title, *args, expected=0, input_text=None):
            return command(title, [sys.executable, str(CLI), "--project", str(root), *args], expected, input_text)
        cli("Configure the actual fixture tests", "configure", "--name", "regression", "--", sys.executable, "-m", "unittest", "discover", "-v")
        cli("Begin an explicit coding task", "begin", "--session", "demo-session", "--goal", "One initial attempt plus nonnegative integer retries; reject bool and negatives")
        command("Reproduce three real failing tests", [sys.executable, "-m", "unittest", "discover", "-v"], expected=1)
        cli("Reject completion without evidence", "finish", "--summary", "Claimed fix", "--risk", "None stated", expected=2)
        cli("Record a real failed verification", "verify", expected=1)
        (root / "budget.py").write_text(FIXED)
        cli("Checkpoint after SCRIPTED repair, not an LLM edit", "checkpoint", "--note", "Script repaired retry semantics and input validation", "--next", "Run the same regression tests")
        cli("Replay a compact SessionStart hook payload", "hook", input_text=json.dumps({"hook_event_name": "SessionStart", "source": "compact", "session_id": "demo-session"}))
        command("Run the same three tests after repair", [sys.executable, "-m", "unittest", "discover", "-v"])
        cli("Bind passing checks to the worktree", "verify")
        (root / "budget.py").write_text(FIXED + "\n# A later edit invalidates the old receipt.\n")
        cli("Reject stale evidence after another edit", "finish", "--summary", "Retry fixed", "--risk", "Offline only", expected=2)
        cli("Re-verify the latest bytes", "verify")
        cli("Complete with current evidence and explicit limits", "finish", "--summary", "Retry budget fixture repaired and checked", "--risk", "Scripted offline fixture; no model capability result")
    report = {"schema": 1, "kind": "OFFLINE_SCRIPTED", "model_calls": 0,
              "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "python": sys.version.split()[0], "all_expected_outcomes": all(s["expected"] for s in steps), "steps": steps}
    (output / "demo.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (output / "demo.html").write_text(render(report))
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "artifacts/demo")
    args = p.parse_args()
    run_demo(args.output.resolve())
