"use strict";

// The VardKey service worker of section 31 point 6. It caches only the static
// shell, never an API response, never /health, and never the login page, so the
// app can never show stale or unauthenticated data. Every fetch still goes to
// the server first; the cache is only there for the shell while the server is
// unreachable.

const CACHE_NAME = "vardkey-shell-v1";

// The shell: the pages and the assets they need. /api/*, /health and /login are
// deliberately absent.
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
];

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
  if (url.origin !== self.location.origin) {
    return false;
  }
  // The API, the readiness endpoint and the login page always go to the server.
  return !(
    url.pathname.startsWith("/api/")
    || url.pathname === "/health"
    || url.pathname === "/login"
  );
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
