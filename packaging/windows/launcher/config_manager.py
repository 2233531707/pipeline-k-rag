from __future__ import annotations

from pathlib import Path


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value
    return values


def initialize_env(project_dir: Path) -> tuple[Path, int]:
    template = project_dir / ".env.template"
    target = project_dir / ".env"
    if not template.exists():
        raise FileNotFoundError(f"缺少配置模板: {template}")

    if not target.exists():
        target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        return target, len(_parse_env(template))

    current = _parse_env(target)
    missing_lines: list[str] = []
    for raw_line in template.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key not in current:
            missing_lines.append(raw_line)

    if missing_lines:
        with target.open("a", encoding="utf-8", newline="\n") as file:
            file.write("\n# Added by Yuxi Desktop Launcher\n")
            file.write("\n".join(missing_lines) + "\n")
    return target, len(missing_lines)
