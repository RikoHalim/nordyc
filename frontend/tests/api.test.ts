import { afterEach, describe, expect, it, vi } from "vitest";
import courses from "../../examples/api/courses.synthetic.json";
import { ApiClient, ApiError, validateResponse } from "../src/api/client";

const credential = "SYNTHETIC-FRONTEND-CREDENTIAL-NOT-LIVE";
const privateText = "PRIVATE-SERVER-BODY-SENTINEL";
const path = "/api/v1/programmes/753afd59-9415-5a85-b2f5-c1bbc7bdde5b/courses";
const json = (value: unknown, status = 200, headers: HeadersInit = {}) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
const envelope = (code: string) => ({
  error: { code, message: privateText, details: [] },
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("actual OpenAPI response validation", () => {
  it("accepts the normalized real synthetic course-page response and preserves unknowns", () => {
    const accepted = validateResponse<typeof courses.response>(
      courses.response,
      "CoursePage",
    );
    expect(accepted).toEqual(courses.response);
    expect(accepted.items.some((course) => course.semester === null)).toBe(
      true,
    );
  });

  it.each(["id", "course_type", "total", "missing"])(
    "rejects invalid %s before rendering",
    (field) => {
      const value = structuredClone(courses.response);
      if (field === "id") value.items[0].id = "invalid-uuid";
      if (field === "course_type")
        value.items[0].course_type = "invented-course-category";
      if (field === "total")
        (value as unknown as { total: unknown }).total = "6";
      if (field === "missing") delete (value as Partial<typeof value>).items;
      expect(() => validateResponse(value, "CoursePage")).toThrowError(
        ApiError,
      );
    },
  );

  it("does not accept an arbitrary withheld object as a course-page success", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          json({ source_text_withheld: true, secret: privateText }),
        ),
    );
    const error = await new ApiClient(credential)
      .get(path, "CoursePage")
      .catch((error) => error);
    expect(error).toMatchObject({ code: "INVALID_RESPONSE" });
    expect(String(error)).not.toContain(privateText);
  });
});

describe("safe errors and explicit authorization", () => {
  it.each([
    () =>
      new Response(`<html>${privateText}</html>`, {
        status: 502,
        headers: { "Content-Type": "text/html" },
      }),
    () =>
      new Response(`{"private":"${privateText}"`, {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
  ])("never exposes HTML or malformed JSON server bodies", async (response) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response()));
    const error = await new ApiClient(credential)
      .get(path, "CoursePage")
      .catch((error) => error);
    expect(error).toBeInstanceOf(ApiError);
    if (!(error instanceof ApiError))
      throw new Error("Expected a safe client error");
    expect(error.code).toBe("INVALID_RESPONSE");
    expect(JSON.stringify(error) + String(error)).not.toContain(privateText);
  });

  it.each([
    () => json(envelope("NOT_AUTHORIZED"), 401),
    () =>
      new Response(`<html>${privateText}</html>`, {
        status: 401,
        headers: { "Content-Type": "text/html" },
      }),
    () =>
      new Response("{", {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
  ])(
    "revokes workspace access for every 401 response shape",
    async (response) => {
      const unauthorised = vi.fn();
      const fetch = vi.fn().mockResolvedValue(response());
      vi.stubGlobal("fetch", fetch);
      await expect(
        new ApiClient(credential, unauthorised).get(path, "CoursePage"),
      ).rejects.toBeInstanceOf(ApiError);
      expect(unauthorised).toHaveBeenCalledOnce();
      expect(fetch).toHaveBeenCalledOnce();
    },
  );

  it("does not escalate or retry a forbidden grant", async () => {
    const unauthorised = vi.fn();
    const fetch = vi.fn().mockResolvedValue(json(envelope("FORBIDDEN"), 403));
    vi.stubGlobal("fetch", fetch);
    const error = await new ApiClient(credential, unauthorised)
      .post(path, "CoursePage", {})
      .catch((error) => error);
    expect(error).toMatchObject({ code: "FORBIDDEN", status: 403 });
    if (!(error instanceof ApiError))
      throw new Error("Expected a safe client error");
    expect(error.message).not.toContain(privateText);
    expect(fetch).toHaveBeenCalledOnce();
    expect(unauthorised).not.toHaveBeenCalled();
  });

  it("never publishes arbitrary error codes or request headers as private text", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          json(envelope(privateText), 500, { "X-Request-ID": privateText }),
        ),
    );
    const error = await new ApiClient(credential)
      .get(path, "CoursePage")
      .catch((error) => error);
    expect(error).toMatchObject({ code: "REQUEST_FAILED", status: 500 });
    expect(JSON.stringify(error) + String(error)).not.toContain(privateText);
  });

  it("preserves a valid opaque request ID for an ordinary documented error", async () => {
    const requestId = "9a6ff274-5dd7-47fc-8250-141e51f5a24d";
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          json(envelope("CONFLICT"), 409, { "X-Request-ID": requestId }),
        ),
    );
    await expect(
      new ApiClient(credential).get(path, "CoursePage"),
    ).rejects.toMatchObject({ code: "CONFLICT", requestId });
  });
});

