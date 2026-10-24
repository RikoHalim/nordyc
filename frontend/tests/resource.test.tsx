import {
  act,
  render,
  renderHook,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../src/api/client";
import { useResource } from "../src/lib/resource";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

beforeEach(() => {
  vi.spyOn(document, "hidden", "get").mockReturnValue(false);
});
afterEach(() => {
  vi.useRealTimers();
});

describe("source revalidation and programme boundaries", () => {
  it("removes old evidence while reloading, and keeps it withheld after a failed revalidation", async () => {
    const reload = deferred<string>();
    const load = vi
      .fn()
      .mockResolvedValueOnce("PRIVATE-PERMITTED-EVIDENCE")
      .mockImplementationOnce(() => reload.promise);
    const { result } = renderHook(() =>
      useResource("institution-A:programme-A:evidence", load, 0),
    );
    await waitFor(() =>
      expect(result.current.data).toBe("PRIVATE-PERMITTED-EVIDENCE"),
    );
    act(() => result.current.reload());
    expect(result.current.data).toBeUndefined();
    expect(result.current.loading).toBe(true);
    await act(async () => reload.reject(new ApiError("FORBIDDEN", 403)));
    expect(result.current.data).toBeUndefined();
    expect(result.current.error).toMatchObject({ code: "FORBIDDEN" });
    expect(result.current.loading).toBe(false);
  });

  it("never returns the previous institution data during any render of a new programme", async () => {
    const next = deferred<string>();
    const seen: Array<{ key: string; data: string | undefined }> = [];
    function Probe({ identity }: { identity: string }) {
      const state = useResource(
        identity,
        () => (identity === "A" ? Promise.resolve("PRIVATE-A") : next.promise),
        0,
      );
      seen.push({ key: identity, data: state.data });
      return <div>{state.data ?? "No current evidence"}</div>;
    }
    const view = render(<Probe identity="A" />);
    await screen.findByText("PRIVATE-A");
    view.rerender(<Probe identity="B" />);
    expect(
      seen.some((state) => state.key === "B" && state.data === "PRIVATE-A"),
    ).toBe(false);
    expect(screen.queryByText("PRIVATE-A")).not.toBeInTheDocument();
    await act(async () => next.resolve("PERMITTED-B"));
    expect(screen.getByText("PERMITTED-B")).toBeInTheDocument();
  });

  it("fences late responses after programme change even if a loader ignores cancellation", async () => {
    const first = deferred<string>(),
      second = deferred<string>();
    const signals: AbortSignal[] = [];
    const { result, rerender } = renderHook(
      ({ key }) =>
        useResource(
          key,
          (signal) => {
            signals.push(signal);
            return key === "A" ? first.promise : second.promise;
          },
          0,
        ),
      { initialProps: { key: "A" } },
    );
    rerender({ key: "B" });
    expect(signals[0].aborted).toBe(true);
    await act(async () => first.resolve("PRIVATE-STALE-A"));
    expect(result.current.data).toBeUndefined();
    await act(async () => second.resolve("PERMITTED-B"));
    expect(result.current.data).toBe("PERMITTED-B");
  });

  it("erases current data on visibility loss and fences the outstanding response", async () => {
    const pending = deferred<string>();
    const load = vi
      .fn()
      .mockResolvedValueOnce("PRIVATE-EVIDENCE")
      .mockImplementationOnce(() => pending.promise);
    const { result } = renderHook(() => useResource("A:evidence", load, 0));
    await waitFor(() => expect(result.current.data).toBe("PRIVATE-EVIDENCE"));
    act(() => result.current.reload());
    vi.spyOn(document, "hidden", "get").mockReturnValue(true);
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(result.current.data).toBeUndefined();
    await act(async () => pending.resolve("PRIVATE-LATE-HIDDEN-EVIDENCE"));
    expect(result.current.data).toBeUndefined();
    vi.spyOn(document, "hidden", "get").mockReturnValue(false);
    load.mockResolvedValueOnce("REVALIDATED-EVIDENCE");
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    await waitFor(() =>
      expect(result.current.data).toBe("REVALIDATED-EVIDENCE"),
    );
  });

  it("aborts on unmount and never publishes a late result or invokes a second loader", async () => {
    const pending = deferred<string>();
    let signal!: AbortSignal;
    const load = vi.fn((current: AbortSignal) => {
      signal = current;
      return pending.promise;
    });
    const { result, unmount } = renderHook(() => useResource("A", load, 0));
    unmount();
    expect(signal.aborted).toBe(true);
    await act(async () => pending.resolve("PRIVATE-AFTER-UNMOUNT"));
    expect(result.current.data).toBeUndefined();
    expect(load).toHaveBeenCalledOnce();
  });

  it("does not load a null workspace and clears the previous scope", async () => {
    const load = vi.fn().mockResolvedValue("PRIVATE-A");
    const { result, rerender } = renderHook(
      ({ key }) => useResource(key, load, 0),
      { initialProps: { key: "A" as string | null } },
    );
    await waitFor(() => expect(result.current.data).toBe("PRIVATE-A"));
    rerender({ key: null });
    expect(result.current.data).toBeUndefined();
    expect(result.current.loading).toBe(false);
    expect(load).toHaveBeenCalledOnce();
  });

  it("clears old evidence when focus revalidation fails", async () => {
    const load = vi.fn().mockResolvedValue("ELIGIBLE-EVIDENCE");
    const { result } = renderHook(() => useResource("A", load, 0));
    await waitFor(() => expect(result.current.data).toBe("ELIGIBLE-EVIDENCE"));
    load.mockRejectedValueOnce(new ApiError("DATABASE_UNAVAILABLE", 503));
    act(() => window.dispatchEvent(new Event("focus")));
    await waitFor(() =>
      expect(result.current.error?.code).toBe("DATABASE_UNAVAILABLE"),
    );
    expect(result.current.data).toBeUndefined();
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("polls visible reads only and stops all work after unmount", async () => {
    vi.useFakeTimers();
    const load = vi.fn().mockResolvedValue("CURRENT-EVIDENCE");
    const view = renderHook(() => useResource("A:read-only", load, 1000));
    await act(async () => {
      await Promise.resolve();
    });
    expect(load).toHaveBeenCalledOnce();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(load).toHaveBeenCalledTimes(2);
    vi.spyOn(document, "hidden", "get").mockReturnValue(true);
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(view.result.current.data).toBeUndefined();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(load).toHaveBeenCalledTimes(2);
    vi.spyOn(document, "hidden", "get").mockReturnValue(false);
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(load).toHaveBeenCalledTimes(3);
    view.unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(load).toHaveBeenCalledTimes(3);
  });
});
