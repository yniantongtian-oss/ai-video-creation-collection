#!/usr/bin/env python3
"""Validate bundled ComfyUI workflows and their model manifest."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "workflows"
MANIFEST_PATH = WORKFLOW_DIR / "models.json"
REQUIRED = {
    "wan22_t2v_4step.json",
    "wan22_i2v_4step.json",
    "wan22_long_video_3shot.json",
}
MODEL_SUFFIXES = (".safetensors", ".ckpt", ".pt", ".pth", ".bin")


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing file: {path.relative_to(ROOT)}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path.relative_to(ROOT)}: invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc


def model_names(node: dict) -> set[str]:
    names: set[str] = set()
    for value in node.get("widgets_values", []):
        if isinstance(value, str) and value.lower().endswith(MODEL_SUFFIXES):
            names.add(value)
    return names


def validate_workflow(path: Path) -> tuple[list[str], set[str], int, int]:
    errors: list[str] = []
    models: set[str] = set()
    data = load_json(path)
    if not isinstance(data, dict):
        return [f"{path.name}: root must be an object"], models, 0, 0

    for field in ("last_node_id", "last_link_id", "nodes", "links", "version"):
        if field not in data:
            errors.append(f"{path.name}: missing top-level field {field}")

    nodes_raw = data.get("nodes")
    links_raw = data.get("links")
    if not isinstance(nodes_raw, list) or not nodes_raw:
        return errors + [f"{path.name}: nodes must be a non-empty array"], models, 0, 0
    if not isinstance(links_raw, list):
        return errors + [f"{path.name}: links must be an array"], models, len(nodes_raw), 0

    nodes: dict[int, dict] = {}
    for index, node in enumerate(nodes_raw):
        prefix = f"{path.name}: nodes[{index}]"
        if not isinstance(node, dict):
            errors.append(f"{prefix} must be an object")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, int):
            errors.append(f"{prefix}.id must be an integer")
            continue
        if node_id in nodes:
            errors.append(f"{path.name}: duplicate node id {node_id}")
            continue
        if not isinstance(node.get("type"), str) or not node.get("type"):
            errors.append(f"{prefix}.type must be a non-empty string")
        if not isinstance(node.get("inputs", []), list):
            errors.append(f"{prefix}.inputs must be an array")
        if not isinstance(node.get("outputs", []), list):
            errors.append(f"{prefix}.outputs must be an array")
        nodes[node_id] = node
        models.update(model_names(node))

    link_ids: set[int] = set()
    for index, link in enumerate(links_raw):
        prefix = f"{path.name}: links[{index}]"
        if not isinstance(link, list) or len(link) < 6:
            errors.append(f"{prefix} must contain at least 6 values")
            continue
        link_id, origin_id, origin_slot, target_id, target_slot, link_type = link[:6]
        if not all(isinstance(value, int) for value in link[:5]):
            errors.append(f"{prefix}: ids and slots must be integers")
            continue
        if not isinstance(link_type, str) or not link_type:
            errors.append(f"{prefix}: type must be a non-empty string")
        if link_id in link_ids:
            errors.append(f"{path.name}: duplicate link id {link_id}")
        link_ids.add(link_id)

        origin = nodes.get(origin_id)
        target = nodes.get(target_id)
        if origin is None:
            errors.append(f"{prefix}: unknown origin node {origin_id}")
            continue
        if target is None:
            errors.append(f"{prefix}: unknown target node {target_id}")
            continue

        outputs = origin.get("outputs", [])
        inputs = target.get("inputs", [])
        if not 0 <= origin_slot < len(outputs):
            errors.append(f"{prefix}: origin slot {origin_slot} is out of range")
            continue
        if not 0 <= target_slot < len(inputs):
            errors.append(f"{prefix}: target slot {target_slot} is out of range")
            continue

        output_links = outputs[origin_slot].get("links")
        if link_id not in (output_links or []):
            errors.append(f"{prefix}: origin output does not reference link {link_id}")
        if inputs[target_slot].get("link") != link_id:
            errors.append(f"{prefix}: target input does not reference link {link_id}")

    if nodes and data.get("last_node_id") != max(nodes):
        errors.append(f"{path.name}: last_node_id does not match largest node id")
    expected_last_link = max(link_ids) if link_ids else 0
    if data.get("last_link_id") != expected_last_link:
        errors.append(f"{path.name}: last_link_id does not match largest link id")
    if data.get("version") != 0.4:
        errors.append(f"{path.name}: workflow version must be 0.4")

    node_types = {node.get("type") for node in nodes.values()}
    for required_type in ("CreateVideo", "SaveVideo"):
        if required_type not in node_types:
            errors.append(f"{path.name}: missing output node {required_type}")

    if path.name == "wan22_i2v_4step.json" and "WanImageToVideo" not in node_types:
        errors.append(f"{path.name}: missing WanImageToVideo")
    if path.name == "wan22_long_video_3shot.json":
        if sum(node.get("type") == "WanImageToVideo" for node in nodes.values()) != 3:
            errors.append(f"{path.name}: expected exactly 3 WanImageToVideo nodes")
        for required_type in ("ImageFromBatch", "ImageBatch"):
            if required_type not in node_types:
                errors.append(f"{path.name}: missing {required_type}")

    return errors, models, len(nodes), len(links_raw)


def validate_manifest(references: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    data = load_json(MANIFEST_PATH)
    if not isinstance(data, dict) or not isinstance(data.get("models"), list):
        return ["workflows/models.json: models must be an array"]

    by_workflow = {name: set() for name in references}
    seen_ids: set[str] = set()
    seen_destinations: set[tuple[str, str]] = set()

    for index, entry in enumerate(data["models"]):
        prefix = f"workflows/models.json: models[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        model_id = entry.get("id")
        filename = entry.get("filename")
        directory = entry.get("directory")
        url = entry.get("url")
        workflows = entry.get("workflows")

        if not isinstance(model_id, str) or not model_id:
            errors.append(f"{prefix}.id must be a non-empty string")
        elif model_id in seen_ids:
            errors.append(f"{prefix}.id duplicates {model_id!r}")
        else:
            seen_ids.add(model_id)

        if directory not in {"diffusion_models", "loras", "text_encoders", "vae"}:
            errors.append(f"{prefix}.directory is unsupported")
        if not isinstance(filename, str) or not filename:
            errors.append(f"{prefix}.filename must be a non-empty string")
        destination = (str(directory), str(filename))
        if destination in seen_destinations:
            errors.append(f"{prefix} duplicates {destination[0]}/{destination[1]}")
        seen_destinations.add(destination)

        if not isinstance(url, str):
            errors.append(f"{prefix}.url must be a string")
        else:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.netloc:
                errors.append(f"{prefix}.url must be HTTPS")

        if not isinstance(workflows, list) or not workflows:
            errors.append(f"{prefix}.workflows must be a non-empty array")
            continue
        for workflow in workflows:
            if workflow not in references:
                errors.append(f"{prefix} references unknown workflow {workflow!r}")
            elif isinstance(filename, str):
                by_workflow[workflow].add(filename)

    for workflow, filenames in references.items():
        missing = filenames - by_workflow.get(workflow, set())
        if missing:
            errors.append(
                f"{workflow}: models missing from manifest: {', '.join(sorted(missing))}"
            )
    return errors


def main() -> int:
    errors: list[str] = []
    references: dict[str, set[str]] = {}
    total_nodes = 0
    total_links = 0

    actual = {path.name for path in WORKFLOW_DIR.glob("*.json")} - {"models.json"}
    missing = REQUIRED - actual
    if missing:
        errors.append(f"missing required workflows: {', '.join(sorted(missing))}")

    for filename in sorted(REQUIRED & actual):
        workflow_errors, models, node_count, link_count = validate_workflow(
            WORKFLOW_DIR / filename
        )
        errors.extend(workflow_errors)
        references[filename] = models
        total_nodes += node_count
        total_links += link_count

    if references:
        errors.extend(validate_manifest(references))

    if errors:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        print(f"Workflow validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print(
        f"Workflows OK: {len(references)} files, "
        f"{total_nodes} nodes, {total_links} links."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
