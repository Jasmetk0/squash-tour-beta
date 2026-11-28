import json
import os
import re
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

source = Path(".github/requirements/fast-ci-linux.lock.txt")
output = Path(os.environ["RUNNER_TEMP"]) / "arm-wheel.lock"
lines = []
for line in source.read_text().splitlines():
    if not line.strip() or line.lstrip().startswith(("#", "--hash=")):
        continue
    match = re.fullmatch(r"([A-Za-z0-9_.-]+)(\[[A-Za-z0-9_,.-]+\])?==([^\s]+)(?:\s+\\)?", line.strip())
    if not match:
        raise ValueError(f"Unexpected requirement: {line}")
    name, extras, version = match.groups()
    with urlopen(f"https://pypi.org/pypi/{quote(name)}/{quote(version)}/json", timeout=30) as response:
        data = json.load(response)
    wheels = [item for item in data["urls"] if item["packagetype"] == "bdist_wheel" and not item.get("yanked")]
    hashes = sorted({item["digests"]["sha256"] for item in wheels})
    if not hashes or any(not re.fullmatch(r"[a-f0-9]{64}", value) for value in hashes):
        raise ValueError(f"No valid non-yanked wheel hashes for {name}=={version}")
    lines.append(f"{name}{extras or ''}=={version} " + " ".join("--hash=sha256:" + value for value in hashes))
if not lines:
    raise ValueError("Empty lock")
output.write_text("\n".join(lines) + "\n")
