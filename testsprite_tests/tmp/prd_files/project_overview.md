# YojanaMitra V3 Hybrid Engine

This project provides backend APIs for scheme eligibility, readiness verification, AI question generation, and re-evaluation using contextual clarifications.

Core flow under test:
- Core deterministic matching by demographics.
- Verification trigger with prior clarification retrieval.
- AI-generated contextual questions with 32-char hash IDs.
- Hybrid answer routing between profile updates and readiness re-evaluation.
- SchemeClarification UPSERT and AI verdict upgrades.
