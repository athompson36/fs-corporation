"""Ordered model selection; no model execution or unverifiable model rankings."""
def choose_model(registry, department, position, capability, classification="public",
                 task_assignment=None, company_default=None):
    if classification not in {"public","internal","restricted"}:
        raise ValueError("Unknown data classification")
    if task_assignment:
        candidates=list(task_assignment) if not isinstance(task_assignment,str) else [task_assignment]
    elif position in registry.get("positions",{}):
        candidates=registry["positions"][position]
    elif department in registry.get("departments",{}):
        candidates=registry["departments"][department]
    elif company_default:
        candidates=list(company_default) if not isinstance(company_default,str) else [company_default]
    else:
        candidates=registry.get("company_default",[])
    for key in candidates:
        profile=registry["profiles"][key]
        if not profile["enabled"] or capability not in profile["capabilities"]:
            continue
        if classification not in profile["allowed_data"]:
            continue
        return {"profile_id":key,**profile}
    raise LookupError("No enabled model meets capability and data constraints")
