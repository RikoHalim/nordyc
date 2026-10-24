import { defineConfig, loadEnv, normalizePath } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { loadLocalDemo, isLocalDemoRequest } from "./dev/local-demo.ts";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const port = Number(env.FRONTEND_PORT || 5173);
  const target = env.BACKEND_ORIGIN || "http://127.0.0.1:8000";
  const url = new URL(target);
  const localDemo =
    mode === "production"
      ? undefined
      : loadLocalDemo(env.SHIFTOS_LOCAL_DEMO_AUTH_FILE);
  if (
    localDemo &&
    !["127.0.0.1", "localhost", "::1"].includes(
      env.FRONTEND_HOST || "127.0.0.1",
    )
  )
    throw new Error(
      "Automatic demonstration access requires a loopback server.",
    );
  if (
    !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname) ||
    url.protocol !== "http:"
  ) {
    throw new Error(
      "The development API proxy requires an explicit loopback HTTP backend.",
    );
  }
  if (!Number.isInteger(port) || port < 1 || port > 65535)
    throw new Error("Invalid frontend port.");
  return {
    plugins: [
      react(),
      {
        name: "local-synthetic-demo-entry",
        configureServer(server) {
          server.middlewares.use((request, response, next) => {
            if (request.url?.split("?")[0] === "/__local_demo") {
              response.setHeader("Cache-Control", "no-store");
              response.setHeader("Content-Type", "application/json");
              if (!isLocalDemoRequest(request)) {
                response.statusCode = 404;
                response.end('{"enabled":false}');
              } else {
                response.end(JSON.stringify({ enabled: Boolean(localDemo) }));
              }
              return;
            }
            if (
              localDemo &&
              request.url?.startsWith("/api/") &&
              !isLocalDemoRequest(request)
            ) {
              response.statusCode = 403;
              response.end();
              return;
            }
            next();
          });
        },
      },
    ],
    server: {
      host: env.FRONTEND_HOST || "127.0.0.1",
      port,
      strictPort: true,
      allowedHosts: env.REPLIT_DEV_DOMAIN ? [env.REPLIT_DEV_DOMAIN] : [],
      fs: {
        strict: true,
        allow: [
          normalizePath(resolve(fileURLToPath(new URL(".", import.meta.url)))),
        ],
        deny: [
          "**/.env",
          "**/.env.*",
          "**/*.{crt,pem,key,p12,pfx}",
          "**/.git/**",
          `${normalizePath(resolve(fileURLToPath(new URL("../data/local", import.meta.url))))}/**`,
          "**/secrets/**",
          "**/*.private.json",
          "**/test-results/**",
          "**/playwright-report/**",
          "**/tests/**",
        ],
      },
      proxy: {
        "/api": {
          target,
          configure(proxy) {
            proxy.on("proxyReq", (outgoing, request) => {
              if (
                localDemo &&
                isLocalDemoRequest(request) &&
                !request.headers.authorization
              )
                outgoing.setHeader(
                  "Authorization",
                  `Bearer ${localDemo.credential}`,
                );
            });
          },
        },
        "/health": { target },
      },
    },
    preview: { host: "127.0.0.1", port, strictPort: true },
    build: {
      sourcemap: false,
      chunkSizeWarningLimit: 400,
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              {
                name: "react-runtime",
                test: /node_modules[\\/](react|react-dom|react-router|react-router-dom)[\\/]/,
                priority: 20,
              },
              {
                name: "schema-validation",
                test: /node_modules[\\/](ajv|ajv-formats|fast-uri|fast-deep-equal|json-schema-traverse)[\\/]/,
                priority: 15,
              },
              {
                name: "api-contract",
                test: /api[\\/]openapi\.json$/,
                priority: 10,
              },
            ],
          },
        },
      },
    },
  };
});
