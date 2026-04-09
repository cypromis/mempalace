# TODO

## Performance

- [ ] Cache `MempalaceConfig()` in `palace_db.py` — currently re-instantiated on every `get_client()` call, causing config file + env var I/O on every DB operation. Acceptable for CLI use; measurable overhead for long-running MCP server. Cache at module level or lazily on first call. Trade-off: env var changes won't be picked up without a server restart.

## Remote ChromaDB (follow-up to PR #294)

- [x] Migrate `palace_graph.py` to use `palace_db.get_collection()` — done.
- [ ] Per-user collection namespacing — multiple users sharing a remote instance currently share a single `mempalace_drawers` collection. Add optional namespace/prefix so each user gets isolated memory.
- [ ] Optional authentication support for remote ChromaDB (token-based).
