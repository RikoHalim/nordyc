import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { isLocalDemoRequest, loadLocalDemo } from "../dev/local-demo";

const institution = "00000000-0000-4000-8000-000000000001";
const credential = "SYNTHETIC-LOCAL-DEMO-TEST-ONLY-NOT-LIVE";
const directories: string[] = [];
function fixture(receiptChanges = {}, operatorChanges = {}) {
  const directory = mkdtempSync(join(tmpdir(), "shiftos-local-demo-test-"));
  directories.push(directory);
  const file = join(directory, "auth.private.json");
  writeFileSync(
    file,
    JSON.stringify({
      operator: {
        token: credential,
        permissions: ["read", "write", "review"],
        institution_ids: [institution],
        ...operatorChanges,
      },
    }),
  );
  writeFileSync(
    join(directory, "receipt.json"),
    JSON.stringify({
      is_synthetic: true,
      provider_execution: "mocked",
      external_http: "blocked",
      live_requests: 0,
      status: "ready",
      public_deployment: false,
      programmes: [{ institution_id: institution }],
      ...receiptChanges,
    }),
  );
  return file;
}
afterEach(() => {
  for (const directory of directories.splice(0)) {
    if (
      dirname(resolve(directory)) !== resolve(tmpdir()) ||
      !basename(directory).startsWith("shiftos-local-demo-test-")
    )
      throw new Error("Refusing cleanup outside the owned test directory.");
    rmSync(directory, { recursive: true, force: true });
  }
});

describe("server-only local demonstration opt-in", () => {
  it("does nothing without an explicit private auth file", () => {
    expect(loadLocalDemo()).toBeUndefined();
    expect(loadLocalDemo("")).toBeUndefined();
  });
  it("loads only the scoped synthetic operator credential", () => {
    expect(loadLocalDemo(fixture())).toEqual({ credential });
  });
  it.each([
    { is_synthetic: false },
    { provider_execution: "live" },
    { external_http: "allowed" },
    { live_requests: 1 },
    { status: "stopped" },
    { public_deployment: true },
    { programmes: [] },
  ])("rejects unsafe receipt %j", (changes) => {
    expect(() => loadLocalDemo(fixture(changes))).toThrow(
      "Local synthetic demo access is not valid.",
    );
  });
  it.each([
    { token: "" },
    { token: `${credential}\n` },
    { permissions: ["read", "admin"] },
    { permissions: ["write"] },
    { institution_ids: [] },
    { institution_ids: ["00000000-0000-4000-8000-000000000099"] },
  ])("rejects unscoped or unsafe operator %j", (changes) => {
    expect(() => loadLocalDemo(fixture({}, changes))).toThrow(
      "Local synthetic demo access is not valid.",
    );
  });
  it("does not leak file content or paths in malformed-file errors", () => {
    const file = fixture();
    writeFileSync(file, credential);
    expect(() => loadLocalDemo(file)).toThrow(
      "Local synthetic demo access is not valid.",
    );
  });
});

describe("local demonstration request boundary", () => {
  const request = (remoteAddress = "127.0.0.1", headers = {}) => ({
    socket: { remoteAddress },
    headers: { host: "127.0.0.1:5178", ...headers },
  });
  it.each(["127.0.0.1", "127.0.0.2", "::1", "::ffff:127.0.0.1"])(
    "accepts loopback socket %s with matching local origin",
    (address) => {
      expect(
        isLocalDemoRequest(
          request(address, {
            origin: "http://127.0.0.1:5178",
            "sec-fetch-site": "same-origin",
          }),
        ),
      ).toBe(true);
    },
  );
  it("accepts explicit localhost and IPv6 loopback hosts", () => {
    expect(isLocalDemoRequest(request("::1", { host: "[::1]:5178" }))).toBe(
      true,
    );
    expect(
      isLocalDemoRequest(request("127.0.0.1", { host: "localhost" })),
    ).toBe(true);
  });
  it.each(["10.0.0.1", "192.168.1.2", "203.0.113.1", "::ffff:10.0.0.1", ""])(
    "rejects non-loopback socket %s",
    (address) => expect(isLocalDemoRequest(request(address))).toBe(false),
  );
  it.each([
    { host: "public.pike.replit.dev" },
    { host: "localhost.attacker.invalid" },
    { host: "127.0.0.1:65536" },
    { host: "127.0.0.1:0" },
    { host: "127.999.0.1" },
    { host: "user@localhost" },
    { origin: "https://outside.invalid" },
    { origin: "http://localhost:5178" },
    { origin: "null" },
    { "sec-fetch-site": "cross-site" },
    { "sec-fetch-site": "same-site" },
    { "x-forwarded-host": "public.pike.replit.dev" },
    { "x-forwarded-for": "203.0.113.1" },
    { forwarded: "for=203.0.113.1;host=public.pike.replit.dev" },
  ])("rejects public or mismatched request headers %j", (headers) => {
    expect(isLocalDemoRequest(request("127.0.0.1", headers))).toBe(false);
  });
});
