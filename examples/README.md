# Runnable examples

Run from the project root:

```bash
python3 -m examples.governance
python3 -m examples.model_selection
```

The first demonstrates an initially denied mock PR-preparation task, CEO approval and successful bounded mock execution. It creates no PR. The second selects the eligible mock reviewer profile while disabled profiles are skipped. Both are offline and use no credentials.

Use [project-brief.md](../templates/project-brief.md) to prepare a real project and [delegation.md](../templates/delegation.md) for its authority proposal. Do not replace placeholder repository names until an actual project has been selected.

## Master Consultant

`python3 -m company.consultant --root .` reviews local code/configuration with limited static rules. `python3 -m examples.consultant_proposal` demonstrates a synthetic proposal and CEO decision without executing changes.

The loopback service is `python3 -m company.service`. Backup/restore: `python3 -m company backup` and `python3 -m company restore`.

Hardware firmware enrollment, skill gaps and study/certify are in the core (`enroll_hardware_project`, `study_skill`, `certify_skill`) and loopback API. Live documentation fetch is disabled. Quality Control inspection (`inspect_quality`) is required before acceptance. Hire, training files and performance trends are in [22-employee-development.md](../docs/22-employee-development.md).
