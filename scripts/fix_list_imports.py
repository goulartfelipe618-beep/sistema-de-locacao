"""Corrige import faltante nas listagens."""
from pathlib import Path

IMPORT = '{% from "macros/form_instructions.html" import list_create_actions %}'
root = Path(__file__).resolve().parents[1] / "app"
fixed = 0
for path in root.rglob("*_list.html"):
    text = path.read_text(encoding="utf-8")
    if "list_create_actions(" not in text:
        continue
    if "macros/form_instructions.html" in text:
        continue
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip().startswith("{% extends "):
            lines.insert(i + 1, IMPORT + "\n")
            break
    path.write_text("".join(lines), encoding="utf-8", newline="\n")
    fixed += 1
    print(path)
print("fixed", fixed)
