<div align="center">

# GradeForge

### Explainable AI grading for descriptive exams.

An **offline, multilingual desktop application** that turns student answers into structured, reviewable grades — with semantic scoring, confidence analysis, local history, analytics, and professional reports.

<br>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-informational)

</div>

---

## Overview

**GradeForge** is a local-first grading platform for descriptive and open-ended exams.

Instead of treating an AI-generated score as unquestionable, GradeForge is built around a stricter idea:

> **When the evidence is not strong enough, the system should ask for human review rather than manufacture confidence.**

The application reads answer keys and student papers, extracts their content through OCR/document parsing, evaluates answers using semantic and policy-based scoring, explains the result, flags uncertain cases, and stores the entire grading workflow locally.

It can be used through both a **modern PySide6 desktop application** and a **scriptable command-line interface**.

---

## Why GradeForge?

Traditional automated grading often reduces an answer to a single similarity score. That is not enough for serious assessment.

GradeForge separates grading into interpretable signals such as:

- **Semantic similarity** — how closely the answer matches the expected meaning.
- **Concept coverage** — whether important ideas from the answer key are present.
- **Relevance** — whether the response actually addresses the question.
- **Omission penalties** — meaningful concepts that are missing are reflected in the score.
- **Contradiction detection** — conflicting statements can lower confidence or trigger review.
- **Confidence** — uncertain answers are surfaced instead of silently accepted.
- **Configurable strictness** — grading behavior can be adjusted without rewriting the engine.

The result is not just *a grade*, but a grade that can be **inspected, challenged, adjusted, and reported**.

---

## Core Features

### Intelligent grading

- Multilingual document and OCR pipeline
- Transformer-based semantic embeddings
- Automatic TF-IDF fallback when the transformer backend is unavailable
- Configurable grading policies
- Five strictness levels: `very_lenient`, `lenient`, `balanced`, `strict`, `very_strict`
- Per-question scoring and reasoning
- Confidence-aware grading
- Contradiction detection

### Human-in-the-loop review

- Automatic review flags for uncertain answers
- Per-question confidence information
- AI grade acceptance
- Manual score adjustment
- Teacher notes
- Review history

### Desktop application

- PySide6-based native desktop interface
- Dashboard and exam overview
- New Grading workflow
- Student and exam history
- Review Center
- Class analytics
- Reports
- Settings and persistent application state
- Background grading through Qt threads to keep the UI responsive

### Data & reporting

- Local SQLite persistence
- Exam and student history
- Class-level analytics
- PDF reports
- Excel reports
- JSON reports
- Fully local data flow by default

### Developer-friendly interface

The same grading engine powers both the GUI and CLI, avoiding duplicated grading logic.

```text
Desktop UI ───────┐
                  ├──> Services ──> Grading Engine ──> Reports / Database
CLI ──────────────┘
```

---

## Architecture

GradeForge is organized into focused layers rather than putting the entire application inside the UI.

```text
GradeForge/
│
├── app.py                    # Desktop application entry point
├── main.py                   # CLI entry point
├── download_model.py         # Model setup helper
│
├── src/
│   ├── ai/                   # Embedding backend & language detection
│   ├── analytics/            # Class-level analytics
│   ├── config/               # Application & grading configuration
│   ├── database/             # SQLite repository, schema & DTOs
│   ├── grading/              # Core grading engine & policies
│   ├── models/               # Domain models
│   ├── ocr/                  # OCR interfaces & Tesseract implementation
│   ├── parser/               # Student paper & answer-key parsing
│   ├── reports/              # PDF, Excel & JSON report generation
│   ├── services/             # Application/service layer
│   ├── ui/                   # PySide6 application
│   └── utils/                # Shared utilities
│
├── sample_data/              # Small sample inputs for local testing
├── tests/                    # Automated tests
├── docs/                     # Project documentation & future proposal
├── requirements.txt
├── LICENSE
└── README.md
```

### Design principle

The UI is intentionally **not** the grading engine.

