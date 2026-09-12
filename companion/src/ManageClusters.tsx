import { useState, type ReactNode } from "react";
import { useWideViewport } from "./useWideViewport";

export type ManageClusterGroup = {
  id: string;
  label: string;
  content: ReactNode;
};

export type ManageClustersProps = {
  ariaLabel: string;
  groups: ManageClusterGroup[];
  defaultGroupId?: string;
};

export function ManageClusters({ ariaLabel, groups, defaultGroupId }: ManageClustersProps) {
  const wide = useWideViewport();
  const initial = defaultGroupId && groups.some((g) => g.id === defaultGroupId)
    ? defaultGroupId
    : groups[0]?.id ?? "";
  const [active, setActive] = useState(initial);

  return (
    <>
      {!wide && (
        <div className="segmented manage-cluster-tabs" role="tablist" aria-label={ariaLabel}>
          {groups.map((group) => (
            <button
              key={group.id}
              type="button"
              role="tab"
              aria-selected={active === group.id}
              className={active === group.id ? "active" : ""}
              onClick={() => setActive(group.id)}
            >
              {group.label}
            </button>
          ))}
        </div>
      )}
      {groups.map((group) =>
        (wide || active === group.id) ? (
          <div key={group.id} className="manage-cluster" data-cluster={group.id}>
            <div className="cluster-head">
              <h2>{group.label}</h2>
            </div>
            {group.content}
          </div>
        ) : null,
      )}
    </>
  );
}
