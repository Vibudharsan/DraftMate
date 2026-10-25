# Brief review — DraftMate AI – Legal Drafting Studio

Source: `D:\Kode Kurrent\HACKATHON PROBLEM STATEMENT.pdf`, all four pages, including the reference image on page 4.

## Identity and primary workflow

Use the product name specified on page 1: **DraftMate AI – Legal Drafting Studio**. This is a drafting, verification and voice workspace. Case management and additional user-proposed features support that core experience.

Required demonstration: upload a reference → select or invoke a legal skill → generate a draft → review citations → apply voice instructions → export.

## Required behaviour still to implement

- Actual PDF/DOCX processing and document-to-Markdown conversion with source provenance.
- AI drafting, editing and reference-style adaptation preserving substantive meaning unless requested otherwise.
- Modular, extensible skill definitions, invoked from a library or natural language: contracts, notices, petitions, agreements, review, redlining, research, summaries, case analysis and due diligence.
- Citation/authority checking against accessible sources with verified, partially verified and unverified results, source links and explicit uncertainty.
- Voice task interpretation, skill activation, status feedback and confirmation before consequential document actions.
- Selective retrieval, controlled reference context and token management.
- Appropriate document formatting and export, beyond current plain-text export.
- Backend and documented AI/skill/document/voice/verification modules.

## Layout correction for the next design revision

The current landing dashboard is an overview, not the central drafting workspace shown in the brief. Prioritise a central instruction composer/editor with nearby document attachments, skills, voice and supported model selection; provide a separate verification/review panel.

## Additional details visible in the reference image

- Device uploads and selecting existing workspace documents.
- @skill invocation and quick skill chips, including due diligence.
- Tools for browsing, web search and library access.
- Prompt-improvement suggestions and a prompt meter (any score must be explained as a heuristic, not a legal correctness score).
- Categorised/searchable skills for lawyers and students, including drafting, review, research, case tools, compliance, learning and general utilities.
- Templates, matters, conversations and document organisation.

The image is a reference, not evidence that pictured models or integrations are available. The listed repositories and tools on pages 2–3 are study references, not already-integrated components or mandatory dependencies.

## Current prototype status

Working: local draft editing/saving/TXT export, local case metadata, file selection/TXT preview, navigation and illustrative sample-source review. Browser voice recognition is conditional on browser support and permission. AI generation, live verification and other integrations remain labelled as previews.
