import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

export function useResource<T>(
  key: string | null,
  loader: (signal: AbortSignal) => Promise<T>,
  pollMs = 30_000,
) {
  const load = useRef(loader);
  load.current = loader;
  const [data, setData] = useState<T>();
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(Boolean(key));
  const [epoch, setEpoch] = useState(0);
  const [resolved, setResolved] = useState<{
    key: string | null;
    epoch: number;
  } | null>(null);
  const reload = useCallback(() => setEpoch((n) => n + 1), []);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setData(undefined);
    setError(null);
    setLoading(Boolean(key));
    if (key && !document.hidden) {
      load
        .current(controller.signal)
        .then((value) => {
          if (active && !document.hidden) {
            setResolved({ key, epoch });
            setData(value);
            setLoading(false);
          }
        })
        .catch((error) => {
          if (active && error?.name !== "AbortError") {
            setResolved({ key, epoch });
            setData(undefined);
            setError(
              error instanceof ApiError
                ? error
                : new ApiError("INVALID_RESPONSE"),
            );
            setLoading(false);
          }
        });
    }
    const visibility = () => {
      active = false;
      setData(undefined);
      controller.abort();
      if (!document.hidden) reload();
    };
    const focus = () => reload();
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("focus", focus);
    const timer =
      key && pollMs > 0
        ? setInterval(() => {
            if (!document.hidden) reload();
          }, pollMs)
        : undefined;
    return () => {
      active = false;
      controller.abort();
      clearInterval(timer);
      document.removeEventListener("visibilitychange", visibility);
      window.removeEventListener("focus", focus);
    };
  }, [key, epoch, pollMs, reload]);
  const current = resolved?.key === key && resolved?.epoch === epoch;
  return {
    data: current ? data : undefined,
    error: current ? error : null,
    loading: Boolean(key) && (!current || loading),
    reload,
  };
}
