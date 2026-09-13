import {
  parseCompanionSearch,
  serializeCompanionSearch,
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

if (failed) {
  console.error(`${failed} case(s) failed`);
  process.exit(1);
}
console.log("all urlState cases passed");
