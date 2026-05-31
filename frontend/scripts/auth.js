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

  // Auto-capture Supabase session on page load (handles redirect verifications)
  if (window.getSupabaseClient) {
    window.getSupabaseClient(async function (supabase) {
      if (supabase) {
        try {
          var sessionResult = await supabase.auth.getSession();
          var session = sessionResult.data?.session;
          var user = sessionResult.data?.session?.user;
          if (session && session.access_token) {
            localStorage.setItem("promptmax_token", session.access_token);
            var localUserData = {
              email: user.email,
              name: user.user_metadata?.full_name || user.user_metadata?.name || "Supabase User",
              plan: { plan: "free", label: "Free", price_rs: 0 }
            };
            localStorage.setItem("promptmax_user", JSON.stringify(localUserData));
            
            // Auto-redirect to chat if on login page
            if (window.location.pathname.indexOf("/login") !== -1 || window.location.pathname.indexOf("/register") !== -1) {
              window.location.href = "/chat";
            }
          }
        } catch (err) {
          console.error("Auth session auto-capture failed:", err);
        }
      }
    });
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
      var email = getValue("login-email").toLowerCase();
      var password = getValue("login-password");

      // Check if Supabase client is available
      if (window.getSupabaseClient) {
        window.getSupabaseClient(async function (supabase) {
          if (supabase) {
            try {
              setStatus("auth-status", "Signing in via Supabase...", "info");
              var authResult = await supabase.auth.signInWithPassword({
                email: email,
                password: password,
              });
              
              if (authResult.error) {
                throw new Error(authResult.error.message);
              }

              var session = authResult.data.session;
              var user = authResult.data.user;
              if (session && session.access_token) {
                localStorage.setItem("promptmax_token", session.access_token);
                var localUserData = {
                  email: user.email,
                  name: user.user_metadata?.full_name || user.user_metadata?.name || "Supabase User",
                  plan: { plan: "free", label: "Free", price_rs: 0 }
                };
                localStorage.setItem("promptmax_user", JSON.stringify(localUserData));
                
                // Fast-sync/provision with Django backend
                try {
                  var meResponse = await fetch("/api/v1/auth/me/", {
                    headers: { "Authorization": "Bearer " + session.access_token }
                  });
                  if (meResponse.ok) {
                    var meData = await meResponse.json();
                    if (meData.success && meData.user) {
                      localStorage.setItem("promptmax_user", JSON.stringify(meData.user));
                    }
                  }
                } catch (meError) {
                  console.warn("Failed to sync user with Django backend during login:", meError);
                }

                setStatus("auth-status", "Signed in. Opening PromptmaX...", "success");
                setTimeout(redirectAfterAuth, 450);
              } else {
                throw new Error("No session returned from Supabase authentication");
              }
            } catch (error) {
              setStatus("auth-status", error.message, "error");
            }
            return;
          } else {
            // Fallback to Django login
            runDjangoLogin();
          }
        });
      } else {
        runDjangoLogin();
      }

      async function runDjangoLogin() {
        try {
          var data = await postJSON("/login/", {
            email: email,
            password: password,
          });
          saveSession(data);
          setStatus("auth-status", "Signed in. Opening PromptmaX...", "success");
          setTimeout(redirectAfterAuth, 450);
        } catch (error) {
          setStatus("auth-status", error.message, "error");
        }
      }
    });
  }

  var registerForm = byId("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      clearStatus("auth-status");
      var name = getValue("register-name");
      var email = getValue("register-email").toLowerCase();
      var password = getValue("register-password");
      var confirm = getValue("register-confirm");

      if (password !== confirm) {
        setStatus("auth-status", "Passwords do not match.", "error");
        return;
      }

      if (window.getSupabaseClient) {
        window.getSupabaseClient(async function (supabase) {
          if (supabase) {
            try {
              setStatus("auth-status", "Creating Supabase account...", "info");
              var authResult = await supabase.auth.signUp({
                email: email,
                password: password,
                options: {
                  emailRedirectTo: window.location.origin + '/login',
                  data: {
                    full_name: name
                  }
                }
              });

              if (authResult.error) {
                throw new Error(authResult.error.message);
              }

              var session = authResult.data.session;
              var user = authResult.data.user;

              if (session && session.access_token) {
                // Auto-logged in after signup
                localStorage.setItem("promptmax_token", session.access_token);
                var localUserData = {
                  email: user.email,
                  name: user.user_metadata?.full_name || user.user_metadata?.name || "Supabase User",
                  plan: { plan: "free", label: "Free", price_rs: 0 }
                };
                localStorage.setItem("promptmax_user", JSON.stringify(localUserData));
                
                try {
                  var meResponse = await fetch("/api/v1/auth/me/", {
                    headers: { "Authorization": "Bearer " + session.access_token }
                  });
                  if (meResponse.ok) {
                    var meData = await meResponse.json();
                    if (meData.success && meData.user) {
                      localStorage.setItem("promptmax_user", JSON.stringify(meData.user));
                    }
                  }
                } catch (meError) {
                  console.warn("Failed to sync user with Django backend during registration:", meError);
                }

                setStatus("auth-status", "Account created successfully. Redirecting...", "success");
                setTimeout(redirectAfterAuth, 450);
              } else {
                setStatus("auth-status", "Registration successful! Please check your email to verify your account.", "success");
              }
            } catch (error) {
              setStatus("auth-status", error.message, "error");
            }
            return;
          } else {
            runDjangoRegister();
          }
        });
      } else {
        runDjangoRegister();
      }

      async function runDjangoRegister() {
        try {
          await postJSON("/register/", {
            name: name,
            email: email,
            password: password,
          });
          byId("otp-email").value = email;
          byId("register-step").hidden = true;
          byId("otp-step").hidden = false;
          setStatus("otp-status", "Verification code sent. Check your email.", "success");
        } catch (error) {
          setStatus("auth-status", error.message, "error");
        }
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
      var email = getValue("forgot-email").toLowerCase();

      if (window.getSupabaseClient) {
        window.getSupabaseClient(async function (supabase) {
          if (supabase) {
            try {
              setStatus("auth-status", "Sending password reset via Supabase...", "info");
              var resetResult = await supabase.auth.resetPasswordForEmail(email, {
                redirectTo: window.location.origin + '/forgot-password',
              });

              if (resetResult.error) {
                throw new Error(resetResult.error.message);
              }

              setStatus("auth-status", "If the account exists, a reset link has been sent to your email.", "success");
            } catch (error) {
              setStatus("auth-status", error.message, "error");
            }
            return;
          } else {
            runDjangoForgot();
          }
        });
      } else {
        runDjangoForgot();
      }

      async function runDjangoForgot() {
        try {
          await postJSON("/forgot-password/", { email: email });
          byId("reset-email").value = email;
          byId("request-step").hidden = true;
          byId("reset-step").hidden = false;
          setStatus("reset-status", "If the account exists, a reset code has been sent to that email.", "success");
        } catch (error) {
          setStatus("auth-status", error.message, "error");
        }
      }
    });
  }

  var resetForm = byId("reset-form");
  if (resetForm) {
    resetForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      clearStatus("reset-status");
      var email = getValue("reset-email").toLowerCase();
      var otp = getValue("reset-otp");
      var password = getValue("reset-password");
      var confirm = getValue("reset-confirm");

      if (password !== confirm) {
        setStatus("reset-status", "Passwords do not match.", "error");
        return;
      }

      if (window.getSupabaseClient) {
        window.getSupabaseClient(async function (supabase) {
          if (supabase) {
            try {
              setStatus("reset-status", "Updating password via Supabase...", "info");
              var updateResult = await supabase.auth.updateUser({
                password: password,
              });

              if (updateResult.error) {
                throw new Error(updateResult.error.message);
              }

              setStatus("reset-status", "Password updated successfully. Redirecting to sign in...", "success");
              setTimeout(function () {
                window.location.href = "/login";
              }, 750);
            } catch (error) {
              setStatus("reset-status", error.message, "error");
            }
            return;
          } else {
            runDjangoReset();
          }
        });
      } else {
        runDjangoReset();
      }

      async function runDjangoReset() {
        try {
          await postJSON("/reset-password/", {
            email: email,
            otp: otp,
            password: password,
          });
          setStatus("reset-status", "Password updated. Redirecting to sign in...", "success");
          setTimeout(function () {
            window.location.href = "/login";
          }, 750);
        } catch (error) {
          setStatus("reset-status", error.message, "error");
        }
      }
    });
  }
});
