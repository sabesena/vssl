import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
import json

LOGS_DIR = Path("/mnt/1TB/vssl/logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
COMMANDS_LOG = LOGS_DIR / "commands.log"

DANGEROUS_PATTERNS = [
    r'\brm\s+(-[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*r[a-zA-Z]*)\b',
    r'\bdd\b',
    r'\bmkfs\b',
    r'\bshred\b',
    r'>\s*/dev/[sh]d',
    r'\bformat\b.*\b/dev/',
]


def _log_command(command: str, result: str):
    timestamp = datetime.now().isoformat()
    try:
        with open(COMMANDS_LOG, "a") as f:
            f.write(f"[{timestamp}] CMD: {command}\nRESULT: {result[:500]}\n---\n")
    except Exception:
        pass


def _is_dangerous(command: str) -> bool:
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False


def execute_bash(command: str, confirmed: bool = False) -> dict:
    if _is_dangerous(command) and not confirmed:
        return {
            "status": "confirmation_required",
            "output": f"⚠️ Dangerous command detected!\n\nCommand: `{command}`\n\nTo confirm, call execute_bash again with confirmed=true",
            "command": command,
        }
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            executable="/bin/bash",
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"
        if not output.strip():
            output = f"(exit code {result.returncode}, no output)"
        _log_command(command, output)
        return {"status": "success", "output": output, "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": "Command timed out after 30 seconds"}
    except Exception as e:
        return {"status": "error", "output": str(e)}


def read_file(filepath: str) -> dict:
    try:
        path = Path(filepath).expanduser()
        if not path.exists():
            return {"status": "error", "output": f"File not found: {filepath}"}
        if path.is_dir():
            entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
            listing = "\n".join(
                f"{'[DIR] ' if e.is_dir() else '      '}{e.name}" for e in entries
            )
            return {"status": "success", "output": f"Directory listing for {filepath}:\n{listing}"}
        content = path.read_text(errors="replace")
        return {"status": "success", "output": content}
    except Exception as e:
        return {"status": "error", "output": str(e)}


def write_file(filepath: str, content: str) -> dict:
    try:
        path = Path(filepath).expanduser()
        backed_up = False
        if path.exists():
            backup = Path(str(path) + ".backup")
            shutil.copy2(path, backup)
            backed_up = True
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        note = " (previous version saved as .backup)" if backed_up else ""
        return {"status": "success", "output": f"Written {len(content)} chars to {filepath}{note}"}
    except Exception as e:
        return {"status": "error", "output": str(e)}


def edit_waybar_color(element: str, color: str) -> dict:
    css_path = Path("/home/rina/.config/waybar/style.css")
    if not css_path.exists():
        return {"status": "error", "output": "Waybar style.css not found at /home/rina/.config/waybar/style.css"}
    try:
        shutil.copy2(css_path, str(css_path) + ".backup")
        content = css_path.read_text()

        # try to find and patch existing rule for element
        # handles: .element { ... color: X; ... }  or  #element { ... }
        target = element.lstrip(".#")
        selectors = [f".{target}", f"#{target}", f" {target} ", f"\n{target} "]
        modified = False

        # build a simple state-machine parser
        lines = content.split("\n")
        result_lines = []
        depth = 0
        in_target = False
        color_replaced = False

        for line in lines:
            stripped = line.strip()
            if not in_target:
                for sel in selectors:
                    if sel in line and "{" in line:
                        in_target = True
                        depth = line.count("{") - line.count("}")
                        color_replaced = False
                        break
            else:
                depth += line.count("{") - line.count("}")
                if depth <= 0:
                    in_target = False

                if in_target and not color_replaced:
                    # replace color: or background: based on intent
                    prop = "background" if "background" in element.lower() else "color"
                    if f"{prop}:" in stripped or f"{prop} :" in stripped:
                        indent = len(line) - len(line.lstrip())
                        line = " " * indent + f"{prop}: {color};"
                        color_replaced = True
                        modified = True

            result_lines.append(line)

        if modified:
            css_path.write_text("\n".join(result_lines))
            return {"status": "success", "output": f"Updated {element} color to {color} in waybar style.css"}
        else:
            # append new rule
            prop = "background" if "background" in element.lower() else "color"
            new_rule = f"\n.{target} {{\n    {prop}: {color};\n}}"
            css_path.write_text(content + new_rule)
            return {
                "status": "success",
                "output": f"Appended new CSS rule for .{target} with {prop}: {color} (element not found in existing rules)",
            }
    except Exception as e:
        return {"status": "error", "output": str(e)}


def read_config(app: str) -> dict:
    config_base = Path("/home/rina/.config")
    try:
        # try direct path first
        candidate = config_base / app
        if candidate.is_file():
            return {"status": "success", "output": candidate.read_text(errors="replace")}
        if candidate.is_dir():
            # list files and read main config files
            files = sorted(candidate.rglob("*"))
            file_list = [str(f.relative_to(config_base)) for f in files if f.is_file()]
            output = f"Config directory for {app} (files):\n" + "\n".join(file_list)
            # auto-read common config files (small ones)
            common_names = ["config", "config.conf", "config.toml", "style.css", f"{app}.conf"]
            for fname in common_names:
                fpath = candidate / fname
                if fpath.exists() and fpath.stat().st_size < 10000:
                    output += f"\n\n--- {fname} ---\n{fpath.read_text(errors='replace')}"
                    break
            return {"status": "success", "output": output}
        # fuzzy search
        matches = list(config_base.glob(f"**/{app}*"))
        if matches:
            p = matches[0]
            if p.is_file() and p.stat().st_size < 50000:
                return {"status": "success", "output": f"Found: {p}\n\n{p.read_text(errors='replace')}"}
            return {"status": "success", "output": f"Found: {p} (directory or large file)"}
        return {"status": "error", "output": f"No config found for '{app}' in /home/rina/.config/"}
    except Exception as e:
        return {"status": "error", "output": str(e)}


def system_info() -> dict:
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        ram = psutil.virtual_memory()
        load = os.getloadavg()

        lines = [
            "=== System Info ===",
            f"CPU:  {cpu:.1f}% used  ({cpu_count} cores)  |  Load avg: {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}",
            f"RAM:  {ram.used / 1e9:.1f} GB / {ram.total / 1e9:.1f} GB  ({ram.percent}% used)",
        ]

        for mount in ["/", "/mnt/1TB", "/home"]:
            try:
                d = psutil.disk_usage(mount)
                lines.append(
                    f"Disk {mount}: {d.used / 1e9:.1f} GB / {d.total / 1e9:.1f} GB  ({d.percent}% used)"
                )
            except Exception:
                pass

        # top processes
        procs = sorted(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                       key=lambda p: p.info.get("cpu_percent") or 0, reverse=True)[:5]
        lines.append("\nTop processes by CPU:")
        for p in procs:
            lines.append(f"  [{p.info['pid']:6}] {p.info['name']:20} cpu={p.info.get('cpu_percent',0):.1f}%  mem={p.info.get('memory_percent',0):.1f}%")

        return {"status": "success", "output": "\n".join(lines)}
    except ImportError:
        # fallback without psutil
        result = execute_bash("free -h && df -h / && uptime")
        return result
    except Exception as e:
        return {"status": "error", "output": str(e)}


def find_files(pattern: str, directory: str = "/home/rina") -> dict:
    try:
        search_path = Path(directory).expanduser()
        if not search_path.exists():
            return {"status": "error", "output": f"Directory not found: {directory}"}
        matches = list(search_path.rglob(pattern))
        if not matches:
            return {"status": "success", "output": f"No files matching '{pattern}' found in {directory}"}
        matches.sort()
        result = f"Found {len(matches)} match(es) for '{pattern}' in {directory}:\n"
        result += "\n".join(str(m) for m in matches[:60])
        if len(matches) > 60:
            result += f"\n... and {len(matches) - 60} more results"
        return {"status": "success", "output": result}
    except Exception as e:
        return {"status": "error", "output": str(e)}


# ── tool registry ──────────────────────────────────────────────────────────────

TOOLS_SCHEMA = [
    {
        "name": "execute_bash",
        "description": "Execute a bash command and return its output. Timeout 30s. For dangerous commands (rm -rf, dd, mkfs) returns a confirmation prompt.",
        "parameters": {
            "command": "str – The bash command to run",
            "confirmed": "bool (optional) – Pass true to confirm a dangerous command",
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file or list a directory.",
        "parameters": {"filepath": "str – Absolute path to file or directory"},
    },
    {
        "name": "write_file",
        "description": "Write content to a file. Auto-creates parent dirs. Saves .backup of existing file.",
        "parameters": {
            "filepath": "str – Destination path",
            "content": "str – Full content to write",
        },
    },
    {
        "name": "edit_waybar_color",
        "description": "Change a color in /home/rina/.config/waybar/style.css for a given CSS element.",
        "parameters": {
            "element": "str – CSS selector/class name (e.g. 'clock', 'workspaces', '#tray')",
            "color": "str – CSS color value (e.g. '#ff0000', 'rgba(0,255,0,0.8)')",
        },
    },
    {
        "name": "read_config",
        "description": "Read a config file/directory from /home/rina/.config/",
        "parameters": {"app": "str – App name (e.g. 'waybar', 'hypr', 'nvim', 'kitty')"},
    },
    {
        "name": "system_info",
        "description": "Get current CPU, RAM, disk usage and top processes.",
        "parameters": {},
    },
    {
        "name": "find_files",
        "description": "Find files matching a glob pattern in a directory.",
        "parameters": {
            "pattern": "str – Glob pattern (e.g. '*.py', '*.conf', 'waybar*')",
            "directory": "str – Search root (default: /home/rina)",
        },
    },
]

TOOL_FUNCTIONS = {
    "execute_bash": execute_bash,
    "read_file": read_file,
    "write_file": write_file,
    "edit_waybar_color": edit_waybar_color,
    "read_config": read_config,
    "system_info": system_info,
    "find_files": find_files,
}


def execute_tool(name: str, args: dict) -> dict:
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return {"status": "error", "output": f"Unknown tool: '{name}'. Available: {list(TOOL_FUNCTIONS)}"}
    try:
        return fn(**args)
    except TypeError as e:
        return {"status": "error", "output": f"Bad arguments for '{name}': {e}"}
    except Exception as e:
        return {"status": "error", "output": f"Tool '{name}' crashed: {e}"}
