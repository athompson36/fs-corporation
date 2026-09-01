# Employee development, training and performance

Hired employees are first-class records. Positions remain catalog titles; a person filling a role has a background, configurable attributes, a training file and a performance history. Hardware skill gaps from [20-hardware-skills.md](20-hardware-skills.md) still apply. Human Resources from [21-quality-hr.md](21-quality-hr.md) owns this workflow.

## Hire

HR or the CEO hires with a position id (`department:title`), display name, JSON attributes and a written background. Duplicate ids are rejected. Empty backgrounds are rejected. Attributes are configurable (seniority, specialties, languages, tools, or other keys the owner supplies).

```python
c.hire_employee("people:HR Director", "dev-ada", "engineering:Developer", "Ada Developer",
                {"seniority": "mid", "specialties": ["firmware"]},
                "Former ESP32 hobbyist; expanding board-support skills.")
```

Pertinent skills come from [config/employee-development.json](../config/employee-development.json): company-wide skills, department skills and position skills. Hire assigns documented training for every missing pertinent skill.

## Regular training

Training interval defaults to 90 days. `schedule_company_training` reassigns overdue skills for every active employee. Hired employees cannot dispatch product work while training is overdue. Actors who are not hired employees (the local demo `head` fixture) remain ungated by this rule.

Study uses the same HTTPS metadata path as market signals and hardware learning. Page text cannot amend policy. Live fetch stays fail-closed. HR or the CEO certifies; the learner cannot.

`training_file` is the reviewable record: source, summary, study time, certifier and due skills.

## Performance

HR or the CEO sets integer goals and records reviews with a 0–100 score and notes. An employee cannot review themselves. `performance_trend` returns the score series, improving/declining/stable direction from the last two reviews, and current goals.

Loopback: `POST /api/v1/employees`, `GET /api/v1/employees/{id}`, `GET /api/v1/employees/{id}/training`, `POST /api/v1/training/schedule`, `POST /api/v1/employees/{id}/goals`, `POST /api/v1/employees/{id}/reviews`, `GET /api/v1/employees/{id}/performance`.
