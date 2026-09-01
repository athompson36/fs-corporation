# Hardware projects and skill learning

The company can take firmware and board-support work for platforms such as ESP32, Raspberry Pi, and RockPro64. This is software for hardware, not physical fabrication. Real-world construction and hiring physical contractors remain out of scope.

## When a project exceeds current skills

Enrollment of a hardware project records the platform and required skills from [config/hardware-skills.json](../config/hardware-skills.json). If no employee has acquired those skills, the company does **not** dispatch product work. It assigns learning to the pertinent roles:

- Engineering developers for firmware, bootloaders, and peripherals
- IT systems administrators for board Linux and device trees on Raspberry Pi / RockPro64-class machines
- People / Knowledge Curators to file the resulting procedure in company memory

Assigned employees study **approved HTTPS documentation** with the same provenance rules as market signals: timestamps, deduplication, and no policy change from page text. Live crawling is disabled until a source list and the action gateway are configured (`LearningAdapter.fetch` raises `NotImplementedError`).

An independent reviewer (Human Resources or the CEO in the reference core) certifies the study evidence. Certification writes `acquired_skills` and an approved memory record. When every required skill has at least one certified holder, dispatch of `draft` / `review` / `prepare_pr` may proceed under ordinary grants. Quality Control still inspects the resulting product artifact before acceptance.

## Commands

```python
c.seed_hardware_skills()
c.enroll_hardware_project("human-ceo", "badge", "ESP32 badge firmware", platform="esp32")
c.project_skill_gaps("badge")
c.study_skill(learner, assignment_id, source="https://...", title="...", published_at=..., observed_at=..., summary="...")
c.certify_skill("human-ceo", assignment_id)
```

Loopback API: `POST /api/v1/projects` with `platform` or `domain=hardware`; `GET /api/v1/projects/{id}/skills`; `POST /api/v1/learning/{id}/study`; `POST /api/v1/learning/{id}/certify`.

Aliases accepted: `rpi`, `raspberrypi`, `rock-pro-64`, `pine64`, `esp-32`, `sbc`.
