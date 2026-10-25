# DraftMate AI – Legal Drafting Studio

Responsive, buildless web-app prototype for the DraftMate AI hackathon brief. All project files live in `D:\Kode Kurrent\legal-studio`.

## Run

Double-click `Start-DraftMate.cmd` on this machine. Alternatively, from this folder run `python server.py`, then visit http://127.0.0.1:4174. No package installation is required. The page uses optional Google Fonts with local font fallbacks. The local address is accessible on this computer only; phone access requires deployment or a separately configured LAN preview.

## Working now

- Responsive overview and navigable legal workspace.
- Shared case selector (My cases, public transcript cases, separate fictional demos, general workspace, and create-case action).
- Browser-local case creation, per-case drafts and argument notes, plain-text export.
- Persistent personal file storage in browser IndexedDB, with TXT/Markdown preview and original downloads. Files can be independent or linked to a case.
- Fictional sample chronology, highlighted source passages, review findings and approved redline append.
- Searchable tool library and generic argument-practice prompts.
- Browser-dependent English/Hindi speech recognition with transcript review. Browser recognition may use its provider's online service.

## Clearly labelled previews

AI generation, PDF/DOCX extraction, actual legal verification, law mappings, reference-style extraction, translation, global research, collaboration, authentication and AI analysis are not implemented. A local Python service now retrieves public news headlines and Supreme Court transcript metadata. Sample evidence is fictional. Nothing in the preview claims production legal accuracy.

## Brief coverage

| Brief requirement | Interface | Backend remaining |
| --- | --- | --- |
| Upload reference documents | Persistent personal library, case links and original downloads | PDF/DOCX extraction and page rendering |
| Draft/edit/export | Editable studio, saving, TXT export | AI generation; DOCX/PDF export |
| Reference-style adaptation | Dedicated skill entry | Style extraction and constrained application |
| Modular legal skills | Searchable skills library and separate workflows | Skill definitions and orchestration |
| Legal research and citations | Source panel and official source links | Retrieval, identity/quote/support checks |
| Verified/partial/unverified | Status concept represented; no false live verification | Evidence-based status assignment |
| Voice agent | EN/HI browser dictation with review | Intent routing and dependable transcription |
| Confirmation for consequential edits | Explicit approval before sample replacement/redline append | Version history, full diff support |
| Token/context efficiency | Planned in architecture | Extraction cache, retrieval budgets, token metrics |
| Minimal workspace/model controls | Full UI with unavailable provider labelled | Server-side model integration |

Expanded ideas have entries for code transition, chronology, contradictions, missing facts, argument practice, case SWOT, constitutional issues, multilingual explanations, international research, public professional research, updates and private collaboration.

## Next implementation boundaries

Keep private case evidence separate from public authorities. Preserve page provenance at extraction time. Store case jurisdiction, procedural stage and relevant dates. Do not infer legal applicability from a section-number substitution. Verification must distinguish citation existence from support for a proposition and current precedent status. Never put provider API secrets in browser code.

The product name is DraftMate AI – Legal Drafting Studio, as specified on page 1 of the brief. The visual design remains editable. Legacy browser-storage keys are retained to preserve drafts and case data.


## Case-aware library update

`workspace.js` / `workspace.css` add shared case context and four library sections:

1. Rule books: official Constitution, new criminal-law collection, India Code and court sources. These are links/descriptions, not a full-text legal corpus.
2. News: on-demand Times of India and Indian Express RSS retrieval, publisher/date/category filters, newest/oldest sorting, current (last seven days) and past collected items. Categories are keyword-based. Unknown publication dates are shown only in All dates. Only headlines, links and metadata are retained; no article bodies are scraped. These publisher feeds are used for this local personal prototype; check publisher permissions before public/commercial redistribution.
3. Public case records: searchable Supreme Court argument-transcript index, grouped hearings and source links. This source is not all Indian cases, and argument transcripts are not judgments. Refresh fetches the published index, not the linked PDFs. Public case selection updates all workspaces.
4. Important documents: original files stored in IndexedDB, optional case association, local downloads and plain-text preview. Stored files survive reload but are specific to this browser and origin. Clearing browser data removes them. No private documents are sent to the local source-fetching service.

`server.py` provides fixed, allowlisted public-source readers and caches metadata under `data/` on D:. If a source fails, existing records are retained and the failure is displayed. Refresh is manual, not a background scheduled monitor. Past news is limited to collected RSS history (up to 2,000 items), not a historical news database.

Run source-parser checks with `python -m unittest test_sources.py`. The app remains local at 127.0.0.1:4174. Do not use a plain static server if you want the refresh buttons to work.

## Calendar and communications

New Calendar & deadlines, Communications and Connections workspaces are implemented in connections.js and connections.css. Local events and reviewed message drafts work without accounts. Google Identity Services and API flows are wired but require an OAuth Web client ID and user consent; live account operations have not been tested. WhatsApp/SMS support compose-and-handoff only. See CONNECTIONS.md for setup, scopes, tests and exact limitations.


### Profile, language and appearance
Click the top-right avatar to edit a local profile (name, qualification, role, firm, city, email and photo). Images are centre-cropped and resized to 256 pixels before local storage. Profile details are not an authenticated account and are not sent to an AI service.
The moon/sun button switches themes; the selection survives reloads. Language preferences include English and all 22 scheduled Indian languages. This sets the preferred dictation language; actual recognition depends on the browser. The interface is still English and bot translation is not yet connected.
The large case reference banner is removed from general pages. Case-dependent tools keep a compact selector explaining which saved case their work belongs to. The document library retains its classification controls.
