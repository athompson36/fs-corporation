import {
  parseCompanionSearch,
  serializeCompanionSearch,
  stateAfterTabChange,
  stateAfterModeChange,
  type CompanionUrlState,
} from "../src/urlState.ts";

function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg);
}

function eq(actual: string, expected: string, label: string) {
  assert(actual === expected, `${label}: expected ${JSON.stringify(expected)} got ${JSON.stringify(actual)}`);
}

function roundTrip(search: string, label: string) {
  const parsed = parseCompanionSearch(search);
  const serialized = serializeCompanionSearch(parsed);
  const again = serializeCompanionSearch(parseCompanionSearch(serialized));
  eq(again, serialized, `${label} stable serialize`);
  return { parsed, serialized };
}

function assertTransition(
  id: string,
  startSearch: string,
  apply: (s: CompanionUrlState) => CompanionUrlState,
  expectSerialize: string,
) {
  const start = parseCompanionSearch(startSearch);
  const next = apply(start);
  const serialized = serializeCompanionSearch(next);
  eq(serialized, expectSerialize, id);
  // Single-step transition: applying helper once must equal end state (no mid-flight URL).
  const again = serializeCompanionSearch(apply(start));
  eq(again, expectSerialize, `${id} idempotent apply`);
  console.log(`ok - ${id}`);
}

const cases: Array<{
  name: string;
  input: string;
  expectSerialize: string;
  check?: (s: CompanionUrlState) => void;
}> = [
  {
    name: "finance browse defaults",
    input: "?tab=finance",
    expectSerialize: "?tab=finance",
    check: (s) => {
      assert(s.mode === "browse", "mode browse");
      assert(s.group === "overview", "group overview");
    },
  },
  {
    name: "finance browse periods",
    input: "?tab=finance&group=periods",
    expectSerialize: "?tab=finance&group=periods",
    check: (s) => assert(s.group === "periods", "group periods"),
  },
  {
    name: "finance manage default omits group",
    input: "?tab=finance&mode=manage",
    expectSerialize: "?tab=finance&mode=manage",
    check: (s) => {
      assert(s.mode === "manage", "mode manage");
      assert(s.group === "invoice", "group invoice");
    },
  },
  {
    name: "finance manage adjustment",
    input: "?tab=finance&mode=manage&group=adjustment",
    expectSerialize: "?tab=finance&mode=manage&group=adjustment",
    check: (s) => assert(s.group === "adjustment", "group adjustment"),
  },
  {
    name: "invalid finance browse group → overview",
    input: "?tab=finance&group=not-a-group",
    expectSerialize: "?tab=finance",
    check: (s) => assert(s.group === "overview", "coerced overview"),
  },
  {
    name: "projects manage default omits group",
    input: "?tab=projects&mode=manage",
    expectSerialize: "?tab=projects&mode=manage",
    check: (s) => assert(s.group === "enroll", "group enroll"),
  },
];

const transitions: Array<{
  id: string;
  start: string;
  apply: (s: CompanionUrlState) => CompanionUrlState;
  expect: string;
}> = [
  {
    id: "org-manage-to-finance",
    start: "?tab=organization&mode=manage",
    apply: (s) => stateAfterTabChange(s, "finance"),
    expect: "?tab=finance",
  },
  {
    id: "finance-manage-to-dashboard",
    start: "?tab=finance&mode=manage",
    apply: (s) => stateAfterTabChange(s, "dashboard"),
    expect: "?tab=dashboard",
  },
  {
    id: "corporate-people-to-org",
    start: "?tab=corporate&cluster=people",
    apply: (s) => stateAfterTabChange(s, "organization"),
    expect: "?tab=organization",
  },
  {
    id: "finance-periods-to-manage",
    start: "?tab=finance&group=periods",
    apply: (s) => stateAfterModeChange(s, "manage"),
    expect: "?tab=finance&mode=manage",
  },
  {
    id: "finance-adjustment-to-browse",
    start: "?tab=finance&mode=manage&group=adjustment",
    apply: (s) => stateAfterModeChange(s, "browse"),
    expect: "?tab=finance",
  },
];

let failed = 0;
for (const c of cases) {
  try {
    const { parsed, serialized } = roundTrip(c.input, c.name);
    eq(serialized, c.expectSerialize, c.name);
    c.check?.(parsed);
    console.log(`ok - ${c.name}`);
  } catch (e) {
    failed += 1;
    console.error(`not ok - ${c.name}:`, e instanceof Error ? e.message : e);
  }
}

for (const t of transitions) {
  try {
    assertTransition(t.id, t.start, t.apply, t.expect);
  } catch (e) {
    failed += 1;
    console.error(`not ok - ${t.id}:`, e instanceof Error ? e.message : e);
  }
}

if (failed) {
  console.error(`${failed} case(s) failed`);
  process.exit(1);
}
console.log("all urlState cases passed");
