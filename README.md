# Exam Grader

AI-powered semantic grading for descriptive (essay/short-answer) exams —
multilingual, explainable, and configurable by grading strictness.

> **Where this build stands:** the grading *engine* — reading answer
> keys, matching student answers, scoring them semantically, explaining
> every deduction, and producing reports — is fully working end to end,
> both behind the original CLI and behind the new PySide6 desktop app,
> **GradeForge** (`python app.py`). See [`src/ui/README.md`](src/ui/README.md)
> for the UI-to-engine module mapping and its honestly-scoped limitations.
> Every module below is real, tested code — nothing here is a mockup.

## Quick start

```bash
pip install -r requirements.txt
# System deps (Ubuntu/Debian): tesseract-ocr + language packs, poppler-utils
sudo apt-get install tesseract-ocr tesseract-ocr-fas tesseract-ocr-ara poppler-utils

# Desktop app
python app.py

# ...or the original CLI
python main.py \
    --answer-key sample_data/answer_key.txt \
    --students-dir sample_data/students \
    --strictness balanced \
    --output-dir Results
```

`python main.py ...` grades the bundled sample exam (3 biology
questions, 3 students) and writes `Results/<Student Name>/{Original
Exam, Grade Report.pdf, grading.json}` plus `Results/class_report.xlsx`.
`python app.py` opens the same pipeline as a guided desktop workflow —
drop the same sample files into New Grading to see it end to end.

## Why the offline demo's scores look "rough"

With no `sentence-transformers`/`torch` installed, the engine
automatically falls back to an offline TF-IDF similarity backend (see
`src/ai/embedding_backend.py`) so the pipeline is still runnable and
testable without a GPU or internet access. **This fallback is
explicitly logged as reduced-accuracy and is not what should grade real
students.** Install the real dependencies for production-grade
multilingual semantic grading:

```bash
pip install sentence-transformers torch
```

and set `EmbeddingConfig.model_name` to `intfloat/multilingual-e5-large`
or `BAAI/bge-m3` (both handle 100+ languages, including Persian/Arabic,
without translation). No code changes needed — `get_backend()` picks
the transformer backend automatically once it's importable.

## Architecture

```
src/
  config/       StrictnessLevel policies + AppConfig dataclasses
  models/       Framework-free domain dataclasses (the shared contract)
  ocr/          OCREngine interface + Tesseract implementation
  parser/       Raw text -> AnswerKey / StudentPaper (question & score
                detection, student identity extraction)
  ai/           Pluggable multilingual embedding backend + language
                detection + contradiction heuristic
  grading/      The transparent scoring formula + GradingEngine
  database/     SQLite schema + repository (only file that imports sqlite3)
                + dto.py (read-side dataclasses for the UI: review state,
                exam/student summaries)
  reports/      PDF (ReportLab) / Excel (openpyxl) / JSON exporters
  analytics/    Class-wide stats: distribution, question difficulty, pass rate
  services/     UI-facing service layer: QThread grading/import workers,
                settings persistence, report-export path resolution
  ui/           PySide6 desktop app (GradeForge) — see src/ui/README.md
  utils/        Logging, etc.
tests/          Unit tests for the scoring policy (the part that most
                needs to be auditable)
```

Every layer depends only on `src/models/domain.py` dataclasses and the
interfaces above it (`OCREngine`, `EmbeddingBackend`) — never on a
concrete implementation. That's what makes `TesseractOCREngine` swappable
for `PaddleOCREngine` later, or `TFIDFBackend` swappable for a real
transformer model, without touching the grading engine, database, or
reports.

### The scoring formula (see `src/grading/policy.py`)

Per the spec's requirement for a *transparent* policy rather than
arbitrary thresholds, every strictness level (`very_lenient` ... `very_strict`)
is just four numbers plugged into one formula:

```
coverage = mean, over each concept in the official answer, of the
           student answer's best-matching similarity to that concept
fraction = ramp(coverage; partial_credit_floor, full_credit_coverage)
                ** omission_penalty_weight
fraction *= contradiction_penalty          (if a contradiction is found)
score    = fraction * max_score            (0 if overall similarity is
                                             below a topic-relevance floor)
```

`tests/test_grading_policy.py` locks in the properties that matter: an
identical answer scores near-max, an empty answer scores 0, an
off-topic answer scores 0, `very_strict` never gives more credit than
`very_lenient` for the same partial answer, and a detected contradiction
never increases the score.

### Question & score detection

`src/parser/common.py` recognizes `Question 1 (3 points)`, `Q3 - 2
Marks`, `2) [5]`, and a standalone `Score: 4`, per the spec's examples.
Student papers are matched to the same question numbers; identity
(name/ID/class) is pulled from `Name:`/`Student:`/`ID:` style labels
(English + Persian labels included) with a confidence score — low
confidence should surface a manual-confirmation prompt in the UI, per
spec (`StudentIdentity.status`).

## What's NOT built yet (by design — see Roadmap)

- Handwriting-specialized OCR (Tesseract handles printed text well;
  handwriting needs a dedicated model — e.g. TrOCR — swapped in behind
  the same `OCREngine` interface)
- GitHub Actions CI, code coverage badges, contributing guide
- Cloud sync, LMS integration, plagiarism detection (all future-phase
  items in the original spec, and all designed for as extension points,
  not implemented)
- A few smaller GradeForge desktop-app gaps are listed honestly in
  [`src/ui/README.md`](src/ui/README.md#known-limitations-honest-not-hidden)

## Roadmap

1. ~~Core grading engine, OCR, parsing, reports, analytics, DB~~ — **done**
2. ~~PySide6 dashboard (dark theme, charts, live batch-grading log) calling
   the exact same `GradingEngine`/`ExamRepository` used by `main.py`~~ — **done**
3. Swap in a real handwriting OCR model behind `OCREngine`
4. Teacher-defined rubrics feeding `Question.rubric_concepts` instead of
   naive sentence-splitting for concept extraction
5. CI, tests for parser/OCR/report layers, packaging for distribution

## License

MIT (add `LICENSE` file before any public release).
