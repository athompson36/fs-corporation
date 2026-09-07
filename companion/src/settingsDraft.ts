import type { CompanySetting, SettingValue } from "./api/client";

export function normalizeSettingDraft(
  draft: SettingValue,
  type: CompanySetting["type"],
): SettingValue {
  switch (type) {
    case "int": {
      const n = typeof draft === "number" ? draft : parseInt(String(draft), 10);
      return Number.isNaN(n) ? draft : n;
    }
    case "float": {
      const n = typeof draft === "number" ? draft : parseFloat(String(draft));
      return Number.isNaN(n) ? draft : n;
    }
    case "bool":
      return draft === true || draft === "true";
    default:
      return String(draft);
  }
}

export function settingDraftDiffers(
  draft: SettingValue | undefined,
  value: SettingValue,
  type: CompanySetting["type"],
): boolean {
  if (draft === undefined) return false;
  return normalizeSettingDraft(draft, type) !== normalizeSettingDraft(value, type);
}
