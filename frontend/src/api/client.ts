import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";
import { components } from "./openapi.json";

const ajv = new Ajv2020({
  strict: false,
  allErrors: false,
  validateFormats: true,
});
addFormats(ajv);
ajv.addSchema({ $id: "urn:shiftos:api", components }, "urn:shiftos:api");
const MAX_BYTES = 4 * 1024 * 1024;

export class ApiError extends Error {
  constructor(
    public code: string,
    public status = 0,
    public requestId: string | null = null,
  ) {
    super(
      messages[code] ||
        "The request could not be completed. Check your access and try again.",
    );
    this.name = "ApiError";
  }
}

const messages: Record<string, string> = {
  NOT_AUTHORIZED:
    "Your workspace credential is missing, invalid or expired. Reconnect to continue.",
  FORBIDDEN: "Your operator grant does not allow this action.",
  NOT_FOUND: "This record is unavailable in your authorised workspace.",
  CONFLICT:
    "The record or its evidence has changed. Reload it before making a new decision.",
  VALIDATION_ERROR:
    "Check the input format and required fields. The server did not accept it.",
  PAYLOAD_TOO_LARGE: "This file or request exceeds the supported size limit.",
  DATABASE_UNAVAILABLE:
    "The backend database is unavailable. No successful result is being shown.",
  TIMEOUT:
    "The request timed out. Its outcome is unknown; check job history before submitting again.",
  NETWORK: "The backend could not be reached. Check that the API is running.",
  INVALID_RESPONSE:
    "The backend returned an unexpected response. No academic result is being displayed.",
  RESPONSE_TOO_LARGE:
    "The response is too large. Use a smaller page or ask the workspace operator.",
  EVIDENCE_WITHHELD:
    "Evidence access has changed. Restricted source text is withheld until revalidated.",
};

export function validateResponse<T>(value: unknown, schema: string): T {
  const validate = ajv.getSchema(
    `urn:shiftos:api#/components/schemas/${schema}`,
  );
  if (!validate || !validate(value)) throw new ApiError("INVALID_RESPONSE");
  return value as T;
}

async function boundedJson(response: Response): Promise<unknown> {
  if (!response.headers.get("content-type")?.includes("application/json")) {
    await response.body?.cancel();
    throw new ApiError("INVALID_RESPONSE", response.status);
  }
  if (Number(response.headers.get("content-length")) > MAX_BYTES) {
    await response.body?.cancel();
    throw new ApiError("RESPONSE_TOO_LARGE");
  }
  const reader = response.body?.getReader();
  if (!reader) throw new ApiError("INVALID_RESPONSE");
  const decoder = new TextDecoder();
  let text = "",
    size = 0;
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_BYTES) {
        await reader.cancel();
        throw new ApiError("RESPONSE_TOO_LARGE");
      }
      text += decoder.decode(value, { stream: true });
    }
    return JSON.parse(text + decoder.decode());
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError("INVALID_RESPONSE");
  } finally {
    reader.releaseLock();
  }
}

export class ApiClient {
  #credential: string;
  constructor(
    credential: string,
    private onUnauthorised?: () => void,
  ) {
    this.#credential = credential;
  }

  async request<T>(
    path: string,
    schema: string,
    options: {
      method?: "GET" | "POST";
      body?: unknown;
      signal?: AbortSignal;
      pdf?: File;
    } = {},
  ): Promise<T> {
    try {
      const decoded = decodeURIComponent(path.split("?")[0]);
      const url = new URL(path, window.location.origin);
      if (
        !path.startsWith("/api/v1/") ||
        !url.pathname.startsWith("/api/v1/") ||
        url.origin !== window.location.origin ||
        /[\\#\s\u0000-\u001f]/.test(decoded) ||
        /[\s\u0000-\u001f]/.test(path) ||
        decoded.split("/").some((part) => part === "." || part === "..") ||
        decoded.includes("://")
      )
        throw new Error();
    } catch {
      throw new ApiError("INVALID_RESPONSE");
    }
    const controller = new AbortController();
    const onAbort = () => controller.abort();
    options.signal?.addEventListener("abort", onAbort, { once: true });
    if (options.signal?.aborted) controller.abort();
    let timedOut = false;
    const timeout = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 30_000);
    try {
      const response = await fetch(path, {
        method: options.method || "GET",
        signal: controller.signal,
        // Retain same-origin preview access cookies; scoped bearer access still applies.
        credentials: "same-origin",
        cache: "no-store",
        redirect: "error",
        mode: "same-origin",
        headers: {
          Authorization: `Bearer ${this.#credential}`,
          Accept: "application/json",
          ...(options.pdf
            ? { "Content-Type": "application/pdf" }
            : options.body !== undefined
              ? { "Content-Type": "application/json" }
              : {}),
        },
        body:
          options.pdf ||
          (options.body !== undefined
            ? JSON.stringify(options.body)
            : undefined),
      });
      if (response.status === 401) {
        this.onUnauthorised?.();
        await response.body?.cancel();
        throw new ApiError("NOT_AUTHORIZED", 401);
      }
      const value = await boundedJson(response);
      if (!response.ok) {
        const standard: Record<number, string> = {
          403: "FORBIDDEN",
          404: "NOT_FOUND",
          409: "CONFLICT",
          413: "PAYLOAD_TOO_LARGE",
          422: "VALIDATION_ERROR",
          503: "DATABASE_UNAVAILABLE",
        };
        let code = standard[response.status] || "REQUEST_FAILED";
        try {
          const envelope = validateResponse<{ error: { code: string } }>(
            value,
            "ErrorResponse",
          );
          if (Object.hasOwn(messages, envelope.error.code))
            code = envelope.error.code;
        } catch {
          /* Invalid error bodies never become visible source or diagnostic text. */
        }
        const header = response.headers.get("x-request-id");
        const requestId =
          header && /^[a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}$/i.test(header)
            ? header
            : null;
        throw new ApiError(code, response.status, requestId);
      }
      return validateResponse<T>(value, schema);
    } catch (error) {
      if (options.signal?.aborted)
        throw new DOMException("Aborted", "AbortError");
      if (timedOut) throw new ApiError("TIMEOUT");
      if (error instanceof ApiError) throw error;
      throw new ApiError("NETWORK");
    } finally {
      clearTimeout(timeout);
      options.signal?.removeEventListener("abort", onAbort);
    }
  }
  get<T>(path: string, schema: string, signal?: AbortSignal) {
    return this.request<T>(path, schema, { signal });
  }
  post<T>(path: string, schema: string, body: unknown, signal?: AbortSignal) {
    return this.request<T>(path, schema, { method: "POST", body, signal });
  }
  upload<T>(path: string, schema: string, pdf: File, signal?: AbortSignal) {
    return this.request<T>(path, schema, { method: "POST", pdf, signal });
  }
  async all<T>(
    path: string,
    schema: string,
    signal?: AbortSignal,
  ): Promise<T[]> {
    const rows: T[] = [];
    for (let offset = 0; offset < 10_000; offset += 100) {
      const page = await this.get<{
        items: T[];
        total: number;
        needs_evidence_revalidation?: boolean;
      }>(
        `${path}${path.includes("?") ? "&" : "?"}limit=100&offset=${offset}`,
        schema,
        signal,
      );
      if (page.needs_evidence_revalidation)
        throw new ApiError("EVIDENCE_WITHHELD", 409);
      rows.push(...page.items);
      if (rows.length >= page.total) return rows;
      if (page.items.length === 0) throw new ApiError("INVALID_RESPONSE");
    }
    throw new ApiError("RESPONSE_TOO_LARGE");
  }
}
