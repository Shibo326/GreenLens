import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup, screen } from "@testing-library/react";
import fc from "fast-check";
import { RiskBadge, EvidenceBox } from "../Badges";

afterEach(() => {
  cleanup();
});

const LEVEL_TO_LABEL: Record<"HIGH" | "MEDIUM" | "LOW", string> = {
  HIGH: "MISLEADING",
  MEDIUM: "VAGUE",
  LOW: "UNVERIFIED",
};

const LEVEL_TO_COLOR: Record<"HIGH" | "MEDIUM" | "LOW", string> = {
  HIGH: "var(--flag-red)",
  MEDIUM: "var(--flag-amber)",
  LOW: "var(--flag-blue)",
};

const ALL_COLORS = Object.values(LEVEL_TO_COLOR);

describe("RiskBadge property tests", () => {
  // Property: RiskBadge color is determined exclusively by risk level
  it("uses the color mapped to the risk level and no other color, for any level", () => {
    fc.assert(
      fc.property(fc.constantFrom("HIGH", "MEDIUM", "LOW"), (level) => {
        cleanup();
        render(<RiskBadge variant={level} />);
        const label = LEVEL_TO_LABEL[level];
        const badge = screen.getByText(label);
        const expected = LEVEL_TO_COLOR[level];

        expect(badge.style.color).toBe(expected);

        // Assert none of the other level colors are used.
        for (const color of ALL_COLORS) {
          if (color !== expected) {
            expect(badge.style.color).not.toBe(color);
          }
        }
      }),
      { numRuns: 100 },
    );
  });

  it("renders the correct GreenLens severity label for each level", () => {
    fc.assert(
      fc.property(fc.constantFrom("HIGH", "MEDIUM", "LOW"), (level) => {
        cleanup();
        render(<RiskBadge variant={level} />);
        const label = LEVEL_TO_LABEL[level];
        expect(screen.getByText(label)).toBeTruthy();
      }),
      { numRuns: 30 },
    );
  });
});

describe("EvidenceBox", () => {
  // Property: EvidenceBoxes in AI messages use parchment background with dark text
  it("uses parchment background with dark text by default", () => {
    fc.assert(
      fc.property(
        fc.string().filter((s) => s.trim().length > 0),
        (quote) => {
          const { container, unmount } = render(<EvidenceBox quote={quote} />);
          const el = container.firstElementChild as HTMLElement;
          if (el.style.background !== "var(--parchment)") return false;
          if (el.style.color !== "var(--lead)") return false;
          unmount();
          return true;
        },
      ),
      { numRuns: 100 },
    );
  });

  // Property: EvidenceBoxes inside ConflictAlert use paper background with dark text
  it("respects a style override of paper background with dark text", () => {
    fc.assert(
      fc.property(
        fc.string().filter((s) => s.trim().length > 0),
        (quote) => {
          const { container, unmount } = render(
            <EvidenceBox
              quote={quote}
              style={{ background: "var(--paper)", color: "var(--ink)" }}
            />,
          );
          const el = container.firstElementChild as HTMLElement;
          if (el.style.background !== "var(--paper)") return false;
          if (el.style.color !== "var(--ink)") return false;
          unmount();
          return true;
        },
      ),
      { numRuns: 100 },
    );
  });
});
