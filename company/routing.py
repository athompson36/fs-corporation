"""Ordered model selection; optional benchmark quality preference among eligible profiles."""


def choose_model(registry, department, position, capability, classification="public",
                 task_assignment=None, company_default=None, role=None, benchmarks=None):
    if classification not in {"public", "internal", "restricted"}:
        raise ValueError("Unknown data classification")
    if task_assignment:
        candidates = list(task_assignment) if not isinstance(task_assignment, str) else [task_assignment]
    elif position in registry.get("positions", {}):
        candidates = registry["positions"][position]
    elif department in registry.get("departments", {}):
        candidates = registry["departments"][department]
    elif company_default:
        candidates = list(company_default) if not isinstance(company_default, str) else [company_default]
    else:
        candidates = registry.get("company_default", [])

    eligible = []
    for key in candidates:
        profile = registry["profiles"][key]
        if not profile["enabled"] or capability not in profile["capabilities"]:
            continue
        if classification not in profile["allowed_data"]:
            continue
        eligible.append(key)
    if not eligible:
        raise LookupError("No enabled model meets capability and data constraints")

    pick = eligible[0]
    source = "order"
    quality = None
    if role and benchmarks:
        best_by_profile = {}
        for row in benchmarks:
            if row.get("role") != role:
                continue
            pid = row.get("profile_id")
            if pid not in eligible:
                continue
            q = row.get("quality")
            if q is None:
                continue
            prev = best_by_profile.get(pid)
            if prev is None or float(q) > float(prev):
                best_by_profile[pid] = float(q)
        if best_by_profile:
            # Stable: among max quality, keep earliest eligible order.
            best_q = max(best_by_profile.values())
            for key in eligible:
                if best_by_profile.get(key) == best_q:
                    pick = key
                    source = "quality_max"
                    quality = best_q
                    break

    out = {"profile_id": pick, **registry["profiles"][pick], "benchmark_source": source}
    if quality is not None:
        out["benchmark_quality"] = quality
    return out