describe("request boundaries and bounded transport", () => {
  it("allows encoded official source URLs and labels as query data without changing origin", async () => {
    const fetch = vi
      .fn()
      .mockImplementation(() => Promise.resolve(json(courses.response)));
    vi.stubGlobal("fetch", fetch);
    const query = new URLSearchParams({
      source_url: "https://curriculum.example.invalid/programme",
      label: "Fictional degree",
    });
    const uploadPath = `/api/v1/programmes/753afd59-9415-5a85-b2f5-c1bbc7bdde5b/curriculum-pdf?${query}`;
    const file = new File(["%PDF-1.7\nsynthetic test bytes"], "fictional.pdf", {
      type: "application/pdf",
    });
    await new ApiClient(credential).upload(uploadPath, "CoursePage", file);
    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch.mock.calls[0][0]).toBe(uploadPath);
    expect(new URL(fetch.mock.calls[0][0], window.location.origin).origin).toBe(
      window.location.origin,
    );
  });

  it.each([
    "https://outside.invalid/api/v1/programmes",
    "//outside.invalid/api/v1/programmes",
    "/api/v1/../../private",
    "/api/v1/%2e%2e/%2e%2e/private",
    "/api/v1/programmes\\private",
    "/api/v1/programmes#fragment",
    "/api/v1/programmes\n?private=value",
  ])(
    "rejects unsafe credential destination %j without fetching",
    async (unsafe) => {
      const fetch = vi.fn().mockResolvedValue(json(courses.response));
      vi.stubGlobal("fetch", fetch);
      await expect(
        new ApiClient(credential).get(unsafe, "CoursePage"),
      ).rejects.toBeInstanceOf(ApiError);
      expect(fetch).not.toHaveBeenCalled();
    },
  );

  it("sends the credential only in headers and never stores it in browser persistence", async () => {
    const fetch = vi.fn().mockResolvedValue(json(courses.response));
    const storage = vi.spyOn(Storage.prototype, "setItem");
    vi.stubGlobal("fetch", fetch);
    const body = {
      revision_id: "753afd59-9415-5a85-b2f5-c1bbc7bdde5b",
      mode: "offline",
      research: false,
      idempotency_key: "synthetic-deliberate-test",
    };
    await new ApiClient(credential).post(path, "CoursePage", body);
    const request = fetch.mock.calls[0][1] as RequestInit;
    expect(request.headers).toMatchObject({
      Authorization: `Bearer ${credential}`,
      "Content-Type": "application/json",
    });
    expect(request.body).toBe(JSON.stringify(body));
    expect(String(request.body)).not.toContain(credential);
    expect(request).toMatchObject({
      credentials: "same-origin",
      cache: "no-store",
      redirect: "error",
      mode: "same-origin",
    });
    expect(storage).not.toHaveBeenCalled();
  });

  it("retains same-origin preview access without accepting absolute destinations or following sign-in redirects", async () => {
    const fetch = vi.fn().mockResolvedValue(json(courses.response));
    vi.stubGlobal("fetch", fetch);
    const api = new ApiClient(credential);
    await api.get(path, "CoursePage");
    const request = fetch.mock.calls[0][1] as RequestInit;
    expect(request).toMatchObject({
      credentials: "same-origin",
      redirect: "error",
      mode: "same-origin",
      headers: { Authorization: `Bearer ${credential}` },
    });
    for (const destination of [
      `${window.location.origin}${path}`,
      "https://replit.com/__replshield",
    ])
      await expect(api.get(destination, "CoursePage")).rejects.toMatchObject({
        code: "INVALID_RESPONSE",
      });
    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch.mock.calls[0][0]).toBe(path);
  });

  it("uploads PDF bytes directly instead of wrapping them in JSON", async () => {
    const fetch = vi.fn().mockResolvedValue(json(courses.response));
    vi.stubGlobal("fetch", fetch);
    const file = new File(
      ["%PDF-1.7\nsynthetic test bytes"],
      "fictional-course.pdf",
      { type: "application/pdf" },
    );
    await new ApiClient(credential).upload(
      "/api/v1/programmes/753afd59-9415-5a85-b2f5-c1bbc7bdde5b/curriculum-pdf",
      "CoursePage",
      file,
    );
    const request = fetch.mock.calls[0][1] as RequestInit;
    expect(request.body).toBe(file);
    expect(request.headers).toMatchObject({
      "Content-Type": "application/pdf",
    });
  });

  it("cancels oversized declared bodies before reading them", async () => {
    const canceled = vi.fn();
    const body = new ReadableStream<Uint8Array>({ cancel: canceled });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(body, {
          headers: {
            "Content-Type": "application/json",
            "Content-Length": String(4 * 1024 * 1024 + 1),
          },
        }),
      ),
    );
    await expect(
      new ApiClient(credential).get(path, "CoursePage"),
    ).rejects.toMatchObject({ code: "RESPONSE_TOO_LARGE" });
    expect(canceled).toHaveBeenCalledOnce();
  });

  it("bounds a chunked body even without a declared size", async () => {
    const canceled = vi.fn();
    const body = new ReadableStream<Uint8Array>({
      start: (controller) =>
        controller.enqueue(new Uint8Array(4 * 1024 * 1024 + 1)),
      cancel: canceled,
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(body, {
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    await expect(
      new ApiClient(credential).get(path, "CoursePage"),
    ).rejects.toMatchObject({ code: "RESPONSE_TOO_LARGE" });
    expect(canceled).toHaveBeenCalledOnce();
  });

  it("reports an unknown outcome on timeout and never resubmits the paid-capable POST", async () => {
    vi.useFakeTimers();
    const fetch = vi.fn(
      (_input: string, init: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init.signal?.addEventListener(
            "abort",
            () => reject(new DOMException("Aborted", "AbortError")),
            { once: true },
          );
        }),
    );
    vi.stubGlobal("fetch", fetch);
    const pending = new ApiClient(credential).post(path, "CoursePage", {
      mode: "offline",
    });
    const rejected = expect(pending).rejects.toMatchObject({ code: "TIMEOUT" });
    await vi.advanceTimersByTimeAsync(30_001);
    await rejected;
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("keeps explicit cancellation distinct from timeout and never retries", async () => {
    const controller = new AbortController();
    const fetch = vi.fn(
      (_input: string, init: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init.signal?.addEventListener(
            "abort",
            () => reject(new DOMException("Aborted", "AbortError")),
            { once: true },
          );
        }),
    );
    vi.stubGlobal("fetch", fetch);
    const pending = new ApiClient(credential).post(
      path,
      "CoursePage",
      { mode: "offline" },
      controller.signal,
    );
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    expect(fetch).toHaveBeenCalledOnce();
  });
});

describe("complete bounded inventory reads", () => {
  it("rejects a valid withheld evidence page rather than treating it as an empty success", async () => {
    const fetch = vi.fn().mockResolvedValue(
      json({
        items: [],
        total: 0,
        limit: 100,
        offset: 0,
        status: "SUCCEEDED",
        error: null,
        needs_evidence_revalidation: true,
        evidence_access_limitations: ["Source permission withdrawn"],
      }),
    );
    vi.stubGlobal("fetch", fetch);
    await expect(
      new ApiClient(credential).all(
        "/api/v1/career-analyses/753afd59-9415-5a85-b2f5-c1bbc7bdde5b/evidence",
        "EvidencePage",
      ),
    ).rejects.toMatchObject({ code: "EVIDENCE_WITHHELD", status: 409 });
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("retrieves every course over multiple backend pages and retains the revision", async () => {
    const prototype = courses.response.items[0];
    const items = Array.from({ length: 106 }, (_, index) => ({
      ...prototype,
      id: `00000000-0000-4000-8000-${String(index).padStart(12, "0")}`,
    }));
    const fetch = vi.fn((input: string) => {
      const url = new URL(input, "http://localhost");
      const offset = Number(url.searchParams.get("offset"));
      return Promise.resolve(
        json({
          ...courses.response,
          items: items.slice(offset, offset + 100),
          limit: 100,
          offset,
          total: items.length,
        }),
      );
    });
    vi.stubGlobal("fetch", fetch);
    const result = await new ApiClient(credential).all<typeof prototype>(
      path,
      "CoursePage",
    );
    expect(result.map((row) => row.id)).toEqual(items.map((row) => row.id));
    expect(
      result.every(
        (row) => row.programme_revision_id === prototype.programme_revision_id,
      ),
    ).toBe(true);
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("rejects an empty intermediate page instead of presenting incomplete inventory", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(json({ ...courses.response, items: [], total: 5 }));
    vi.stubGlobal("fetch", fetch);
    await expect(
      new ApiClient(credential).all(path, "CoursePage"),
    ).rejects.toMatchObject({ code: "INVALID_RESPONSE" });
    expect(fetch).toHaveBeenCalledOnce();
  });
});
