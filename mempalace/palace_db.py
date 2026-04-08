"""
palace_db.py — Central ChromaDB client factory for MemPalace.

All ChromaDB access in production code must go through this module.
Returns HttpClient when remote config is present, PersistentClient otherwise.
"""

import os

import chromadb

from .config import MempalaceConfig

DEFAULT_COLLECTION = "mempalace_drawers"


def get_client(palace_path=None):
    """Return a ChromaDB client.

    Uses HttpClient when chroma_host is configured; PersistentClient otherwise.
    palace_path is ignored in remote mode — the server manages its own storage.
    """
    cfg = MempalaceConfig()
    if cfg.chroma_host:
        return chromadb.HttpClient(host=cfg.chroma_host, port=cfg.chroma_port, ssl=cfg.chroma_ssl)

    path = palace_path or cfg.palace_path
    os.makedirs(path, exist_ok=True)
    return chromadb.PersistentClient(path=path)


def get_collection(palace_path=None, name=DEFAULT_COLLECTION):
    """Return the named ChromaDB collection, creating it if absent.

    palace_path is passed to get_client and is ignored in remote mode.
    """
    client = get_client(palace_path=palace_path)
    return client.get_or_create_collection(name)
