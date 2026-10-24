import { ApiError } from "../api/client";
import type { AccessContext } from "../api/types";

export type PublicUploadInput = {
  institution_name: string;
  institution_url: string;
  programme_name: string;
  programme_url: string;
  permitted_public_document: true;
};

export type PublicUploadWorkspace = {
  programme_id: string;
  institution_id: string;
};

const uuid = (value: unknown): value is string =>
  typeof value === "string" &&
  /^[a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}$/i.test(value);

export function publicWorkspaceAccess(
  access: AccessContext,
  enabled: boolean | undefined,
  ownInstitution: string | undefined,
  programmeInstitution: string,
): AccessContext {
  if (!enabled) return access;
  return {
    ...access,
    global_admin: false,
    permissions: access.permissions.filter(
      (permission) =>
        permission === "read" ||
        (permission === "write" &&
          ownInstitution === programmeInstitution &&
          access.institution_ids.includes(programmeInstitution)),
    ),
  };
}

/** The session credential stays in the server's HttpOnly cookie, never this JSON. */
export async function createPublicUploadWorkspace(
  input: PublicUploadInput,
  signal?: AbortSignal,
): Promise<PublicUploadWorkspace> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  if (signal?.aborted) controller.abort();
  const timeout = setTimeout(abort, 30_000);
  try {
    const response = await fetch("/__public_upload_session", {
      method: "POST",
      credentials: "same-origin",
      mode: "same-origin",
      redirect: "error",
      cache: "no-store",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(input),
    });
    if (!response.ok) {
      await response.body?.cancel();
      const code =
        response.status === 403
          ? "FORBIDDEN"
          : response.status === 429
            ? "PUBLIC_UPLOAD_LIMIT"
            : response.status === 422
              ? "VALIDATION_ERROR"
              : "PUBLIC_UPLOAD_UNAVAILABLE";
      throw new ApiError(code, response.status);
    }
    if (
      !response.headers.get("content-type")?.includes("application/json") ||
      Number(response.headers.get("content-length")) > 16_384
    ) {
      await response.body?.cancel();
      throw new ApiError("INVALID_RESPONSE");
    }
    const reader = response.body?.getReader();
    if (!reader) throw new ApiError("INVALID_RESPONSE");
    let size = 0;
    let text = "";
    const decoder = new TextDecoder();
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > 16_384) {
          await reader.cancel();
          throw new ApiError("INVALID_RESPONSE");
        }
        text += decoder.decode(value, { stream: true });
      }
    } finally {
      reader.releaseLock();
    }
    const result: unknown = JSON.parse(text + decoder.decode());
    if (
      !result ||
      typeof result !== "object" ||
      !("programme_id" in result) ||
      !("institution_id" in result) ||
      !uuid(result.programme_id) ||
      !uuid(result.institution_id)
    )
      throw new ApiError("INVALID_RESPONSE");
    return {
      programme_id: result.programme_id,
      institution_id: result.institution_id,
    };
  } catch (error) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    if (controller.signal.aborted) throw new ApiError("TIMEOUT");
    if (error instanceof ApiError) throw error;
    throw new ApiError("PUBLIC_UPLOAD_UNAVAILABLE");
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener("abort", abort);
  }
}
