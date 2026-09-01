"""Pinned ChatDev checkout checks. Does not vendor or invoke upstream."""
PINNED_COMMIT = "4fb2db0ea90375ce1059f44fe03ffbd191a7a169"
SDK_SIGNATURE = "def run_workflow(yaml_file, *, task_prompt, attachments=None, session_name=None, fn_module=None, variables=None, log_level=None)"


def validate_chatdev_lock(lock, sdk_source=None):
    if lock.get("commit") != PINNED_COMMIT:
        raise ValueError("ChatDev pin mismatch; see config/upstream.lock.json")
    if sdk_source is not None and "def run_workflow" not in sdk_source:
        raise ValueError("Pinned SDK signature not found")
    if sdk_source is not None and "task_prompt" not in sdk_source:
        raise ValueError("Pinned SDK signature not found")
    return {"commit": PINNED_COMMIT, "sdk_entrypoint": lock.get("sdk_entrypoint", "runtime.sdk.run_workflow")}
