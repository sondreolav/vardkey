"use strict";

// The login step of section 31 point 1. The page carries two separate forms, so
// only the visible one is validated and submitted, and this script picks which
// one to show. It does not load session.js: there is no session yet, and the
// CSRF token only exists once one is started.

const loginForm = document.querySelector("#login-form");
const createAdminForm = document.querySelector("#create-admin-form");
const status = document.querySelector("#login-status");
const title = document.querySelector("#login-title");
const intro = document.querySelector("#login-intro");

function showLogin() {
  createAdminForm.hidden = true;
  loginForm.hidden = false;
  title.textContent = "Sign in";
  intro.textContent = "Enter the VardKey admin password to continue.";
}

function showCreateAdmin() {
  loginForm.hidden = true;
  createAdminForm.hidden = false;
  title.textContent = "Create the admin";
  intro.textContent = "No admin is configured yet. Create the single admin account for this VardKey service.";
}

async function readError(response) {
  try {
    const detail = await response.json();
    return detail.error || "The request could not be completed.";
  } catch {
    return "The request could not be completed.";
  }
}

async function loadSession() {
  try {
    const response = await fetch("/api/session", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      return;
    }
    const session = await response.json();
    if (session.authenticated) {
      // A session is already held, so there is nothing to sign in to.
      window.location.assign("/");
      return;
    }
    if (!session.admin_configured) {
      showCreateAdmin();
    }
  } catch {
    status.textContent = "The login state could not be loaded. Reload the page.";
  }
}

async function submitLogin(event) {
  event.preventDefault();
  if (!loginForm.reportValidity()) {
    return;
  }
  status.textContent = "Signing in…";
  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        username: document.querySelector("#login-username").value,
        password: document.querySelector("#login-password").value,
      }),
    });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    window.location.assign("/");
  } catch (error) {
    status.textContent = error.message;
  }
}

async function submitCreateAdmin(event) {
  event.preventDefault();
  if (!createAdminForm.reportValidity()) {
    return;
  }
  status.textContent = "Creating the admin…";
  try {
    const response = await fetch("/api/admin", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        username: document.querySelector("#admin-username").value,
        password: document.querySelector("#admin-password").value,
      }),
    });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    // The account is stored and a session is started, so the first-run key
    // setup step comes next.
    window.location.assign("/");
  } catch (error) {
    status.textContent = error.message;
  }
}

loginForm.addEventListener("submit", submitLogin);
createAdminForm.addEventListener("submit", submitCreateAdmin);
loadSession();
