# MCSP-232 final compliance check

Checked on 5 October 2026 against:

- `MCSP 232 - Project Guidelines - MCA_NEW.pdf`
- the supplied `Project Report (complete).pdf` as an organization/reference example
- the current ONLINE EXAMINATION SYSTEM source and running application
- `docs/test-results.md`

## Result

The 122-page technical report meets the MCSP-232 documentation structure and length guidance. It is ready for the student's administrative details and mandatory physical attachments. It is not submission-complete until the manual items below are supplied.

## Requirements present in the final report

- A4, one-sided report layout with 122 numbered pages.
- Consistent title: ONLINE EXAMINATION SYSTEM.
- Cover page, originality certificate, declaration, acknowledgement and abstract.
- Synchronized table of contents, list of figures and list of tables.
- Introduction, objectives, need, scope and exclusions.
- Cost/effort estimation, PERT and Gantt scheduling.
- IEEE-shaped SRS, functional/non-functional requirements and traceability.
- Context, Level 1 and Level 2 DFDs; ER, use-case, class, activity, sequence and state views.
- Database design, keys, constraints, normalization through 3NF and data dictionary.
- Modular, procedural and user-interface design.
- Current code excerpts for review-flag persistence and question-bank search.
- Unit, integration, system, security and browser evidence.
- Current screenshots for Student, Faculty and Admin workflows.
- System security, role/access matrix and database least privilege.
- Sample student, faculty and admin reports, including CSV export behavior.
- Limitations, future scope, conclusion, bibliography, appendices and glossary.
- CD handover instructions for the complete executable source.

## Current-code updates incorporated

- Persistent `marked_for_review` and answered/not-answered/marked palette states.
- Keyword, topic, difficulty and type question-bank filters.
- Faculty and admin CSV report exports.
- `attempt_answers.marked_for_review` in the data dictionary and traceability.
- Two new regression cases, bringing the recorded suite to 35 passed.
- All 19 application screenshots replaced from the current running build.

## Mandatory items still requiring the student/guide

1. Insert the original approved project-proposal proforma.
2. Insert the approved project proposal/synopsis.
3. Insert the signed and dated guide bio-data.
4. Fill study-centre and regional-centre details.
5. Fill proposal number, approval date and evaluator details.
6. Fill student and guide addresses/designation.
7. Sign and date the Certificate of Originality and declaration; guide signatures must match the proposal.
8. Bind the required CD containing the complete executable project to the last page and retain an identical copy for viva.
9. Print one-sided on A4 and submit the original bound copy in the applicable regional-centre slot.

## Verification note

- The Docker application stack built and ran successfully; current three-role browser evidence was captured from it.
- The project records a real `35 passed in 6.57s` host-local pytest run in `docs/test-results.md`.
- A later container-only rerun did not execute assertions because the Compose-only MySQL account lacks `test_oes` creation privileges and two privilege probes intentionally connect to host-local `127.0.0.1`. This is an environment mismatch, not an observed application-test failure.
- The supplied reference report was used for section-order comparison only. Its very large full-source dump was not copied because MCSP-232 treats the 100–125 documentation pages separately from complete coding.
