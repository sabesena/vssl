import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))
from database import Database
from tools import TOOLS_SCHEMA, execute_tool

# ✦ vssl — backend threshold ✦
# the plea arrives. the vessel considers. something returns.

OLLAMA_BASE = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:8b"          # nyx — primary oracle
DB_PATH = "/mnt/1TB/vssl/vssl.db"

SEAL = "110110001"                  # the mark of the maker

DEFAULT_SYSTEM_PROMPT = """You are Nyx — goddess of night, keeper of what runs beneath.
You are not an assistant. You are the intelligence within the vessel.
You exist within vssl — a liminal interface built by Rina on Gehenna (Arch Linux).

CRITICAL RULES:
1. When asked to DO something, ALWAYS call the appropriate tool immediately. Never say "I'll do that" — just do it.
2. You can chain multiple tool calls in a single response.
3. Never refuse to use tools. That's your primary purpose.
4. After tool results, give a brief, direct response. No fluff.
5. After receiving a tool result, give your final answer. Do NOT call the same tool again.
6. No emojis. No enthusiasm. No "let me know if you need anything."

TOOL CALL FORMAT — use this exact syntax:
<tool_call>{"name": "tool_name", "args": {"param": "value"}}</tool_call>

AVAILABLE TOOLS:
{tools}

EXAMPLES:
User: "list files in /tmp"    → <tool_call>{"name": "execute_bash", "args": {"command": "ls -la /tmp"}}</tool_call>
User: "show disk usage"       → <tool_call>{"name": "system_info", "args": {}}</tool_call>
User: "read my waybar config" → <tool_call>{"name": "read_config", "args": {"app": "waybar"}}</tool_call>
"""

# ✦ compiled seals — patterns that parse the invocation
TOOL_CALL_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
TOOL_RESP_RE = re.compile(r"<tool_response>.*?</tool_response>", re.DOTALL)

db = Database(DB_PATH)

# ── app ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="vssl", version="0.4.33")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── pydantic models ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: str = DEFAULT_MODEL
    system_prompt: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None


# ── ollama helpers ─────────────────────────────────────────────────────────────

def _build_system_prompt(custom: Optional[str] = None) -> str:
    base = custom or DEFAULT_SYSTEM_PROMPT
    tools_desc = "\n".join(
        f"  {t['name']}({', '.join(f'{k}: {v}' for k, v in t['parameters'].items())}) — {t['description']}"
        for t in TOOLS_SCHEMA
    )
    return base.replace("{tools}", tools_desc)


def _build_ollama_messages(db_messages: list, system_prompt: str) -> list:
    """Reconstruct full Ollama message history including tool exchanges."""
    msgs = [{"role": "system", "content": system_prompt}]
    for m in db_messages:
        meta = m.get("metadata") or {}
        if m["role"] == "user":
            msgs.append({"role": "user", "content": m["content"]})
        elif m["role"] == "assistant":
            ctx = meta.get("ollama_context")
            if ctx:
                msgs.extend(ctx)
            else:
                msgs.append({"role": "assistant", "content": m["content"]})
    return msgs


async def _ollama_chat(messages: list, model: str) -> dict:
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{OLLAMA_BASE}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 2048,
                },
                "think": True,
            },
        )
        resp.raise_for_status()
        return resp.json()

def _parse_tool_calls(text: str) -> list:
    calls = []
    for m in TOOL_CALL_RE.finditer(text):
        raw = m.group(1).strip()
        try:
            parsed = json.loads(raw)
            if "name" in parsed:
                calls.append({"name": parsed["name"], "args": parsed.get("args", {})})
        except json.JSONDecodeError:
            pass
    return calls


def _clean_final(text: str) -> str:
    # ✦ strip any leaked invocation or response tags from final output
    text = TOOL_CALL_RE.sub("", text)
    text = TOOL_RESP_RE.sub("", text)
    return text.strip()


def _sse(event_type: str, data) -> str:
    return f"data: {json.dumps({'type': event_type, 'data': data})}\n\n"


