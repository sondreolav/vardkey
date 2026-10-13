"use strict";

// The VardKey service worker of section 31 point 6. It caches only the static
// shell, never an API response, never the health endpoint, and never the login
// page, so the app can never show stale or unauthenticated data. It does that
// with an allowlist: only a request for one of the shell paths below is handled
// at all. Everything else is left to the browser and goes straight to the
// server. Every shell fetch still tries the server first; the cache is only
// there while the server is unreachable.

const CACHE_NAME = "vardkey-shell-v1";

// The shell: the pages, the assets they need, and the manifest and icon the
// browser reads when the app is installed.
const SHELL = [
  "/",
  "/setup",
  "/settings",
  "/health-check",
  "/history",
  "/styles.css",
  "/session.js",
  "/app.js",
  "/setup.js",
  "/settings.js",
  "/health-check.js",
  "/history.js",
  "/manifest.webmanifest",
  "/icon.svg",
];
const SHELL_PATHS = new Set(SHELL);

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) =>
        Promise.all(
          names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

function isShellRequest(request) {
  if (request.method !== "GET") {
    return false;
  }
  const url = new URL(request.url);
  // A query string, such as the history detail link, still matches its path.
  return url.origin === self.location.origin && SHELL_PATHS.has(url.pathname);
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (!isShellRequest(request)) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        // A fresh copy replaces the cached shell, so an update is picked up as
        // soon as the server answers.
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        return response;
      })
      .catch(() =>
        caches.match(request).then((cached) => {
          if (cached) {
            return cached;
          }
          // A navigation that was never cached falls back to the dashboard
          // shell; anything else has nothing to fall back to.
          if (request.mode === "navigate") {
            return caches.match("/");
          }
          return Response.error();
        }),
      ),
  );
});
