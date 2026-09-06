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

## Visual design pass

Icons: `src/ui/icons.py` -- 38 hand-built Lucide-style line icons (SVG path
data, no bundled asset files, no network fetch), recolored per-theme and
rendered via QSvgRenderer. Used throughout: sidebar nav, buttons, badges,
stat cards, empty states, the drop zone.

Notifications: `src/ui/widgets/toast.py` -- floating, auto-dismissing,
stacked bottom-right, for routine confirmations (report exported) that
shouldn't interrupt with a modal dialog. QMessageBox is still used for
destructive-action confirmations (delete exam) and blocking errors.

Elevation: `Card` (`src/ui/widgets/common.py`) has a real drop shadow via
`QGraphicsDropShadowEffect`, with a hover-lift option for interactive
cards (stat tiles).

Two real bugs found and fixed during this pass, not just polish:
- **Icon rendering**: `QSvgRenderer.render(painter)` with no explicit
  target rect, combined with a pixmap that has `devicePixelRatio() != 1`,
  double-applies the DPR scale and only a corner of the icon renders.
  Fixed by always passing an explicit `QRectF(0, 0, size, size)` in
  logical pixels.
- **Stale-widget overlap on refresh**: every page's "clear and rebuild"
  pattern used `layout.takeAt()` / `removeWidget()` + `deleteLater()`.
  `deleteLater()` defers actual deletion to the next event-loop cycle,
  but a widget removed from a layout keeps rendering at its last
  geometry until then -- so a fast refresh (e.g. re-filtering the
  Review Center) briefly showed old and new content overlapping. Fixed
  by hiding the widget immediately (`clear_layout()` helper, and an
  explicit `.hide()` before `.deleteLater()` on the QScrollArea-swap
  pages).
- (Also fixed as part of the same pass: the base `QWidget` QSS rule was
  giving every widget, including plain labels, an explicit background
  color, which showed as a visible "box" behind word-wrapped text
  inside cards. Background is now only set on root containers.)

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
