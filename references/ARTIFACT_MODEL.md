# Artifact and cache model

Use artifact identity to avoid redundant work.

A durable artifact record should include:

```json
{
  "artifact_id": "reader-...",
  "type": "reader_artifact",
  "path": "...",
  "producer": "nature-reader",
  "producer_version": {
    "source": "nature",
    "commit": "...",
    "tree_sha": "..."
  },
  "inputs": ["paper-..."],
  "input_hashes": ["..."],
  "sha256": "...",
  "created_at": "...",
  "tags": []
}
```

A cached artifact is reusable if its semantically relevant inputs and producer version remain compatible. Updating a producer does not force regeneration unless the new task requires the changed behavior or the user chooses to refresh.