This separation makes the core pipeline reusable from the CLI, easier to test, and easier to extend with future interfaces such as web or LMS integrations.

---

## Grading Pipeline

At a high level, a grading run follows this flow:

```text
Answer Key ──┐
             ├──> Parse ──> Normalize ──> Semantic Analysis ──> Policy ──> Grade
Student Paper┘                                                   │
                                                                 ├──> Confidence
                                                                 ├──> Review Flag
                                                                 └──> Explanation

Grade ──> SQLite History
      └─> PDF / Excel / JSON Reports
```

The system is designed so that low-confidence results can be reviewed instead of being treated as automatically correct.

---

## Getting Started

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd GradeForge
```

### 2. Create a virtual environment

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install OCR system dependencies

GradeForge uses Tesseract for OCR and Poppler for PDF rendering.

On Ubuntu/Debian:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-fas tesseract-ocr-ara tesseract-ocr-chi-sim poppler-utils
```

On Windows, install **Tesseract OCR** and **Poppler** separately and make sure their executables are available to the application.

### 5. Launch the desktop application

```bash
python app.py
```

---

## CLI Usage

GradeForge can also run without the desktop interface.

```bash
python main.py \
  --answer-key sample_data/answer_key.txt \
  --students-dir sample_data/students \
  --strictness balanced
```

Useful options include:

```text
--strictness
--languages
--embedding-backend
--no-contradiction-detection
--exam-title
--output-dir
--db
-v / --verbose
```

For the complete command reference:

```bash
python main.py --help
```

---

## Semantic Backend

GradeForge supports two grading backends:

| Backend | Purpose |
|---|---|
| `sentence_transformer` | Higher-quality semantic grading using transformer embeddings |
| `tfidf` | Lightweight local fallback when transformer dependencies are unavailable |
| `auto` | Selects the preferred backend automatically |

For production-quality semantic grading, the transformer stack is recommended.

The project is designed to remain usable when that stack is unavailable rather than failing the entire grading pipeline.

---

## Privacy & Local-First Design

GradeForge is designed as an **offline-first application**.

Student documents, grading history, configuration, and generated reports can remain on the local machine. There is no requirement for a cloud grading service in the core architecture.

This makes the project particularly suitable for environments where student data should not be uploaded to external services by default.

---

## Current Status

GradeForge currently includes:

- A functional PySide6 desktop application
- A reusable grading engine
- Multilingual OCR/document parsing
- Semantic grading with fallback behavior
- Review workflows
- SQLite persistence
- Analytics
- PDF, Excel, and JSON reporting
- CLI execution
- Automated tests for core grading policy behavior

The project is **functional and usable, but still evolving**.

---

## Roadmap

### Near term

- Expand automated coverage across OCR, parsing, grading, and reporting
- Improve handwriting-oriented OCR support
- Add richer teacher-defined rubrics
- Improve concept extraction and explanation quality
- Add CI and coverage reporting
- Package the desktop application for easier distribution

### Longer term

- More advanced rubric-based assessment
- Better document/image review tools
- Optional LMS integrations
- Optional remote/cloud extensions as separate components

The roadmap is intentionally modular: the local grading core should remain usable independently of future integrations.

---

## Documentation

Project documentation will live under [`docs/`](docs/).

The **project proposal will be added there as a PDF once it is finalized.**

---

## Testing

Run the current test suite with:

```bash
pytest
```

The test suite is currently focused on the core grading policy layer and will expand as the project matures.

---

## Contributing

GradeForge is currently a personal development project, but the codebase is structured with future extension in mind.

If you want to experiment with the project, the best places to start are:

- `src/grading/` for grading behavior
- `src/services/` for application workflows
- `src/parser/` for document handling
- `src/ui/` for the desktop interface
- `tests/` for regression coverage

Keep grading logic independent from presentation logic whenever possible.

---

## License

GradeForge is released under the **MIT License**. See [`LICENSE`](LICENSE) for details.

---

<div align="center">

**GradeForge — make automated grading explainable, reviewable, and local.**

</div>
