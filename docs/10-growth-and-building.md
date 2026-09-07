# Company growth and virtual construction

## Two distinct forms of progress

Visual progress celebrates accepted project milestones. Operational expansion adds positions, enabled tools, infrastructure or ongoing cost only when justified and approved. Keep simulated construction credits separate from real provider bills and real revenue.

Each unique accepted project may award one progress credit in the first release. Later use weighted milestones with an explicit anti-duplication policy. Reopening work or retrying an acceptance event cannot farm credits. If acceptance is withdrawn, record a compensating event; do not erase the historical decision.

## Growth proposal

Evidence of a bottleneck or missing capability; accepted milestone references; expected workload; alternatives such as shared staff; requested positions/rooms/tools; setup and ongoing real costs; simulated cost; success measures; approval scope; rollback/deactivation plan.

Company size is not itself a success measure. The company can expand visual space without activating expensive workers. A room can host several roles, and dormant staff retain knowledge without continuous inference.

## Facilities workflow

Facilities architect drafts a room plan. Finance estimates operating impact. CEO or authorized delegate approves the exact expansion. General contractor breaks it into provisioning tasks. Specialist contractors configure storage, workspace isolation, permitted tools and visual layout. An independent inspector verifies required capabilities and permission boundaries. Accepted inspection activates the room and emits room.built.

These are virtual/software contractors. A networking contractor configures an approved service boundary; an art contractor creates room assets; a workspace contractor provisions approved task storage. No physical building services are implied.

## Visual stages

1. Small office: executive desk and shared project workspace.
2. Dedicated studios: Engineering, Art and Marketing zones.
3. Operations floor: Finance, IT, Support and meeting rooms.
4. Specialized spaces: media studio, training center and research lab.
5. Additional wings/buildings: justified by the portfolio and capacity.

The chrome uses the cosmic-restraint system. The CEO desk shows persisted department rooms on a readable top-down 2D grid and warning chips for unmet requirements. Persisted department staff appear as small validated sprite markers, or explicitly neutral markers when no sprite is set; selecting one opens its persisted worker card. When no floorplan rooms exist, the isometric expansion ledger remains the fallback. Furnished custom room art can still be layered later. Animation respects `prefers-reduced-motion`.

## Projection rules

Room identity derives from expansion ID; room state derives from authoritative events. Replaying events must reconstruct the same operational building. Agent movement and construction effects are decorative and must not pretend that a task is running or delay actual completion. If a task fails, show its actual failed/blocked state.

Clicking a room reveals its purpose, staff/model assignments, queue, artifacts, simulated costs and related decisions from persisted events. Show proposed rooms distinctly from active rooms. Offline/dormant activity is visible without implying live agents. Empty staff or deliverable lists stay empty.

## Current core

Floorplans, grid-positioned rooms, per-department minimum room requirements, worker sprite selections, and editable identity fields persist in SQLite. CEO or authenticated admin-companion layout mutations fail closed on unknown room types, grid bounds, overlap, and removal of expansion-bound rooms. Sprite and identity mutations additionally require HR or CEO authority and reject values outside the seeded sprite catalog. A default plan places one room for every non-retired department; requirement gaps and missing sprites remain warnings/placeholders, never invented operational state.

The separate growth ledger remains: CEO acceptance of one synthetic draft per project creates one expansion proposal, and approved contractor work can build it. Floorplan layout does not imply staffing, running models, real resource provisioning, or real cost.
