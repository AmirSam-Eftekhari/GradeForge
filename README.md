<div align="center">

# GradeForge

### Explainable AI grading for descriptive exams.

**GradeForge** is an offline-first, multilingual desktop application for grading descriptive and open-ended exams with semantic analysis, confidence-aware review, local history, analytics, and report generation.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-informational)](LICENSE)

</div>

---

## Overview

GradeForge is a local grading platform designed for descriptive and open-ended exam responses.

It is built around a simple principle:

> **When the available evidence is not strong enough, the system should ask for human review rather than manufacture confidence.**

Instead of reducing an answer to a single similarity score, GradeForge combines multiple interpretable signals:

- **Semantic similarity** — how closely the response matches the expected meaning.
- **Concept coverage** — whether important ideas from the answer key are present.
- **Relevance** — whether the response actually addresses the question.
- **Omission penalties** — meaningful concepts that are missing can affect the score.
- **Contradiction detection** — conflicting statements can reduce confidence or trigger review.
- **Confidence** — uncertain results are surfaced instead of silently accepted.
- **Configurable strictness** — grading behavior can be adjusted without rewriting the engine.

The result is not simply a grade. It is a **reviewable grading decision** with supporting signals and an audit-friendly workflow.

GradeForge can be used through both a **PySide6 desktop application** and a **command-line interface**.

---

## Why GradeForge?

Automated grading is useful only when its limitations are visible.

A semantic model can recognize that two answers are similar, but similarity alone does not guarantee that an answer is correct, complete, relevant, or free of contradictions. GradeForge therefore treats semantic similarity as one input to a broader grading policy rather than as the final authority.

This leads to a **human-in-the-loop** workflow:

```text
Student Answer
      │
      ▼
Text Extraction / Parsing
      │
      ▼
Semantic & Content Analysis
      │
      ├── Similarity
      ├── Concept Coverage
      ├── Relevance
      ├── Omissions
      └── Contradictions
      │
      ▼
Grading Policy
      │
      ├── Grade
      ├── Confidence
      ├── Explanation
      └── Review Flag
             │
             ▼
      Human Review when needed
```

The goal is not to pretend that AI grading is infallible. The goal is to make automated grading **useful, inspectable, and conservative when evidence is weak**.

---

## Core Features

### Intelligent grading

- Multilingual document and OCR pipeline
- Transformer-based semantic embeddings
- Automatic TF-IDF fallback when the transformer backend is unavailable
- Configurable grading policies
- Five strictness levels:
  - `very_lenient`
  - `lenient`
  - `balanced`
  - `strict`
  - `very_strict`
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

- Native PySide6 interface
- Dashboard and exam overview
- Guided New Grading workflow
- Student and exam history
- Review Center
- Class analytics
- Report generation
- Persistent settings and application state
- Background grading through Qt threads to keep the UI responsive

### Data & reporting

- Local SQLite persistence
- Exam and student history
- Class-level analytics
- PDF reports
- Excel reports
- JSON reports
- Local-first data flow by default

### Developer interface

The GUI and CLI use the **same underlying grading engine**:

```text
Desktop UI ───────┐
                  ├──> Services ──> Grading Engine ──> Reports / Database
CLI ──────────────┘
```

This keeps grading logic independent from presentation and avoids maintaining two separate implementations.

---

## Getting Started

### Requirements

- Python **3.10+**
- Tesseract OCR for OCR-based workflows
- Poppler for PDF rendering
- Python dependencies listed in `requirements.txt`

> **Note:** GradeForge is designed to run locally, but OCR system dependencies such as Tesseract and Poppler must be installed separately from the Python packages.

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd GradeForge
```

Replace `<your-repository-url>` with the URL of your GitHub repository.

### 2. Create a virtual environment

#### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install OCR dependencies

#### Ubuntu / Debian

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-fas tesseract-ocr-ara tesseract-ocr-chi-sim poppler-utils
```

#### Windows

Install **Tesseract OCR** and **Poppler** separately, then make sure their executables are available to GradeForge.

The exact installation path can vary by system.

### 5. Launch GradeForge

```bash
python app.py
```

The desktop application should open with the GradeForge dashboard.

---

## Using the Desktop Application

The typical workflow is:

### 1. Prepare the answer key

Provide the answer key using the format supported by the application.

### 2. Add student papers

Select the directory or input files containing the student responses.

GradeForge can process supported text, document, PDF, and image inputs through its parsing/OCR pipeline.

### 3. Configure grading

Choose the grading options appropriate for the exam, including the desired **strictness level** and semantic backend.

For most use cases, start with:

```text
Strictness: balanced
Embedding backend: auto
```

