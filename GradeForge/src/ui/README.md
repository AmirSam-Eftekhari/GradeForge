# UI (phase 2)

`PySide6` isn't installable in the sandbox this build was created in (no
network access), so the dark-mode desktop dashboard from the spec is
deliberately not built as unverified/unrunnable code — instead, this
phase's job was to make sure there's a clean, working core to call into.

When picked up, the dashboard is a thin layer over what already exists:

| UI element                        | Calls into                                              |
|-----------------------------------|----------------------------------------------------------|
| "Select answer key / folder"      | `src.parser.document_reader.read_document` + `parse_answer_key` |
| Strictness slider                 | `src.config.strictness.get_policy`                       |
| "Run Grading" button + progress   | `src.grading.engine.GradingEngine.grade_batch`            |
| Per-student result view           | `GradingResult` / `QuestionFeedback` dataclasses          |
| Class dashboard charts            | `src.analytics.class_analytics.compute_class_analytics`   |
| Export buttons                    | `src.reports.*`                                           |
| History / cross-exam view         | `src.database.repository.ExamRepository`                  |

None of the business logic should move into the UI layer — widgets
should only format and display what these modules already return.
