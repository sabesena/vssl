# ✦ vssl memory — the vessel remembers ✦

import os
from pathlib import Path
from typing import Optional

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

MEMORY_DIR = Path("/mnt/1TB/vssl/memory")
EMBED_MODEL = "all-MiniLM-L6-v2"

_CONFIG_DIRS: list[Path] = [
    Path.home() / ".config" / "waybar",
    Path.home() / ".config" / "hypr",
    Path.home() / ".config" / "kitty",
]
_MD_DIR = Path("/mnt/1TB/vssl")

_TEXT_SUFFIXES = frozenset({
    "", ".conf", ".ini", ".toml", ".yaml", ".yml",
    ".json", ".sh", ".css", ".md", ".txt",
    ".py", ".rasi", ".zsh", ".fish", ".cfg",
})


class VsslMemory:
    def __init__(self) -> None:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._model = SentenceTransformer(EMBED_MODEL, device="cuda:0")
        self._client = chromadb.PersistentClient(
            path=str(MEMORY_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        self._conv = self._client.get_or_create_collection(
            "conversation_memory",
            metadata={"hnsw:space": "cosine"},
        )
        self._sys = self._client.get_or_create_collection(
            "system_knowledge",
            metadata={"hnsw:space": "cosine"},
        )

    # ── embedding ───────────────────────────────────────────────────────────────

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text, normalize_embeddings=True).tolist()

    # ── store ───────────────────────────────────────────────────────────────────

    def store_exchange(self, conv_id: str, plea: str, response: str) -> None:
        text = f"User: {plea}\nNyx: {response}"
        doc_id = f"{conv_id}_{hash(text) & 0xFFFFFFFF}"
        self._conv.upsert(
            ids=[doc_id],
            embeddings=[self.embed(text)],
            documents=[text],
            metadatas=[{"conv_id": conv_id}],
        )

    # ── retrieve ─────────────────────────────────────────────────────────────────

    def retrieve_relevant(self, plea: str, n: int = 4) -> str:
        emb = self.embed(plea)
        docs: list[str] = []

        for coll in (self._conv, self._sys):
            count = coll.count()
            if count == 0:
                continue
            k = min(n, count)
            r = coll.query(query_embeddings=[emb], n_results=k)
            docs.extend(r.get("documents", [[]])[0])

        seen: set[str] = set()
        unique: list[str] = []
        for d in docs:
            if d not in seen:
                seen.add(d)
                unique.append(d)

        return "\n---\n".join(unique[:n]) if unique else ""

    # ── index ───────────────────────────────────────────────────────────────────

    def index_system_files(self, paths: Optional[list] = None) -> int:
        indexed = 0

        def _upsert_file(fp: Path) -> None:
            nonlocal indexed
            try:
                if fp.stat().st_size > 50_000:
                    return
                content = fp.read_text(errors="replace").strip()
                if not content:
                    return
                snippet = content[:2000]
                self._sys.upsert(
                    ids=[str(fp)],
                    embeddings=[self.embed(f"{fp.name}\n{snippet}")],
                    documents=[f"# {fp}\n{snippet}"],
                    metadatas=[{"path": str(fp)}],
                )
                indexed += 1
            except Exception:
                pass

        config_dirs = [Path(p).expanduser() for p in (paths or _CONFIG_DIRS)]
        for base in config_dirs:
            if not base.exists():
                continue
            for fp in base.rglob("*"):
                if fp.is_file() and fp.suffix in _TEXT_SUFFIXES:
                    _upsert_file(fp)

        if not paths:
            for fp in _MD_DIR.rglob("*.md"):
                if fp.is_file():
                    _upsert_file(fp)

        return indexed