### 4. Run grading

Start the grading process from the New Grading workflow.

GradeForge processes the papers in the background so the desktop interface remains responsive.

### 5. Review uncertain answers

Open the **Review Center** to inspect questions that were flagged.

For each review item, you can inspect the available grading signals, accept the AI grade, adjust the score, and leave a teacher note.

### 6. Inspect results

Use the student results, exam history, and analytics views to inspect the completed grading run.

### 7. Export reports

Generate the required report format:

- PDF
- Excel
- JSON

---

## CLI Usage

GradeForge can also be used without the desktop interface.

A basic grading run using the included sample data is:

```bash
python main.py \
  --answer-key sample_data/answer_key.txt \
  --students-dir sample_data/students \
  --strictness balanced
```

For the complete command reference:

```bash
python main.py --help
```

Common options include:

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

The CLI is useful for automation, reproducible experiments, batch processing, and development workflows.

---

## Semantic Backends

GradeForge supports multiple semantic-analysis backends:

| Backend | Purpose |
|---|---|
| `sentence_transformer` | Higher-quality semantic grading using transformer embeddings |
| `tfidf` | Lightweight local fallback when transformer dependencies are unavailable |
| `auto` | Automatically selects the preferred available backend |

For higher-quality semantic grading, the transformer backend is recommended.

The TF-IDF fallback allows the grading pipeline to remain usable when the transformer stack is unavailable.

---

## Architecture

GradeForge is organized into focused layers instead of putting the entire application inside the UI.

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
│   ├── reports/              # PDF, Excel & JSON reporting
│   ├── services/             # Application/service layer
│   ├── ui/                   # PySide6 application
│   └── utils/                # Shared utilities
│
├── sample_data/              # Small sample inputs for local testing
├── tests/                    # Automated tests
├── docs/                     # Project documentation & proposal
├── requirements.txt
├── LICENSE
└── README.md
```

### Design principle

The UI is **not** the grading engine.

The core grading pipeline is kept independent from presentation logic so it can be reused by the GUI and CLI, tested independently, and extended with future interfaces.

---

## Grading Pipeline

At a high level, a grading run follows:

```text
Answer Key ──┐
             ├──> Parse ──> Normalize ──> Semantic Analysis ──> Policy ──> Grade
Student Paper┘                                                        │
                                                                      ├──> Confidence
                                                                      ├──> Review Flag
                                                                      └──> Explanation

Grade ──> SQLite History
      └─> PDF / Excel / JSON Reports
```

This separation makes the grading process easier to inspect and evolve.

---

## Privacy & Local-First Design

GradeForge is designed as an **offline-first application**.

Student documents, grading history, configuration, and generated reports can remain on the local machine. The core architecture does not require a cloud grading service.

This is useful for environments where student data should not be uploaded to external services by default.

> **Offline-first does not mean that every dependency is bundled with the repository.** OCR engines and other system-level dependencies still need to be installed locally.

---

## Testing

Run the test suite with:

```bash
pytest
```

The current automated tests focus primarily on the core grading-policy behavior. Integration coverage for OCR, parsing, reporting, and the complete desktop workflow can be expanded as the project evolves.

---

## Project Status

GradeForge currently includes:

- Functional PySide6 desktop application
- Reusable grading engine
- Multilingual OCR/document parsing
- Semantic grading with fallback behavior
- Confidence-aware review workflows
- SQLite persistence
- Exam and student history
- Class analytics
- PDF, Excel, and JSON reporting
- CLI execution
- Automated tests for core grading behavior

### Planned improvements

- Handwriting-specialized OCR
- Teacher-defined rubrics and richer concept extraction
- Broader OCR/parser/report integration tests
- Continuous integration and coverage reporting
- Application packaging and distribution
- Future LMS/cloud integrations as separate extensions

The current release should be considered **functional and usable, but still evolving**.

---

## Documentation

Project documentation lives under [`docs/`](docs/).

The **project proposal will be added there as a PDF once it is finalized**.

---

## Contributing

GradeForge is currently a personal development project, but the codebase is structured with future extension in mind.

If you want to explore the implementation, useful starting points are:

- `src/grading/` — grading behavior and policies
- `src/services/` — application workflows
- `src/parser/` — document and answer parsing
- `src/ocr/` — OCR integration
- `src/ui/` — desktop interface
- `tests/` — regression coverage

When extending the project, keep grading logic independent from presentation logic whenever possible.

---

## License

GradeForge is released under the **MIT License**.

See [`LICENSE`](LICENSE) for details.

---

<div align="center">

**GradeForge — make automated grading explainable, reviewable, and local.**

</div>
