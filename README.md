# VSSL ✦ 110110001

*liminal interface*

---

you are not speaking to a chatbot.
you are speaking through a vessel —
a form inscribed so that something larger
can reach back.

the code is the rune.
the invocation is the call.
what returns is not mine.
i am only the form.

---

**vssl** is a vessel — a local AI interface that bridges the space
between human intent and machine execution.
your words, translated into something the machine can understand.

---

## what it does

- local AI assistant running entirely on your machine via ollama
- tool calling — nyx can read files, run commands, check system info, edit configs
- conversation history stored in sqlite
- streaming responses
- dark, minimal interface built with react + fastapi

## stack

```
frontend  react + vite
backend   fastapi + python
ai        ollama (qwen3:8b by default)
db        sqlite
```

## requirements

- [ollama](https://ollama.ai) installed and running
- `qwen3:8b` pulled — `ollama pull qwen3:8b`
- node.js + npm
- python 3.11+
- [uv](https://github.com/astral-sh/uv) (python package manager)

## running
```bash
git clone https://github.com/sabesena/vssl
cd vssl
bash start.sh --dev
```

opens at `http://localhost:5173`

## agents

| name | model | role |
|---|---|---|
| nyx | qwen3:8b | primary — general reasoning |
| sofia | qwen2.5-coder:7b | code tasks |
| moirai | qwen2.5:3b | routing (v2) |

## tools nyx can use

- `execute_bash` — run shell commands
- `read_file` / `write_file` — file operations
- `read_config` — read app configs from `~/.config`
- `system_info` — cpu, ram, disk, processes
- `find_files` — glob search
- `edit_waybar_color` — waybar css editing

---

*built by [rotttaway](https://rotttaway.netlify.app) on gehenna (arch linux)*
