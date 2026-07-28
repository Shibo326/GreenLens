import { describe, it, expect, afterEach, vi } from "vitest";
import { render, cleanup, screen } from "@testing-library/react";
import fc from "fast-check";
import { DocumentStack } from "../DocumentStack";

// Property tests care about card counts, not animation timing. framer-motion's
// AnimatePresence keeps exiting elements mounted while their exit animation
// plays, which never resolves deterministically in jsdom. Stubbing it to
// render/unmount children synchronously keeps the tests focused on the
// component's structural behavior (Requirements 5.1, 5.6) rather than motion.
vi.mock("framer-motion", () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  motion: {
    div: ({
      children,
      initial: _initial,
      animate: _animate,
      exit: _exit,
      transition: _transition,
      ...rest
    }: Record<string, unknown> & { children?: React.ReactNode }) => (
      <div {...rest}>{children}</div>
    ),
  },
}));

afterEach(() => {
  cleanup();
});

interface FileSpec {
  name: string;
  size: number;
  type: "application/pdf" | "image/png" | "image/jpeg";
}

const fileSpecArb = fc.record({
  name: fc.string({ minLength: 1 }),
  size: fc.nat(),
  type: fc.constantFrom(
    "application/pdf" as const,
    "image/png" as const,
    "image/jpeg" as const,
  ),
});

function toFiles(specs: FileSpec[]): File[] {
  return specs.map(
    (spec) => new File([""], spec.name, { type: spec.type }),
  );
}

describe("DocumentStack property tests", () => {
  // Feature: greenlens-ui-redesign, Property 1: DocumentStack card count matches file count
  it("renders exactly one PaperCard per file for any non-empty file array", () => {
    fc.assert(
      fc.property(
        fc.array(fileSpecArb, { minLength: 1, maxLength: 10 }),
        (specs) => {
          cleanup();
          const files = toFiles(specs);
          render(<DocumentStack files={files} onRemove={() => {}} />);
          const cards = screen.getAllByTestId("paper-card");
          expect(cards.length).toBe(files.length);
        },
      ),
    );
  });

  // Feature: greenlens-ui-redesign, Property 3: DocumentStack removal reduces count by one
  it("reduces rendered card count by exactly one after removing any valid index", () => {
    fc.assert(
      fc.property(
        fc
          .array(fileSpecArb, { minLength: 1, maxLength: 10 })
          .chain((specs) =>
            fc.tuple(
              fc.constant(specs),
              fc.integer({ min: 0, max: specs.length - 1 }),
            ),
          ),
        ([specs, removeIndex]) => {
          cleanup();
          const files = toFiles(specs);
          const remainingFiles = files.filter((_, i) => i !== removeIndex);

          // Simulate the parent component's behavior of removing an item
          // from the files array and re-rendering DocumentStack with the
          // updated array, mirroring how onRemove is expected to be wired up.
          const { rerender } = render(
            <DocumentStack files={files} onRemove={() => {}} />,
          );
          expect(screen.getAllByTestId("paper-card").length).toBe(
            files.length,
          );

          rerender(
            <DocumentStack files={remainingFiles} onRemove={() => {}} />,
          );

          const cardsAfterRemoval = screen.queryAllByTestId("paper-card");
          expect(cardsAfterRemoval.length).toBe(files.length - 1);
        },
      ),
    );
  });
});
