/**
 * Bootstrap admin creation — standalone so it does not depend on main.js load order.
 * Uses the same origin as the page (works for localhost, 127.0.0.1, and deployed hosts).
 */
(function () {
  "use strict";

  function formatApiErrorDetail(detail) {
    if (detail == null) return "Request failed";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map(function (x) { return (x && x.msg) ? x.msg : JSON.stringify(x); }).join("; ");
    }
    return String(detail);
  }

  function bootstrapAdmin(ev) {
    if (ev) ev.preventDefault();

    var emailEl = document.getElementById("email");
    var passwordEl = document.getElementById("password");
    var secretEl = document.getElementById("bootstrapSecret");

    if (!emailEl || !passwordEl || !secretEl) {
      window.alert("Bootstrap controls are missing on this page. Use the login screen at the app home page.");
      return;
    }

    var email = (emailEl.value || "").trim();
    var password = passwordEl.value || "";
    var secret = secretEl.value || "";

    if (!email || !password) {
      window.alert("Enter email and password for the new admin account.");
      return;
    }
    if (!secret) {
      window.alert("Enter the bootstrap secret (see hint below).");
      return;
    }

    var url = window.location.origin + "/auth/bootstrap-admin";

    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: email,
        password: password,
        bootstrap_secret: secret
      })
    })
      .then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) {
          if (!res.ok) {
            throw new Error(formatApiErrorDetail(data.detail) || "Bootstrap failed");
          }
          return data;
        });
      })
      .then(function () {
        window.alert("Admin created. You can log in with that email and password.");
      })
      .catch(function (err) {
        window.alert(err.message || String(err));
      });
  }

  function wire() {
    var btn = document.getElementById("bootstrapAdminBtn");
    if (btn) {
      btn.addEventListener("click", bootstrapAdmin);
    }
    window.bootstrapAdmin = bootstrapAdmin;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();
