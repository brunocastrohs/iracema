import { useEffect, useRef, useState } from "react";

export default function TypewriterText({ text, animate, speed = 22, onDone, onTick }) {
  const [shown, setShown] = useState(animate ? "" : (text || ""));
  const rafRef = useRef(null);
  const lastAtRef = useRef(0);
  const iRef = useRef(0);
  const doneRef = useRef(false);

  const lastTickRef = useRef(0);
  const TICK_EVERY_MS = 60;

  useEffect(() => {
    doneRef.current = false;
    iRef.current = 0;
    lastAtRef.current = 0;
    lastTickRef.current = 0;

    setShown(animate ? "" : (text || ""));

    if (!animate) {
      onDone?.();
      return;
    }

    const full = text || "";

    const tick = (t) => {
      if (doneRef.current) return;

      if (!lastAtRef.current) lastAtRef.current = t;
      const elapsed = t - lastAtRef.current;

      const step = Math.floor(elapsed / speed);

      if (step > 0) {
        lastAtRef.current = lastAtRef.current + step * speed;

        iRef.current = Math.min(full.length, iRef.current + step);
        setShown(full.slice(0, iRef.current));

        if (onTick) {
          if (!lastTickRef.current) lastTickRef.current = t;
          if (t - lastTickRef.current >= TICK_EVERY_MS) {
            lastTickRef.current = t;
            onTick();
          }
        }

        if (iRef.current >= full.length) {
          doneRef.current = true;
          onDone?.();
          return;
        }
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => rafRef.current && cancelAnimationFrame(rafRef.current);
  }, [text, animate, speed, onDone, onTick]);

  return <span>{shown}</span>;
}
