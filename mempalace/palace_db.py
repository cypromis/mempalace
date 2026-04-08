"""
palace_db.py — Central ChromaDB client factory for MemPalace.

All ChromaDB access in production code must go through this module.
Returns HttpClient when remote config is present, PersistentClient otherwise.
"""

import os

import chromadb

from .config import MempalaceConfig
from .config import DEFAULT_COLLECTION_NAME as DEFAULT_COLLECTION

_http_clients = {}  # cache: (host, port, ssl) -> HttpClient


def get_client(palace_path=None):
    """Return a ChromaDB client.

    Uses HttpClient when chroma_host is configured; PersistentClient otherwise.
    palace_path is ignored in remote mode — the server manages its own storage.
    HttpClient instances are cached by (host, port, ssl) to avoid repeated
    connection overhead in long-lived processes (e.g. MCP server).
    """
    cfg = MempalaceConfig()
    if cfg.chroma_host:
        key = (cfg.chroma_host, cfg.chroma_port, cfg.chroma_ssl)
        if key not in _http_clients:
            _http_clients[key] = chromadb.HttpClient(
                host=cfg.chroma_host, port=cfg.chroma_port, ssl=cfg.chroma_ssl
            )
        return _http_clients[key]

    path = palace_path or cfg.palace_path
    os.makedirs(path, exist_ok=True)
    return chromadb.PersistentClient(path=path)


def get_collection(palace_path=None, name=DEFAULT_COLLECTION):
    """Return the named ChromaDB collection, creating it if absent.

    palace_path is passed to get_client and is ignored in remote mode.
    """
    client = get_client(palace_path=palace_path)
    return client.get_or_create_collection(name)
