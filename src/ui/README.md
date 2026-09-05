# GradeForge desktop UI

PySide6 was installable and runnable in this build environment (unlike
the sandbox the phase-1 note above used to assume), so the dashboard
described in the original spec is implemented and has been smoke-tested
headlessly (`QT_QPA_PLATFORM=offscreen`) end-to-end: answer key import →
student paper import → grading → save → results/analytics/reports/review.

Run it with:

    python app.py

`python main.py ...` remains the original, unmodified CLI.

## Layout

```
app.py                      entry point
src/services/                application/service layer (no UI, no business logic)
    grading_service.py       QThread workers wrapping parser/OCR/ai/grading
    report_service.py        resolves output paths, calls src/reports/*
    settings_service.py      persists AppConfig to the app_settings table
src/database/
    dto.py                   read-side dataclasses (review state, summaries)
    repository.py             extended with list/get/update methods + migration
src/ui/
    app_context.py            shared state: repo, config, theme, navigation signal
    main_window.py             sidebar + QStackedWidget shell
    theme.py                   dark/light QSS
    widgets/                   Card, StatCard, EmptyState, DropZone, bar_chart, badge
    pages/                      one file per screen (see below)
```

## UI element -> existing module mapping

| UI element                          | Calls into                                                        |
|--------------------------------------|--------------------------------------------------------------------|
| New Grading / answer key drop zone   | `AnswerKeyImportWorker` -> `document_reader.read_document` + `parse_answer_key` |
| New Grading / student import queue   | `StudentImportWorker` -> `read_document` + `parse_student_paper`   |
| Strictness radio + parameter bars    | `src.config.strictness.POLICIES` / `StrictnessPolicy` fields       |
| AI/model status badge                | `src.ai.embedding_backend.is_sentence_transformer_available`       |
| "Start Grading" progress screen      | `GradingWorker` -> `src.grading.engine.GradingEngine.grade_paper`  |
| Results Overview / Analytics charts  | `src.analytics.class_analytics.compute_class_analytics`            |
| Student Result page                  | `QuestionFeedback` + review columns (`src/database/dto.py`)        |
| Review Center                        | `ExamRepository.list_review_items` / `update_review`               |
| Reports page                         | `src/services/report_service.py` -> `src.reports.*` (unchanged)    |
| Exams / Students / history pages     | `ExamRepository.list_exams` / `list_all_students` / `get_student_history` |
| Settings                             | `src/services/settings_service.py` -> `AppConfig` (unchanged shape)|

No grading formulas, SQL, or parsing logic live in `src/ui/` — every page
is a thin layer that calls the service layer above and formats what
comes back.

## Known limitations (honest, not hidden)

- No pause (only cancel) for a running grading batch.
- No drag-based question reordering in the Answer Key editor (add/remove/
  edit all work; position doesn't affect grading, since matching is by
  question number, not order).
- No page-by-page OCR/document image preview -- confidence and
  extraction method are shown, but not a rendered page thumbnail.
- Editing a *past* exam's answer key isn't exposed (only before its
  first grading run, in the New Grading wizard) -- retroactively editing
  and re-grading raises product questions (what happens to existing
  human reviews?) this build doesn't try to guess at.
