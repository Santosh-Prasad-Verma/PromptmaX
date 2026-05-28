document.addEventListener("DOMContentLoaded", function () {
  var statusNode = document.getElementById("pricing-status");
  var buttons = document.querySelectorAll("[data-plan]");

  function getToken() {
    return localStorage.getItem("promptmax_token") || "";
  }

  function getUser() {
    try {
      return JSON.parse(localStorage.getItem("promptmax_user") || "null");
    } catch (error) {
      return null;
    }
  }

  function saveUser(user) {
    if (user) localStorage.setItem("promptmax_user", JSON.stringify(user));
  }

  function setStatus(message, kind) {
    if (!statusNode) return;
    statusNode.textContent = message || "";
    statusNode.className = "pricing-status" + (kind ? " " + kind : "");
  }

  function apiErrorMessage(data, response) {
    if (data && data.message) return data.message;
    if (data && data.detail) return data.detail;
    if (data && typeof data.error === "string") return data.error;
    if (data && data.details) {
      var firstKey = Object.keys(data.details)[0];
      var firstValue = firstKey ? data.details[firstKey] : "";
      if (Array.isArray(firstValue)) firstValue = firstValue[0];
      if (firstKey && firstValue) return firstKey + ": " + firstValue;
    }
    return response && response.status ? "Request failed (" + response.status + ")" : "Request failed";
  }

  async function api(path, payload) {
    var token = getToken();
    var response = await fetch(path, {
      method: payload ? "POST" : "GET",
      headers: Object.assign(
        { "Content-Type": "application/json" },
        token ? { Authorization: "Token " + token } : {}
      ),
      credentials: "same-origin",
      body: payload ? JSON.stringify(payload) : undefined,
    });
    var data = await response.json().catch(function () {
      return {};
    });
    if (!response.ok || data.success === false) {
      var error = new Error(apiErrorMessage(data, response));
      error.status = response.status;
      throw error;
    }
    return data;
  }

  async function selectFreePlan(button) {
    button.disabled = true;
    setStatus("Activating Free plan...", "");
    try {
      var data = await api("/api/v1/auth/select-plan/", { plan: "free" });
      saveUser(data.user || Object.assign({}, getUser(), { plan: data.plan }));
      setStatus("Free plan selected. Opening chat...", "success");
      window.location.assign("/chat");
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        localStorage.removeItem("promptmax_token");
        localStorage.removeItem("promptmax_user");
        window.location.href = "/login";
        return;
      }
      setStatus(error.message, "error");
      button.disabled = false;
    }
  }

  async function openPaidCheckout(plan, button) {
    if (!window.Razorpay) {
      setStatus("Razorpay checkout script did not load. Check your internet connection and try again.", "error");
      return;
    }

    button.disabled = true;
    setStatus("Starting secure checkout...", "");

    try {
      var orderData = await api("/api/v1/auth/razorpay/order/", { plan: plan });
      var user = orderData.user || getUser() || {};
      var checkout = new window.Razorpay({
        key: orderData.key_id,
        amount: orderData.order.amount,
        currency: orderData.order.currency,
        name: "PromptmaX",
        description: orderData.plan.label + " plan",
        order_id: orderData.order.id,
        prefill: {
          name: user.name || "",
          email: user.email || "",
        },
        theme: { color: "#005346" },
        modal: {
          ondismiss: function () {
            button.disabled = false;
            setStatus("Payment cancelled. Your current plan was not changed.", "error");
          },
        },
        handler: async function (response) {
          setStatus("Verifying payment...", "");
          try {
            var verified = await api("/api/v1/auth/razorpay/verify/", {
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            saveUser(verified.user || Object.assign({}, getUser(), { plan: verified.plan }));
            setStatus("Payment verified. Opening chat...", "success");
            window.location.assign("/chat");
          } catch (error) {
            button.disabled = false;
            setStatus(error.message, "error");
          }
        },
      });

      checkout.open();
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        localStorage.removeItem("promptmax_token");
        localStorage.removeItem("promptmax_user");
        window.location.href = "/login";
        return;
      }
      button.disabled = false;
      setStatus(error.message, "error");
    }
  }

  async function refreshUser() {
    if (!getToken()) return;
    try {
      var data = await api("/api/v1/auth/me/");
      saveUser(data.user);
      if (data.user && data.user.plan) {
        setStatus("Current plan: " + data.user.plan.label + ". You can continue to the playground.", "success");
      }
    } catch (error) {
      localStorage.removeItem("promptmax_token");
      localStorage.removeItem("promptmax_user");
    }
  }

  buttons.forEach(function (button) {
    button.addEventListener("click", async function () {
      var plan = button.getAttribute("data-plan");
      if (!getToken()) {
        window.location.href = "/login";
        return;
      }

      if (plan === "free") {
        await selectFreePlan(button);
        return;
      }

      await openPaidCheckout(plan, button);
    });
  });

  refreshUser();
});
