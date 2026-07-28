import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup, screen } from "@testing-library/react";
import fc from "fast-check";
import type { Conflict } from "../../../lib/types";

// NOTE on test approach:
// The ConflictAlert markup lives inline inside Dashboard.tsx (not an extracted
// component), and Dashboard.tsx also renders Recharts charts (ResponsiveContainer)
// which depend on browser ResizeObserver APIs that aren't polyfilled in the jsdom
// test environment, plus a full Context+Reducer store and multiple API mocks.
// Rendering the full Dashboard page for a purely conditional-rendering/style
// property would be brittle and slow to set up reliably.
//
// Per the task instructions, we take approach (b): a minimal isolated mirror
// component that reproduces, verbatim, the exact conditional (`hasConflicts =
// analysis.conflicts.length > 0`) and inline style object used by the real
// ConflictAlert block in Dashboard.tsx. This keeps the property test focused
// on the actual rendering logic/style contract without needing to stand up
// the entire dashboard page.
function ConflictAlertMirror({ conflicts }: { conflicts: Conflict[] }) {
  const hasConflicts = conflicts.length > 0;

  return (
    <div>
      {hasConflicts && (
        <div
          data-testid="conflict-alert"
          className="rounded-lg p-4 animate-slideDown"
          style={{
            background: "rgba(237,28,36,0.06)",
            border: "1px solid rgba(237,28,36,0.25)",
            borderLeft: "4px solid var(--amd-signal)",
          }}
        >
          <span>Conflict Detected</span>
          <span>
            {conflicts.length} conflict{conflicts.length !== 1 ? "s" : ""} found
          </span>
        </div>
      )}
    </div>
  );
}

afterEach(() => {
  cleanup();
});

const conflictArb = fc.record<Conflict>({
  id: fc.uuid(),
  type: fc.string({ minLength: 1 }),
  severity: fc.constantFrom("HIGH", "MEDIUM", "LOW"),
  documentA: fc.record({
    name: fc.string({ minLength: 1 }),
    excerpt: fc.string(),
  }),
  documentB: fc.record({
    name: fc.string({ minLength: 1 }),
    excerpt: fc.string(),
  }),
  explanation: fc.string(),
  recommendedAction: fc.string(),
});

const conflictsArb = fc.array(conflictArb, { maxLength: 6 });

describe("ConflictAlert property tests", () => {
  // Feature: greenlens-ui-redesign, Property 4: ConflictAlert renders iff conflicts exist
  it("renders the ConflictAlert iff conflicts.length > 0, with the correct border/background when rendered", () => {
    fc.assert(
      fc.property(conflictsArb, (conflicts) => {
        cleanup();
        render(<ConflictAlertMirror conflicts={conflicts} />);

        const hasConflicts = conflicts.length > 0;
        const alert = screen.queryByTestId("conflict-alert");

        if (hasConflicts) {
          expect(alert).not.toBeNull();

          const styleAttr = alert!.getAttribute("style") ?? "";
          const normalized = styleAttr.replace(/\s+/g, "");

          // 4px left border in --amd-signal
          expect(normalized).toContain("border-left:4pxsolidvar(--amd-signal)");
          // background tinted with rgba(237, 28, 36, 0.06)
          expect(normalized).toContain("background:rgba(237,28,36,0.06)");
        } else {
          expect(alert).toBeNull();
        }
      }),
      { numRuns: 100 },
    );
  });
});
