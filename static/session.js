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
// - it adds the navigation menu to the top bar, so the pages and the logout
//   endpoint are reachable from every page (section 32.7 point 1).

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

  // The menu replaced the lone Sign out button, so the top bar is the same on
  // every page and the dashboard keeps no navigation link of its own
  // (section 32.7 point 1). The order is the dashboard first, then the check
  // form, the settings and the history, then a separator, then Sign out. The
  // page the user is already on is marked and greyed out instead of being a
  // link (section 32.7 follow-up point 2).
  const MENU_ITEMS = [
    { label: "Dashboard", href: "/" },
    { label: "Start health check", href: "/health-check" },
    { label: "Settings", href: "/settings" },
    { label: "History", href: "/history" },
  ];
  const MENU_PANEL_ID = "app-menu-panel";

  function setMenuOpen(menu, open) {
    const panel = menu.querySelector(".menu-panel");
    const button = menu.querySelector(".menu-button");
    if (!panel || !button) {
      return;
    }
    panel.hidden = !open;
    button.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function currentPath() {
    // "/health-check/" and "/health-check" are the same page, and the root stays
    // "/", so the menu compares normalised paths alone.
    const path = window.location.pathname.replace(/\/+$/, "");
    return path === "" ? "/" : path;
  }

  function createMenuItem(menu, item) {
    if (currentPath() === item.href) {
      // The page the user is already on is not a link at all: a span cannot be
      // followed, so the menu never reloads the page it is showing, and
      // aria-current tells a screen reader where the user is.
      const current = document.createElement("span");
      current.className = "menu-item menu-item-current";
      current.textContent = item.label;
      current.setAttribute("aria-current", "page");
      return current;
    }
    const link = document.createElement("a");
    link.className = "menu-item";
    link.href = item.href;
    link.textContent = item.label;
    link.addEventListener("click", () => setMenuOpen(menu, false));
    return link;
  }

  function createMenu() {
    const menu = document.createElement("div");
    menu.className = "menu";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary-button menu-button";
    button.textContent = "Menu";
    button.setAttribute("aria-haspopup", "true");
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", MENU_PANEL_ID);

    // The panel is hidden until the button is pressed, so the menu never covers
    // the page on its own.
    const panel = document.createElement("div");
    panel.className = "menu-panel";
    panel.id = MENU_PANEL_ID;
    panel.hidden = true;

    for (const item of MENU_ITEMS) {
      panel.append(createMenuItem(menu, item));
    }

    const separator = document.createElement("div");
    separator.className = "menu-separator";
    separator.setAttribute("role", "separator");
    panel.append(separator);

    const signOutButton = document.createElement("button");
    signOutButton.type = "button";
    signOutButton.className = "menu-item";
    signOutButton.textContent = "Sign out";
    signOutButton.addEventListener("click", () => {
      setMenuOpen(menu, false);
      signOut();
    });
    panel.append(signOutButton);

    button.addEventListener("click", () => {
      setMenuOpen(menu, panel.hidden);
    });

    menu.append(button, panel);
    return menu;
  }

  function addNavigationMenu() {
    const topbar = document.querySelector(".topbar");
    if (!topbar || topbar.querySelector(".menu")) {
      return;
    }
    const menu = createMenu();
    (topbar.querySelector(".topbar-actions") || topbar).append(menu);

    // The panel closes on Escape and on a click outside it, so it never stays
    // open behind another interaction (section 32.7 point 1). A click on the
    // button is inside the menu, so the toggle above is what handles it.
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        setMenuOpen(menu, false);
      }
    });
    document.addEventListener("click", (event) => {
      if (!menu.contains(event.target)) {
        setMenuOpen(menu, false);
      }
    });
  }

  addNavigationMenu();
})();
