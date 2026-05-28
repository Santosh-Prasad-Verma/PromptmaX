document.addEventListener("DOMContentLoaded", function () {
  var API = "/api/v1/auth";

  function byId(id) {
    return document.getElementById(id);
  }

  function setStatus(id, message, kind) {
    var node = byId(id);
    if (!node) return;
    node.textContent = message || "";
    node.className = "auth-status show" + (kind ? " " + kind : "");
  }

  function clearStatus(id) {
    var node = byId(id);
    if (!node) return;
    node.textContent = "";
    node.className = "auth-status";
  }

  async function postJSON(path, payload) {
    var response = await fetch(API + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });
    var data = await response.json().catch(function () {
      return {};
    });
    if (!response.ok || data.success === false) {
      var detail = data.message || data.error || "Request failed";
      if (data.details) {
        var firstKey = Object.keys(data.details)[0];
        if (firstKey && data.details[firstKey][0]) detail = data.details[firstKey][0];
      }
      throw new Error(detail);
    }
    return data;
  }

  function saveSession(data) {
    if (data.token) localStorage.setItem("promptmax_token", data.token);
    if (data.user) localStorage.setItem("promptmax_user", JSON.stringify(data.user));
  }

  function getSessionUser() {
    try {
      return JSON.parse(localStorage.getItem("promptmax_user") || "null");
    } catch (error) {
      return null;
    }
  }

  function redirectAfterAuth() {
    var user = getSessionUser();
    if (user && user.plan && user.plan.plan) {
      window.location.href = "/chat";
      return;
    }
    window.location.href = "/pricing?first=1";
  }

  function getValue(id) {
    var el = byId(id);
    return el ? el.value.trim() : "";
  }

  var loginForm = byId("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      clearStatus("auth-status");
      try {
        var data = await postJSON("/login/", {
          email: getValue("login-email").toLowerCase(),
          password: getValue("login-password"),
        });
        saveSession(data);
        setStatus("auth-status", "Signed in. Opening PromptmaX...", "success");
        setTimeout(redirectAfterAuth, 450);
      } catch (error) {
        setStatus("auth-status", error.message, "error");
      }
    });
  }

  var registerForm = byId("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      clearStatus("auth-status");
      var password = getValue("register-password");
      var confirm = getValue("register-confirm");
      if (password !== confirm) {
        setStatus("auth-status", "Passwords do not match.", "error");
        return;
      }
      try {
        await postJSON("/register/", {
          name: getValue("register-name"),
          email: getValue("register-email").toLowerCase(),
          password: password,
        });
        byId("otp-email").value = getValue("register-email").toLowerCase();
        byId("register-step").hidden = true;
        byId("otp-step").hidden = false;
        setStatus("otp-status", "Verification code sent. Check your email.", "success");
      } catch (error) {
        setStatus("auth-status", error.message, "error");
      }
    });
  }

  var otpForm = byId("otp-form");
  if (otpForm) {
    otpForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      clearStatus("otp-status");
      try {
        var data = await postJSON("/verify-otp/", {
          email: getValue("otp-email").toLowerCase(),
          otp: getValue("otp-code"),
        });
        saveSession(data);
        setStatus("otp-status", "Email verified. Choose your plan...", "success");
        setTimeout(redirectAfterAuth, 450);
      } catch (error) {
        setStatus("otp-status", error.message, "error");
      }
    });
  }

  var resendButton = byId("resend-otp");
  if (resendButton) {
    resendButton.addEventListener("click", async function () {
      clearStatus("otp-status");
      try {
        await postJSON("/resend-otp/", { email: getValue("otp-email").toLowerCase() });
        setStatus("otp-status", "New verification code sent to your email.", "success");
      } catch (error) {
        setStatus("otp-status", error.message, "error");
      }
    });
  }

  var forgotRequestForm = byId("forgot-request-form");
  if (forgotRequestForm) {
    forgotRequestForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      clearStatus("auth-status");
      try {
        await postJSON("/forgot-password/", { email: getValue("forgot-email").toLowerCase() });
        byId("reset-email").value = getValue("forgot-email").toLowerCase();
        byId("request-step").hidden = true;
        byId("reset-step").hidden = false;
        setStatus("reset-status", "If the account exists, a reset code has been sent to that email.", "success");
      } catch (error) {
        setStatus("auth-status", error.message, "error");
      }
    });
  }

  var resetForm = byId("reset-form");
  if (resetForm) {
    resetForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      clearStatus("reset-status");
      var password = getValue("reset-password");
      var confirm = getValue("reset-confirm");
      if (password !== confirm) {
        setStatus("reset-status", "Passwords do not match.", "error");
        return;
      }
      try {
        await postJSON("/reset-password/", {
          email: getValue("reset-email").toLowerCase(),
          otp: getValue("reset-otp"),
          password: password,
        });
        setStatus("reset-status", "Password updated. Redirecting to sign in...", "success");
        setTimeout(function () {
          window.location.href = "/login";
        }, 750);
      } catch (error) {
        setStatus("reset-status", error.message, "error");
      }
    });
  }
});
