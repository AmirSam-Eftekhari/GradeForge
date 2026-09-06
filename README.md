# GradeForge

**Offline, multilingual AI-powered semantic grading platform for descriptive exams.**

GradeForge reads answer keys and student papers, grades answers using configurable semantic similarity and grading policies, explains deductions, flags uncertain cases for human review, stores grading history locally, and exports PDF, Excel, and JSON reports.

> **Current status:** The core grading pipeline and PySide6 desktop application are implemented and working. This repository is an active project; handwriting-specialized OCR, broader automated test coverage, CI, and packaging are planned next.

## Features

- Multilingual OCR and document parsing
- Semantic grading with transformer embeddings
- Offline TF-IDF fallback when transformer dependencies are unavailable
- Configurable grading strictness
- Explainable per-question scoring
- Confidence and manual-review workflow
- SQLite-based local history
- Class analytics
- PDF, Excel, and JSON reports
- PySide6 desktop interface
- CLI entry point for automation

## Quick start

```bash
pip install -r requirements.txt
python app.py
```

For the CLI:

```bash
python main.py \
  --answer-key sample_data/answer_key.txt \
  --students-dir sample_data/students \
  --strictness balanced
```

### System dependencies

For PDF/image OCR, install Tesseract OCR and Poppler. On Ubuntu/Debian:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-fas tesseract-ocr-ara poppler-utils
```

For production-quality multilingual semantic grading, install the transformer backend dependencies listed in `requirements.txt`.

## Architecture

```text
src/
├── ai/          Embedding backend and language detection
├── analytics/   Class-level analytics
├── config/      Application and strictness configuration
├── database/    SQLite repository and DTOs
├── grading/     Transparent grading engine and policies
├── models/      Domain models
├── ocr/         OCR interfaces and implementations
├── parser/      Answer-key and student-paper parsing
├── reports/     PDF, Excel and JSON reporting
├── services/    Application/service layer
├── ui/          GradeForge PySide6 desktop application
└── utils/       Shared utilities
```

The UI, CLI, and reporting layers use the same underlying grading engine rather than maintaining separate grading implementations.

## Grading philosophy

GradeForge is designed around a simple principle:

> **When the available evidence is insufficient, the system should flag the answer for review instead of pretending to be certain.**

The scoring policy combines concept coverage, semantic similarity, relevance, omission penalties, and contradiction detection. Strictness levels adjust the policy parameters without changing the underlying grading engine.

## Project proposal

The project proposal will live in [`docs/PROJECT_PROPOSAL.md`](docs/PROJECT_PROPOSAL.md).

## Roadmap

- Handwriting-specialized OCR
- Teacher-defined rubrics and richer concept extraction
- Broader parser/OCR/report integration tests
- Continuous integration and coverage reporting
- Application packaging and distribution
- Future LMS/cloud integrations as separate extensions

## License

MIT License — see [`LICENSE`](LICENSE).
