import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../src/api/client";
import { useResource } from "../src/lib/resource";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

function View({
  resourceKey = "programme-one",
  loader,
  pollMs = 0,
}: {
  resourceKey?: string;
  loader: (signal: AbortSignal) => Promise<string>;
  pollMs?: number;
}) {
  const resource = useResource(resourceKey, loader, pollMs, true);
  if (resource.loading) return <p>Loading programme</p>;
  if (resource.error) return <p role="alert">{resource.error.message}</p>;
  return (
    <section>
      <p>{resource.data}</p>
      <input type="file" aria-label="Curriculum PDF" />
    </section>
  );
}

beforeEach(() => {
  vi.spyOn(document, "hidden", "get").mockReturnValue(false);
});
afterEach(() => vi.useRealTimers());

describe("resource background refresh and privacy", () => {
  it("preserves the mounted file input and selected PDF across a focus refresh", async () => {
    const initial = deferred<string>();
    const refresh = deferred<string>();
    const loader = vi
      .fn()
      .mockReturnValueOnce(initial.promise)
      .mockReturnValueOnce(refresh.promise);
    render(<View loader={loader} />);
    await act(async () => initial.resolve("Stored programme"));
    const input = screen.getByLabelText("Curriculum PDF") as HTMLInputElement;
    const file = new File(["%PDF-1.7"], "synthetic.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(input, { target: { files: [file] } });
    act(() => window.dispatchEvent(new Event("focus")));
    expect(screen.getByLabelText("Curriculum PDF")).toBe(input);
    expect(input.files?.[0]).toBe(file);
    expect(screen.getByText("Stored programme")).toBeVisible();
    expect(screen.queryByText("Loading programme")).not.toBeInTheDocument();
    await act(async () => refresh.resolve("Refreshed programme"));
    expect(screen.getByText("Refreshed programme")).toBeVisible();
    expect(screen.getByLabelText("Curriculum PDF")).toBe(input);
    expect(input.files?.[0]).toBe(file);
  });

  it("retains same-key data while a polling refresh is pending", async () => {
    vi.useFakeTimers();
    const refresh = deferred<string>();
    const loader = vi
      .fn()
      .mockResolvedValueOnce("Stored programme")
      .mockReturnValueOnce(refresh.promise);
    render(<View loader={loader} pollMs={3000} />);
    await act(async () => {});
    const input = screen.getByLabelText("Curriculum PDF");
    await act(async () => vi.advanceTimersByTime(3000));
    expect(loader).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Stored programme")).toBeVisible();
    expect(screen.getByLabelText("Curriculum PDF")).toBe(input);
    expect(screen.queryByText("Loading programme")).not.toBeInTheDocument();
  });

  it("hides old programme data immediately when the resource key changes", async () => {
    const next = deferred<string>();
    const loader = vi
      .fn()
      .mockResolvedValueOnce("Private first programme")
      .mockReturnValueOnce(next.promise);
    const view = render(<View loader={loader} />);
    await act(async () => {});
    view.rerender(<View loader={loader} resourceKey="programme-two" />);
    expect(
      screen.queryByText("Private first programme"),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Loading programme")).toBeVisible();
    await act(async () => next.resolve("Second programme"));
    expect(screen.getByText("Second programme")).toBeVisible();
  });

  it("clears displayed data if background permission revalidation fails", async () => {
    const refresh = deferred<string>();
    const loader = vi
      .fn()
      .mockResolvedValueOnce("Private programme")
      .mockReturnValueOnce(refresh.promise);
    render(<View loader={loader} />);
    await act(async () => {});
    act(() => window.dispatchEvent(new Event("focus")));
    await act(async () => refresh.reject(new ApiError("FORBIDDEN", 403)));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "does not allow this action",
    );
    expect(screen.queryByText("Private programme")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Curriculum PDF")).not.toBeInTheDocument();
  });

  it("clears private data and aborts while hidden, then requires a new visible read", async () => {
    let hidden = false;
    vi.spyOn(document, "hidden", "get").mockImplementation(() => hidden);
    const refresh = deferred<string>();
    const pending = deferred<string>();
    const loader = vi
      .fn()
      .mockResolvedValueOnce("Private programme")
      .mockReturnValueOnce(pending.promise)
      .mockReturnValueOnce(refresh.promise);
    render(<View loader={loader} />);
    await act(async () => {});
    act(() => window.dispatchEvent(new Event("focus")));
    const signal = loader.mock.calls[1][0] as AbortSignal;
    hidden = true;
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(signal.aborted).toBe(true);
    expect(screen.queryByText("Private programme")).not.toBeInTheDocument();
    await act(async () => pending.resolve("Late hidden response"));
    expect(screen.queryByText("Late hidden response")).not.toBeInTheDocument();
    hidden = false;
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(loader).toHaveBeenCalledTimes(3);
    expect(screen.getByText("Loading programme")).toBeVisible();
    await act(async () => refresh.resolve("Revalidated programme"));
    expect(screen.getByText("Revalidated programme")).toBeVisible();
  });
});
