"""Audit storyboard files for maxLength truncation, newlines, and text completeness.

Contract: design_planner.md §1, §6 item 7; design_testing_and_validation.md §2.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from animated_infographics.contracts.models import Bible
from animated_infographics.contracts.templates import REGISTRY
from animated_infographics.planner.validate import internal_id_errors, word_cap_errors

# Terminal punctuation symbols that count as closing/completed text
TERMINAL_PUNCTUATION: tuple[str, ...] = (".", "!", "?", ")", '"', "'", "”", "’")

# Characters that indicate a cut-off when appearing at the end of a string
CUT_OFF_ENDINGS: tuple[str, ...] = ("-", "(", "[", ",", ":", "/")


def resolve_schema(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    """Resolve $ref within schema."""
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        ref_path = schema["$ref"].lstrip("#/").split("/")
        target = root
        for part in ref_path:
            target = target[part]
        return resolve_schema(target, root)
    return schema


def get_field_max_lengths(
    schema: dict[str, Any], root: dict[str, Any], path: str = ""
) -> dict[str, int]:
    """Recursively extract max_length constraints from JSON schema."""
    schema = resolve_schema(schema, root)
    res: dict[str, int] = {}
    if not isinstance(schema, dict):
        return res
    if "maxLength" in schema:
        res[path] = schema["maxLength"]
    if "anyOf" in schema:
        for opt in schema["anyOf"]:
            res.update(get_field_max_lengths(opt, root, path))
    if "oneOf" in schema:
        for opt in schema["oneOf"]:
            res.update(get_field_max_lengths(opt, root, path))
    if "allOf" in schema:
        for opt in schema["allOf"]:
            res.update(get_field_max_lengths(opt, root, path))
    if "properties" in schema:
        for k, v in schema["properties"].items():
            subpath = f"{path}.{k}" if path else k
            res.update(get_field_max_lengths(v, root, subpath))
    if "items" in schema:
        subpath = f"{path}[]"
        res.update(get_field_max_lengths(schema["items"], root, subpath))
    return res


TEMPLATE_FIELD_LIMITS: dict[str, dict[str, int]] = {
    name: get_field_max_lengths(
        spec.props_model.model_json_schema(), spec.props_model.model_json_schema()
    )
    for name, spec in REGISTRY.items()
}


def is_text_cut_off(s: str) -> bool:
    """Check if string violates text completeness per design_planner.md §6 item 7."""
    # 1. Contains no letter or digit
    if not any(c.isalnum() for c in s):
        return True
    # 2. Ends with -, (, [, ,, :, or /
    if s.rstrip().endswith(CUT_OFF_ENDINGS):
        return True
    # 3. (, [, or " characters are unbalanced
    if s.count("(") != s.count(")") or s.count("[") != s.count("]") or (s.count('"') % 2 != 0):
        return True
    # 4. Last word is a truncation fragment (single lowercase letter other than a)
    tokens = s.strip().split()
    if tokens:
        last = tokens[-1].rstrip(".,!?:;\"'…")
        if len(last) == 1 and last.islower() and last != "a":
            return True
    return False


def extract_scene_strings(
    template: str, props: dict[str, Any]
) -> list[tuple[str, str, int | None]]:
    """Extract all string values and their max_length constraints from a scene props dictionary.

    Returns list of (instance_path, string_value, max_length_or_none).
    """
    limits = TEMPLATE_FIELD_LIMITS.get(template, {})
    results: list[tuple[str, str, int | None]] = []

    def walk(obj: Any, schema_path: str, instance_path: str) -> None:
        if isinstance(obj, str):
            ml = limits.get(schema_path)
            results.append((instance_path, obj, ml))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                sp = f"{schema_path}.{k}" if schema_path else k
                ip = f"{instance_path}.{k}" if instance_path else k
                walk(v, sp, ip)
        elif isinstance(obj, list):
            sp = f"{schema_path}[]"
            for i, it in enumerate(obj):
                ip = f"{instance_path}[{i}]"
                walk(it, sp, ip)

    walk(props, "", "props")
    return results


def is_free_text_field(template: str, path: str) -> bool:
    """Determine whether path is a free-text field subjected to completeness checks.

    Per §6 item 7: checked on title, subtitle, text, descriptor,
    label, heading, points[], kicker, contact_name, messages[].text, lines[].text,
    events[].label, markers[].label, edges[].label and non-empty suffix.
    Not on ids, enums, prefix, date_label or era_label.
    """
    if "date_label" in path or "era_label" in path or path.endswith("_id") or "_id" in path:
        return False
    if path.endswith(".prefix") or path.endswith(".icon") or path.endswith(".emotion"):
        return False
    if path.endswith(".tone") or path.endswith(".region") or path.endswith(".style"):
        return False
    return True


def audit_storyboards(storyboard_paths: list[Path], dedup: bool = True) -> dict[str, Any]:
    """Audit a set of storyboard.json files and return statistics."""
    scenes_seen: dict[tuple[str, str], tuple[dict[str, Any], Bible | None]] = {}
    total_scenes_count = 0

    for sb_path in storyboard_paths:
        try:
            data = json.loads(sb_path.read_text(encoding="utf-8"))
            bible_file = sb_path.parent / "bible.json"
            bible: Bible | None = None
            if bible_file.exists():
                try:
                    bible = Bible.model_validate_json(bible_file.read_text(encoding="utf-8"))
                except Exception:
                    bible = None

            for sc in data.get("scenes", []):
                total_scenes_count += 1
                template = sc.get("template", "")
                props = sc.get("props", {})
                props_key = json.dumps(props, sort_keys=True)
                key = (template, props_key)
                if dedup:
                    if key not in scenes_seen:
                        scenes_seen[key] = (sc, bible)
                else:
                    scenes_seen[(f"{sb_path}:{total_scenes_count}", props_key)] = (sc, bible)
        except Exception as e:
            print(f"Warning: could not read {sb_path}: {e}", file=sys.stderr)

    unique_scenes = list(scenes_seen.values())
    unique_scenes_count = len(unique_scenes)

    total_strings = 0
    at_max_length_count = 0
    at_max_length_no_punct: list[dict[str, Any]] = []
    contains_newline: list[dict[str, Any]] = []
    completeness_failures: list[dict[str, Any]] = []
    id_leaks: list[dict[str, Any]] = []
    word_cap_violations: list[dict[str, Any]] = []

    for sc, bible in unique_scenes:
        tmpl = sc.get("template", "")
        props = sc.get("props", {})
        extracted = extract_scene_strings(tmpl, props)
        total_strings += len(extracted)

        cap_errs = word_cap_errors(tmpl, props)
        if cap_errs:
            word_cap_violations.append(
                {
                    "template": tmpl,
                    "errors": cap_errs,
                    "props": props,
                }
            )

        for path, val, ml in extracted:
            if ml is not None and len(val) == ml:
                at_max_length_count += 1
                stripped = val.strip()
                if not stripped.endswith(TERMINAL_PUNCTUATION):
                    at_max_length_no_punct.append(
                        {
                            "template": tmpl,
                            "path": path,
                            "length": len(val),
                            "max_length": ml,
                            "value": val,
                        }
                    )

            if "\n" in val:
                contains_newline.append(
                    {
                        "template": tmpl,
                        "path": path,
                        "value": val,
                    }
                )

            if is_free_text_field(tmpl, path):
                # non-empty suffix check
                if path.endswith(".suffix") and not val:
                    continue
                if is_text_cut_off(val):
                    completeness_failures.append(
                        {
                            "template": tmpl,
                            "path": path,
                            "value": val,
                        }
                    )

                id_errs: list[str] = []
                if bible is not None:
                    id_errs = internal_id_errors(path, val, bible)
                else:
                    tokens = re.findall(r"[A-Za-z0-9]+", val)
                    id_errs = [
                        f'{path}: contains internal id "{t.casefold()}"'
                        for t in tokens
                        if re.match(r"^(?:c[1-8]|p[1-4]|v[1-3])$", t.casefold())
                    ]
                if id_errs:
                    id_leaks.append(
                        {
                            "template": tmpl,
                            "path": path,
                            "value": val,
                            "errors": id_errs,
                        }
                    )

    return {
        "storyboards_count": len(storyboard_paths),
        "total_scenes_count": total_scenes_count,
        "unique_scenes_count": unique_scenes_count,
        "total_strings": total_strings,
        "at_max_length_count": at_max_length_count,
        "at_max_length_no_punct_count": len(at_max_length_no_punct),
        "contains_newline_count": len(contains_newline),
        "completeness_failures_count": len(completeness_failures),
        "id_leaks_count": len(id_leaks),
        "word_cap_violations_count": len(word_cap_violations),
        "at_max_length_no_punct": at_max_length_no_punct,
        "contains_newline": contains_newline,
        "completeness_failures": completeness_failures,
        "id_leaks": id_leaks,
        "word_cap_violations": word_cap_violations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit storyboard text fields")
    parser.add_argument(
        "paths",
        nargs="*",
        help="Storyboard files or directories to audit (defaults to artifacts/e2e)",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Audit baseline Wave A runs (up to 20260925_203215)",
    )
    parser.add_argument(
        "--no-dedup",
        action="store_true",
        help="Do not deduplicate identical scenes across storyboards",
    )
    args = parser.parse_args()

    files: list[Path] = []
    if args.baseline:
        base_dir = Path("artifacts/e2e")
        for d in sorted(base_dir.iterdir()):
            if d.is_dir() and d.name <= "20260925_203215":
                files.extend(sorted(d.glob("jobs/**/storyboard.json")))
    elif args.paths:
        for p_str in args.paths:
            p = Path(p_str)
            if p.is_file():
                files.append(p)
            elif p.is_dir():
                files.extend(sorted(p.glob("**/storyboard.json")))
    else:
        files = sorted(Path("artifacts/e2e").glob("*/jobs/**/storyboard.json"))

    result = audit_storyboards(files, dedup=not args.no_dedup)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
