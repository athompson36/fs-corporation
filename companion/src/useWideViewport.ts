import { useEffect, useState } from "react";

export function useWideViewport(): boolean {
  const [wide, setWide] = useState(() => {
    if (typeof window === "undefined") return true;
    return window.matchMedia("(min-width: 720px)").matches;
  });
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 720px)");
    const onChange = () => setWide(mq.matches);
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return wide;
}
