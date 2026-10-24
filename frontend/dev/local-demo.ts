import { readFileSync } from "node:fs";
import { basename, dirname, resolve } from "node:path";
import { isIP } from "node:net";
import type { IncomingHttpHeaders } from "node:http";

type LocalDemoRequest = {
  socket: { remoteAddress?: string };
  headers: IncomingHttpHeaders;
};
const record = (value: unknown): value is Record<string, unknown> =>
  Boolean(value && typeof value === "object" && !Array.isArray(value));
const uuid = (value: unknown): value is string =>
  typeof value === "string" &&
  /^[a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}$/i.test(value);

/** Server-only opt-in. Never serialize its return value into a browser response. */
export function loadLocalDemo(
  authFile?: string,
): { credential: string } | undefined {
  if (!authFile?.trim()) return undefined;
  try {
    const file = resolve(authFile);
    if (basename(file) !== "auth.private.json") throw new Error();
    const auth: unknown = JSON.parse(readFileSync(file, "utf8"));
    const receipt: unknown = JSON.parse(
      readFileSync(resolve(dirname(file), "receipt.json"), "utf8"),
    );
    if (
      !record(receipt) ||
      receipt.is_synthetic !== true ||
      receipt.provider_execution !== "mocked" ||
      receipt.external_http !== "blocked" ||
      receipt.live_requests !== 0 ||
      receipt.status !== "ready" ||
      receipt.public_deployment !== false ||
      !Array.isArray(receipt.programmes) ||
      receipt.programmes.length === 0 ||
      !receipt.programmes.every(
        (row) => record(row) && uuid(row.institution_id),
      ) ||
      !record(auth) ||
      !record(auth.operator)
    )
      throw new Error();
    const operator = auth.operator;
    const institutions = new Set(
      receipt.programmes.map((row) => row.institution_id as string),
    );
    if (
      typeof operator.token !== "string" ||
      operator.token.length < 32 ||
      operator.token.length > 4096 ||
      /[\s\u0000-\u001f]/.test(operator.token) ||
      !Array.isArray(operator.permissions) ||
      !operator.permissions.includes("read") ||
      !operator.permissions.every((permission) =>
        ["read", "write", "review"].includes(permission),
      ) ||
      !Array.isArray(operator.institution_ids) ||
      operator.institution_ids.length === 0 ||
      !operator.institution_ids.every((id) => uuid(id) && institutions.has(id))
    )
      throw new Error();
    return { credential: operator.token };
  } catch {
    throw new Error("Local synthetic demo access is not valid.");
  }
}

function loopbackAddress(address?: string) {
  if (!address) return false;
  if (address === "::1") return true;
  const ipv4 = address.startsWith("::ffff:") ? address.slice(7) : address;
  return isIP(ipv4) === 4 && ipv4.startsWith("127.");
}

/** A forwarded/public request can never receive local development access. */
export function isLocalDemoRequest(request: LocalDemoRequest): boolean {
  if (!loopbackAddress(request.socket.remoteAddress)) return false;
  if (
    [
      "forwarded",
      "x-forwarded-for",
      "x-forwarded-host",
      "x-forwarded-proto",
    ].some((header) => request.headers[header] !== undefined)
  )
    return false;
  const { host, origin } = request.headers;
  if (typeof host !== "string") return false;
  const match =
    /^(localhost|127(?:\.\d{1,3}){3}|\[::1\])(?::(\d{1,5}))?$/i.exec(host);
  if (!match) return false;
  const hostname = match[1].toLowerCase();
  if (
    hostname !== "localhost" &&
    hostname !== "[::1]" &&
    !loopbackAddress(hostname)
  )
    return false;
  if (match[2] && (Number(match[2]) < 1 || Number(match[2]) > 65535))
    return false;
  if (origin !== undefined && origin !== `http://${host}`) return false;
  const site = request.headers["sec-fetch-site"];
  return site === undefined || site === "same-origin" || site === "none";
}
