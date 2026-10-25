# Legal reference database

Research & citations searches a local SQLite FTS5 index (`data/legal-reference.sqlite`), and the AI features (command bar answers, drafting, courtroom) retrieve passages from it plus a local Chroma vector index. Searches never send the question to a dataset service. Results show collection, record, passage and source link; excerpts can be appended to the active case draft.

## Coverage

From the full [KanoonGPT/indian-legal-documents](https://huggingface.co/datasets/KanoonGPT/indian-legal-documents) dataset (35,845 documents, Apache-2.0), one copy per law (the most English, then longest, version; copies detected by normalised title):

| Collection | id | Laws | Passages | Search |
|---|---|---|---|---|
| Central Acts, Codes, Ordinances and the Constitution of India | `central` | 1,985 | 44,093 | keyword + vector |
| Central Rules (e.g. DPDP Rules 2025) | `rules` | 2,618 | 66,947 | keyword |
| State Acts and Ordinances | `state` | 7,565 | 144,488 | keyword |

Also: KanoonGPT/indian-case-laws (first 200 records, metadata only, `cases`), the Kaggle IPC–BNS mapping (578 rows, `mapping`). OpenNyAI judgments remain gated (not imported). Not imported from the dataset: central notifications/circulars/orders and state rules (add a group to `GROUPS` in `import_legal_data.py` to include them).

These are dataset copies, not official gazette text. Verify the official text, commencement, amendments and applicability on India Code or the official gazette before relying on a provision. A mapped IPC/BNS section is not necessarily legally identical.

## Search behaviour
- Common abbreviations are expanded (DPDP, BNS, BNSS, BSA, IPC, CrPC, CPC, RTI, IBC, POCSO, POSH, NDPS, GST, RERA, PMLA, UAPA, FEMA, …) because statute text rarely uses them.
- Passages containing every term are preferred; any-term matches fill the rest. Results are re-ranked so a law whose title names the query terms comes first, with a small preference for central Acts.
- Vector search (local MiniLM embeddings, English-oriented) covers `central`, `cases` and `mapping`.

## Rebuild
1. `python import_legal_data.py --source kanoon-full` — downloads the dataset's 8 parquet files (~450 MB) to `data/datasets/indian-legal-documents/` if missing, then replaces the `central`, `rules` and `state` collections (~3 minutes; needs `duckdb`). `--groups central,rules` limits it.
2. Stop the DraftMate server, then `python document_engine.py` to add new passages to the vector index (~30 minutes for `central` on a laptop CPU; already-indexed passages are skipped). Restart the server afterwards. Chroma must not be written by two processes at once.

Other sources: `--source cases --limit 200 --offset 200`, `--source mapping`.

Validation: `python -m unittest test_legal_reference test_sources test_command`.
