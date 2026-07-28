import { describe, it, vi, beforeEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import fc from "fast-check";
import type { UploadedDocument } from "../../../lib/types";

// Mock the store hooks used by Chat.tsx so we can provide a non-null session
// without needing the real Context+Reducer provider tree.
vi.mock("../../../lib/store", () => ({
  useAppState: () => ({
    sessionId: "test-session-id",
    documents: [
      {
        id: "doc-1",
        filename: "contract.pdf",
        fileType: "pdf",
        fileSize: 1024,
        uploadedAt: new Date().toISOString(),
        processingStatus: "complete",
      } as UploadedDocument,
    ],
    analysis: null,
    isLoading: false,
    error: null,
    isDemo: false,
  }),
  useAppDispatch: () => vi.fn(),
}));

// Mock the API layer so Chat.tsx's effects (getSuggestedQuestions) and the
// send action (streamChatMessage) don't perform real network calls.
vi.mock("../../../lib/api", () => ({
  getSuggestedQuestions: vi.fn().mockResolvedValue([]),
  streamChatMessage: vi.fn().mockResolvedValue(undefined),
  exportReport: vi.fn().mockResolvedValue(new Blob()),
  sendVisionMessage: vi.fn().mockResolvedValue(undefined),
}));

import Chat from "../Chat";

// jsdom does not implement scrollIntoView; Chat.tsx calls it in a useEffect.
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

function renderChat() {
  return render(
    <MemoryRouter>
      <Chat />
    </MemoryRouter>,
  );
}

describe("Chat send button", () => {
  beforeEach(() => {
    cleanup();
  });

  // Feature: greenlens-ui-redesign, Property 8: Send button state is determined by input value trimmed emptiness
  it("enables with volt background iff input trims to non-empty, disables with graphite/opacity 0.5 otherwise (Property 8)", () => {
    fc.assert(
      fc.property(fc.string(), (value) => {
        const { getByPlaceholderText, unmount } = renderChat();
        const input = getByPlaceholderText(
          "Ask about sustainability claims…",
        ) as HTMLInputElement;
        // The send button is the last button inside the input's parent container
        const buttons = input.parentElement?.querySelectorAll("button");
        const sendButton = buttons ? buttons[buttons.length - 1] as HTMLButtonElement : null;
        if (!sendButton) { unmount(); return false; }

        fireEvent.change(input, { target: { value } });

        const isNonEmpty = value.trim().length > 0;
        const bg = sendButton.style.background;
        const opacity = sendButton.style.opacity;
        const disabled = sendButton.disabled;

        let ok: boolean;
        if (isNonEmpty) {
          ok = bg === "var(--volt)" && opacity === "1" && disabled === false;
        } else {
          ok =
            bg === "var(--graphite)" && opacity === "0.5" && disabled === true;
        }

        unmount();
        return ok;
      }),
      { numRuns: 50 },
    );
  }, 15000);
});
