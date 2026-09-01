# CEO rules and delegated authority

## Authority hierarchy

Human owner → CEO authority → department-head delegation → specialist/contractor assignment. A human may occupy the CEO position directly. An AI CEO may propose direction and approve actions only within a root delegation defined by the human. Hybrid mode reserves strategic exceptions for the human while delegating routine decisions.

Each delegation contains subject, grantor, optional parent grant, permitted actions, resource/project/branch scopes, data classification, maximum action cost, aggregate budget, start/expiry time, approval rights, escalation rules and revocation status. A head may approve a subordinate's work only if the grant includes that approval capability. Delegating execution does not imply delegating authority to redelegate.

## Decision algorithm (production)

1. Resolve authenticated principal, company membership and applicable grants.
2. Apply owner/system restrictions and explicit denies before allows.
3. Intersect all child permissions with parent scopes; reject cycles and invalid parents.
4. Validate current policy version, expiry/revocation, resource identity and exact branch/action.
5. Check data/model/tool compatibility.
6. Atomically check company, department, project and task budgets and reserve worst-case cost.
7. Validate required approval against exact operation, target, payload, cost ceiling and expiry.
8. Record outcome, reasoning code and policy references; dispatch only on allow.

Permission checks are deterministic code. Natural-language rules must be compiled into explicit constraints and reviewed before activation. Ambiguous rules remain proposals until clarified; the system should not invent new authority.

## Rule evolution

Heads submit amendments with observed problem, examples, proposed diff, expected benefits, cost impact and rollback plan. The authorized CEO approves a specific diff. Activation increments the version and revalidates queued tasks and approvals. Conflicting proposals based on an old version must be rebased.

Procedural improvements within existing authority can be delegated separately from permission changes. For example, Engineering may refine its code review checklist but cannot enable production deployment or increase its budget through that checklist.

## Illustrative delegation

Marketing can research selected markets and prepare campaign drafts up to a specified budget. It may ask Art for assets within an agreed interdepartmental allocation. It cannot publish externally without the publishing capability. Engineering can prepare changes on `company/*` branches for one enrolled fork; upstream merge and deployment are separate actions.

## CEO decision package

Title and requested decision; project/department; evidence links; proposal and alternatives; exact resources/actions; budget impact; likely outcome and uncertainty; material risks; expiry; recommended approver; accept/edit/reject/request-research controls.

## Reference implementation

`propose_policy` accepts a valid next-version policy. `approve_policy` / `reject_policy` / `withdraw_policy` require the appropriate identity. `rollback_policy` writes a new version restoring earlier content. `execute_mock` checks actor/action/project/expiry and budget, including parent/child delegations, blocks hardware projects that still have skill gaps, and blocks hired employees whose training is overdue. `inspect_quality` records a Quality Control verdict; `accept_project` requires a passing inspection of the exact artifact. `approve_action` may be used by the CEO or a grant with `approval_rights`. `pause` blocks new mock dispatch. A revised policy can remove a grant, immediately denying new actions. `revoke_delegation` cancels queued descendant work. Acceptance and expansion approval are CEO-only in the core. Skill certification is HR or CEO.

The loopback service authenticates bearer tokens and maps them to `principal_id`. Direct SQLite access and process memory remain outside the trust boundary.

**Still not a production isolation boundary:** container sandboxes, live provider credentials, GitHub App writes, and non-loopback deployment.
