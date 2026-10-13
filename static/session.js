"use strict";

// The shared session helper of section 31 point 1. It is loaded on the five
// application pages and does three small things, so the existing page scripts
// do not have to change:
//
// - it copies the readable CSRF cookie into the X-CSRF-Token header on every
//   same-origin fetch, which is the double-submit the server checks on every
//   state-changing POST;
// - it sends the browser to the login page when a call answers 401, so an
//   expired session does not leave a half-loaded page behind;
// - it adds a Sign out control to the top bar, so the logout endpoint is
//   reachable from the UI.

(function () {
  const CSRF_COOKIE = "vardkey_csrf";
  const CSRF_HEADER = "X-CSRF-Token";
  const nativeFetch = window.fetch.bind(window);

  function readCookie(name) {
    const prefix = `${name}=`;
    for (const part of document.cookie.split(";")) {
      const entry = part.trim();
      if (entry.startsWith(prefix)) {
        return decodeURIComponent(entry.slice(prefix.length));
      }
    }
    return null;
  }

  window.fetch = function (input, init) {
    const token = readCookie(CSRF_COOKIE);
    let options = init;
    if (token) {
      const source = (init && init.headers)
        || (typeof input === "object" && input && input.headers)
        || {};
      const headers = new Headers(source);
      if (!headers.has(CSRF_HEADER)) {
        headers.set(CSRF_HEADER, token);
      }
      options = { ...(init || {}), headers };
    }
    return nativeFetch(input, options).then((response) => {
      if (response.status === 401) {
        window.location.assign("/login");
      }
      return response;
    });
  };

  function signOut() {
    // The CSRF header is added by the wrapped fetch above. A failed logout still
    // sends the user to the login page, because the session is of no use either
    // way.
    window.fetch("/api/logout", { method: "POST" }).catch(() => {}).finally(() => {
      window.location.assign("/login");
    });
  }

  function addSignOutControl() {
    const topbar = document.querySelector(".topbar");
    if (!topbar || topbar.querySelector(".sign-out")) {
      return;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "sign-out";
    button.textContent = "Sign out";
    button.addEventListener("click", signOut);
    (topbar.querySelector(".topbar-actions") || topbar).append(button);
  }

  addSignOutControl();
})();
