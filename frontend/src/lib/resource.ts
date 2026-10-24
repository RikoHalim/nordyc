import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

export function useResource<T>(
  key: string | null,
  loader: (signal: AbortSignal) => Promise<T>,
  pollMs = 30_000,
  keepMountedOnRefresh = false,
) {
  const load = useRef(loader);
  load.current = loader;
  const [state, setState] = useState<{
    key: string | null;
    data?: T;
    error: ApiError | null;
    loading: boolean;
  }>({ key, error: null, loading: Boolean(key) });
  const [epoch, setEpoch] = useState(0);
  const reload = useCallback(() => setEpoch((n) => n + 1), []);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setState((previous) =>
      keepMountedOnRefresh &&
      previous.key === key &&
      previous.data !== undefined &&
      !document.hidden
        ? { ...previous, error: null, loading: false }
        : { key, error: null, loading: Boolean(key) },
    );
    if (key && !document.hidden) {
      load
        .current(controller.signal)
        .then((value) => {
          if (active && !document.hidden) {
            setState({ key, data: value, error: null, loading: false });
          }
        })
        .catch((error) => {
          if (active && error?.name !== "AbortError") {
            setState({
              key,
              error:
                error instanceof ApiError
                  ? error
                  : new ApiError("INVALID_RESPONSE"),
              loading: false,
            });
          }
        });
    }
    const visibility = () => {
      active = false;
      setState({ key, error: null, loading: Boolean(key) });
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
  }, [key, epoch, pollMs, reload, keepMountedOnRefresh]);
  const current = state.key === key;
  return {
    data: current ? state.data : undefined,
    error: current ? state.error : null,
    loading: Boolean(key) && (!current || state.loading),
    reload,
  };
}
