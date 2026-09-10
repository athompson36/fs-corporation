const OPTIONS: [PanelMode, string][] = [
  ["browse", "Browse"],
  ["manage", "Manage"],
];

export type PanelMode = "browse" | "manage";

export type ModeSwitchProps = {
  mode: PanelMode;
  onChange: (mode: PanelMode) => void;
  label?: string;
};

export function ModeSwitch({ mode, onChange, label = "Panel mode" }: ModeSwitchProps) {
  return (
    <div className="segmented panel-mode" role="tablist" aria-label={label}>
      {OPTIONS.map(([value, text]) => (
        <button
          key={value}
          type="button"
          role="tab"
          aria-selected={mode === value}
          className={mode === value ? "active" : ""}
          onClick={() => onChange(value)}
        >
          {text}
        </button>
      ))}
    </div>
  );
}
