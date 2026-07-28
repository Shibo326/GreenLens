import { useEffect } from "react";
import confetti from "canvas-confetti";

/**
 * Green leaf-themed confetti burst. Renders once on mount.
 * Use on the Dashboard page to celebrate analysis completion.
 */
export function ConfettiEffect() {
  useEffect(() => {
    // First burst — green leaves from center
    confetti({
      particleCount: 80,
      spread: 100,
      origin: { y: 0.4 },
      colors: ["#3DDC84", "#6ee7a8", "#22c55e", "#16a34a"],
      shapes: ["circle"],
      gravity: 0.8,
      ticks: 120,
      scalar: 1.2,
    });

    // Second burst — wider spray after short delay
    const timer = setTimeout(() => {
      confetti({
        particleCount: 40,
        spread: 140,
        origin: { y: 0.35, x: 0.3 },
        colors: ["#3DDC84", "#F0A937", "#5FA8D3"],
        shapes: ["circle"],
        gravity: 1,
        ticks: 100,
        scalar: 0.9,
      });
      confetti({
        particleCount: 40,
        spread: 140,
        origin: { y: 0.35, x: 0.7 },
        colors: ["#3DDC84", "#F0A937", "#5FA8D3"],
        shapes: ["circle"],
        gravity: 1,
        ticks: 100,
        scalar: 0.9,
      });
    }, 200);

    return () => clearTimeout(timer);
  }, []);

  // No DOM element needed — canvas-confetti renders to its own canvas
  return null;
}