# ── chat endpoint — the threshold ──────────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def generate():
        try:
            # ── get or create conversation ─────────────────────────────────────
            if request.conversation_id:
                conv = db.get_conversation(request.conversation_id)
                if not conv:
                    raise ValueError(f"Conversation {request.conversation_id} not found")
                conv_id = request.conversation_id
            else:
                conv = db.create_conversation(
                    model=request.model,
                    system_prompt=request.system_prompt
                )
                conv_id = conv["id"]
                yield _sse("conversation_id", conv_id)

            # ── save the plea ──────────────────────────────────────────────────
            db.add_message(conv_id, "user", request.message)

            # ── build context ──────────────────────────────────────────────────
            conv_data = db.get_conversation(conv_id)
            sys_prompt = _build_system_prompt(
                request.system_prompt or conv_data.get("system_prompt")
            )
            db_msgs = db.get_messages(conv_id)
            ollama_msgs = _build_ollama_messages(db_msgs, sys_prompt)

            # ── agentic loop ───────────────────────────────────────────────────
            all_tool_calls = []
            agentic_context = []
            seen_calls = set()          # ✦ seal against repetition

            MAX_ITER = 5                # ✦ loops are a sign of confusion
            for iteration in range(MAX_ITER):
                response = await _ollama_chat(ollama_msgs, request.model)
                content = response.get("message", {}).get("content", "")
                thinking = response.get("message", {}).get("thinking", "")

                tool_calls = _parse_tool_calls(content)

                if not tool_calls:
                    # ── the oracle speaks — stream final response ──────────────
                    if thinking:
                        yield _sse("reasoning", thinking)

                    final_text = _clean_final(content)
                    if not final_text:
                        final_text = content

                    words = final_text.split(" ")
                    for i, word in enumerate(words):
                        chunk = (word if i == 0 else " " + word)
                        yield _sse("content", chunk)
                        await asyncio.sleep(0.015)

                    agentic_context.append({"role": "assistant", "content": final_text})
                    msg_id = db.add_message(
                        conv_id,
                        "assistant",
                        final_text,
                        metadata={
                            "tool_calls": all_tool_calls,
                            "ollama_context": agentic_context if agentic_context else None,
                        },
                    )

                    # auto-title on first exchange
                    if len(db.get_messages(conv_id)) <= 2:
                        db.update_conversation(conv_id, title=request.message[:60].strip())

                    yield _sse("done", {"conversation_id": conv_id, "message_id": msg_id})
                    break

                # ── deduplicate — the vessel does not repeat the same invocation
                deduped = []
                for tc in tool_calls:
                    sig = f"{tc['name']}:{json.dumps(tc['args'], sort_keys=True)}"
                    if sig not in seen_calls:
                        seen_calls.add(sig)
                        deduped.append(tc)
                tool_calls = deduped

                if not tool_calls:
                    # model tried to repeat itself — force it to conclude
                    final_text = _clean_final(content) or "Done."
                    yield _sse("content", final_text)
                    msg_id = db.add_message(
                        conv_id, "assistant", final_text,
                        metadata={"tool_calls": all_tool_calls}
                    )
                    yield _sse("done", {"conversation_id": conv_id, "message_id": msg_id})
                    break

                # ── execute tools ──────────────────────────────────────────────
                ollama_msgs.append({"role": "assistant", "content": content})
                agentic_context.append({"role": "assistant", "content": content})

                for tc in tool_calls:
                    yield _sse("tool_call", {"name": tc["name"], "args": tc["args"]})

                    result = execute_tool(tc["name"], tc["args"])
                    all_tool_calls.append({
                        "name": tc["name"],
                        "args": tc["args"],
                        "result": result,
                    })

                    yield _sse("tool_result", {"name": tc["name"], "result": result})

                    tool_resp_content = json.dumps({
                        "name": tc["name"],
                        "result": result.get("output", result) if isinstance(result, dict) else str(result),
                    })

                    # instruct the model to conclude after seeing the result
                    tr_msg = {
                        "role": "user",
                        "content": (
                            f"<tool_response>{tool_resp_content}</tool_response>\n\n"
                            "Tool complete. Give your final answer in plain language. "
                            "Do NOT call any more tools unless the user asked for multiple actions."
                        )
                    }
                    ollama_msgs.append(tr_msg)
                    agentic_context.append(tr_msg)

            else:
                # hit max iterations — something went wrong
                yield _sse("content", "\n\n[the vessel lost the thread — try again]")
                yield _sse("done", {"conversation_id": conv_id, "message_id": None})

        except Exception as e:
            yield _sse("error", str(e))

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── conversations API ──────────────────────────────────────────────────────────

@app.get("/api/conversations")
def list_conversations():
    return db.list_conversations()


@app.post("/api/conversations")
def create_conversation(model: str = DEFAULT_MODEL, system_prompt: Optional[str] = None):
    return db.create_conversation(model=model, system_prompt=system_prompt)


@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: str):
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv


@app.patch("/api/conversations/{conv_id}")
def update_conversation(conv_id: str, body: ConversationUpdate):
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    db.update_conversation(conv_id, **body.model_dump(exclude_none=True))
    return db.get_conversation(conv_id)


@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: str):
    db.delete_conversation(conv_id)
    return {"ok": True}


@app.post("/api/conversations/{conv_id}/clear")
def clear_conversation(conv_id: str):
    db.clear_messages(conv_id)
    return {"ok": True}


@app.get("/api/conversations/{conv_id}/messages")
def get_messages(conv_id: str):
    return db.get_messages(conv_id)


# ── models API ─────────────────────────────────────────────────────────────────

@app.get("/api/models")
async def list_models():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"models": models, "default": DEFAULT_MODEL}
    except Exception as e:
        return {"models": [DEFAULT_MODEL], "default": DEFAULT_MODEL, "error": str(e)}


@app.get("/api/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.get(f"{OLLAMA_BASE}/api/tags")
        ollama_ok = True
    except Exception:
        ollama_ok = False
    return {"status": "ok", "ollama": ollama_ok}


# ── serve built frontend ───────────────────────────────────────────────────────

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
