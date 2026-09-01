# Quality Control and Human Resources

## Quality Control

Quality Control independently verifies product work. Engineering may still employ a QA Engineer for in-team testing. The Master Consultant remains an adviser. Neither replaces this department.

Flow: producer creates an artifact → Quality Inspector records `pass` or `fail` on the exact hash → only a passing latest inspection allows the CEO to accept. The producer, CEO, and other departments cannot record the QC verdict.

Facilities construction still uses the existing room inspector. Policy, consultant proposals, and study records are not product deliverables.

```python
c.inspect_quality("quality:Quality Inspector", task_id, artifact_hash, "pass")
c.accept_project("human-ceo", task_id, artifact_hash)
```

Loopback: `POST /api/v1/tasks/{id}/quality-inspect`.

## Human Resources

The People catalog department is named **Human Resources** (id `people`) so hardware learning assignments keep working. HR oversees staffing, development, and training. Knowledge Curators file procedures. The HR Director or Training Specialist certifies completed study; the CEO may still certify. Learners cannot certify themselves.

```python
c.certify_skill("people:HR Director", assignment_id)
c.development_roster("people:HR Director")
```

Loopback: `GET /api/v1/hr/development`. Hire, training files, goals and reviews are in [22-employee-development.md](22-employee-development.md).
