document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-prompt");
  var thread = document.getElementById("chat-thread");
  var status = document.getElementById("chat-status");
  var submitButton = document.getElementById("chat-submit");
  var modeSelect = document.getElementById("chat-mode");
  var activeMode = (modeSelect && modeSelect.value) || "generate";
  var planReady = false;
  var currentAssistantBubble = null;

  function token() {
    return localStorage.getItem("promptmax_token") || "";
  }

  function setStatus(text) {
    if (status) status.textContent = text || "";
  }

  function scrollThread() {
    if (thread) thread.scrollTop = thread.scrollHeight;
  }

  function escapeHTML(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function inlineMarkdown(value) {
    return escapeHTML(value)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
  }

  function renderMarkdown(markdown) {
    var lines = String(markdown || "").replace(/\r/g, "").split("\n");
    var html = [];
    var inCode = false;
    var codeLines = [];
    var listType = "";

    function closeList() {
      if (listType) {
        html.push("</" + listType + ">");
        listType = "";
      }
    }

    lines.forEach(function (line) {
      var codeFence = line.match(/^```/);
      if (codeFence) {
        if (inCode) {
          html.push("<pre><code>" + escapeHTML(codeLines.join("\n")) + "</code></pre>");
          codeLines = [];
          inCode = false;
        } else {
          closeList();
          inCode = true;
        }
        return;
      }

      if (inCode) {
        codeLines.push(line);
        return;
      }

      if (!line.trim()) {
        closeList();
        return;
      }

      var heading = line.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        closeList();
        html.push("<h" + heading[1].length + ">" + inlineMarkdown(heading[2]) + "</h" + heading[1].length + ">");
        return;
      }

      var unordered = line.match(/^\s*[-*]\s+(.+)$/);
      if (unordered) {
        if (listType !== "ul") {
          closeList();
          listType = "ul";
          html.push("<ul>");
        }
        html.push("<li>" + inlineMarkdown(unordered[1]) + "</li>");
        return;
      }

      var ordered = line.match(/^\s*\d+\.\s+(.+)$/);
      if (ordered) {
        if (listType !== "ol") {
          closeList();
          listType = "ol";
          html.push("<ol>");
        }
        html.push("<li>" + inlineMarkdown(ordered[1]) + "</li>");
        return;
      }

      var quote = line.match(/^>\s?(.+)$/);
      if (quote) {
        closeList();
        html.push("<blockquote>" + inlineMarkdown(quote[1]) + "</blockquote>");
        return;
      }

      closeList();
      html.push("<p>" + inlineMarkdown(line) + "</p>");
    });

    closeList();
    if (inCode) html.push("<pre><code>" + escapeHTML(codeLines.join("\n")) + "</code></pre>");
    return html.join("");
  }

  function addMessage(role, text, isEmpty) {
    if (!thread) return null;
    var message = document.createElement("article");
    message.className = "chat-message " + role;

    var avatar = document.createElement("div");
    avatar.className = "chat-avatar";
    avatar.textContent = role === "user" ? "U" : "P";

    var bubble = document.createElement("div");
    bubble.className = "chat-bubble" + (role === "assistant" ? " markdown-body" : "") + (isEmpty ? " empty" : "");
    if (role === "assistant") {
      bubble.innerHTML = renderMarkdown(text);
    } else {
      bubble.textContent = text;
    }

    message.appendChild(avatar);
    message.appendChild(bubble);
    thread.appendChild(message);
    scrollThread();
    return bubble;
  }

  function setOutput(text, isEmpty) {
    if (!currentAssistantBubble) {
      currentAssistantBubble = addMessage("assistant", "", true);
    }
    if (!currentAssistantBubble) return;
    currentAssistantBubble.classList.toggle("empty", Boolean(isEmpty));
    currentAssistantBubble.innerHTML = renderMarkdown(text);
    scrollThread();
  }

  function setBusy(isBusy) {
    if (!submitButton) return;
    submitButton.disabled = isBusy;
    submitButton.innerHTML = isBusy
      ? '<i data-lucide="loader-circle" aria-hidden="true"></i>'
      : '<i data-lucide="arrow-up" aria-hidden="true"></i>';
    if (window.lucide) window.lucide.createIcons();
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

  async function postJSON(path, payload) {
    var headers = {
      "Content-Type": "application/json",
    };
    var userToken = token();
    if (userToken) {
      headers["Authorization"] = (userToken.indexOf(".") !== -1 ? "Bearer " : "Token ") + userToken;
    }
    var response = await fetch(path, {
      method: "POST",
      headers: headers,
      credentials: "same-origin",
      body: JSON.stringify(payload),
    });
    var data = await response.json().catch(function () {
      return {};
    });
    if (!response.ok || data.success === false) {
      throw new Error(apiErrorMessage(data, response));
    }
    return data;
  }

  async function ensureSelectedPlan() {
    // Attempt to load from cache first to guarantee instant profile rendering
    var cachedUser = null;
    try {
      cachedUser = JSON.parse(localStorage.getItem("promptmax_user"));
    } catch (e) {}

    if (!token()) {
      planReady = true;
      populateUserProfile(null);
      return;
    }

    // Instantly display cached user information while backend fetches in the background
    if (cachedUser) {
      populateUserProfile(cachedUser);
    }

    try {
      var response = await fetch("/api/v1/auth/me/", {
        headers: { Authorization: (token().indexOf(".") !== -1 ? "Bearer " : "Token ") + token() },
        credentials: "same-origin",
      });
      var data = await response.json().catch(function () {
        return {};
      });
      
      if (response.ok && data.user) {
        localStorage.setItem("promptmax_user", JSON.stringify(data.user));
        populateUserProfile(data.user);
        
        if (!data.user.plan || !data.user.plan.plan) {
          window.location.href = "/pricing?first=1";
          return;
        }
        planReady = true;
        setStatus("");
        loadHistory();
      } else {
        // Response not OK but we have cache -> fall back to cache instead of logging out!
        if (cachedUser) {
          console.warn("Backend auth/me failed, falling back to cached session");
          planReady = true;
          loadHistory(); // attempt to load history
        } else {
          throw new Error("Session expired.");
        }
      }
    } catch (error) {
      console.error("Backend verification failed:", error);
      if (cachedUser) {
        console.warn("Retaining cached session user despite me endpoint failure");
        populateUserProfile(cachedUser);
        planReady = true;
        loadHistory();
      } else {
        localStorage.removeItem("promptmax_token");
        localStorage.removeItem("promptmax_user");
        planReady = true;
        populateUserProfile(null);
      }
    }
  }

  function populateUserProfile(user) {
    var nameEl = document.getElementById("user-profile-name");
    var emailEl = document.getElementById("user-profile-email");
    var planEl = document.getElementById("user-profile-plan");
    var avatarEl = document.getElementById("user-avatar-initial");
    var logoutBtn = document.getElementById("logout-btn");

    if (!user) {
      if (nameEl) nameEl.textContent = "Guest User";
      if (emailEl) emailEl.textContent = "Please sign in";
      if (planEl) planEl.textContent = "Free Plan";
      if (avatarEl) avatarEl.textContent = "G";
      
      // If guest, customize the logout button to be a sign-in button
      if (logoutBtn) {
        logoutBtn.innerHTML = '<i data-lucide="log-in" aria-hidden="true"></i><span>Sign In</span>';
        logoutBtn.className = "popup-item"; // keep popup-item styling
        logoutBtn.onclick = function(e) {
          e.stopPropagation();
          window.location.href = "/login";
        };
      }

      // Display prompt history call-to-action for guests instead of spinner
      var historyList = document.getElementById("history-list");
      if (historyList) {
        historyList.innerHTML = '<div class="history-empty">Please <a href="/login" style="color: #005346; font-weight: 800; text-decoration: underline;">Sign In</a> to save and view your enhancement history.</div>';
      }
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    var displayName = user.name || user.first_name || "User";
    if (nameEl) nameEl.textContent = displayName;
    if (emailEl) emailEl.textContent = user.email || "";
    if (planEl) {
      planEl.textContent = (user.plan && user.plan.label) || "Free Plan";
    }
    if (avatarEl) {
      var initial = (displayName.trim()[0] || user.email.trim()[0] || "U").toUpperCase();
      avatarEl.textContent = initial;
    }

    // Logged in: keep logout button as standard logout trigger
    if (logoutBtn) {
      logoutBtn.innerHTML = '<i data-lucide="log-out" aria-hidden="true"></i><span>Sign Out</span>';
      logoutBtn.className = "popup-item logout-btn";
      logoutBtn.onclick = function(e) {
        e.stopPropagation();
        localStorage.removeItem("promptmax_token");
        localStorage.removeItem("promptmax_user");
        window.location.href = "/";
      };
    }
    if (window.lucide) window.lucide.createIcons();
  }

  async function loadHistory() {
    var userToken = token();
    if (!userToken) return;
    try {
      var response = await fetch("/api/v1/history/", {
        headers: {
          "Authorization": (userToken.indexOf(".") !== -1 ? "Bearer " : "Token ") + userToken
        },
        credentials: "same-origin"
      });
      if (!response.ok) throw new Error("Failed to load history");
      var data = await response.json();
      renderHistoryList(data.results || []);
    } catch (error) {
      console.error("History fetch error:", error);
      var historyList = document.getElementById("history-list");
      if (historyList) {
        historyList.innerHTML = '<div class="history-error"><i data-lucide="alert-circle" aria-hidden="true"></i><span>Failed to load history</span></div>';
        if (window.lucide) window.lucide.createIcons();
      }
    }
  }

  function renderHistoryList(items) {
    var historyList = document.getElementById("history-list");
    if (!historyList) return;
    if (items.length === 0) {
      historyList.innerHTML = '<div class="history-empty">No recent enhancements</div>';
      return;
    }

    historyList.innerHTML = "";
    items.forEach(function (item) {
      var div = document.createElement("div");
      div.className = "history-item";
      div.dataset.id = item.id;

      var dateStr = "";
      try {
        var date = new Date(item.created_at);
        dateStr = date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
      } catch (e) {}

      var titleText = item.original_prompt || "";
      var displayTitle = titleText.substring(0, 30) + (titleText.length > 30 ? "..." : "");

      div.innerHTML = `
        <div class="history-item-content">
          <span class="history-item-title">${escapeHTML(displayTitle || "Untitled enhancement")}</span>
          <span class="history-item-meta">${escapeHTML(item.intent || "general")} • ${dateStr}</span>
        </div>
        <i data-lucide="chevron-right" class="history-item-arrow" aria-hidden="true"></i>
      `;

      div.addEventListener("click", function () {
        loadHistoryItemIntoChat(item);
        // On mobile, close sidebar on click
        var sidebar = document.getElementById("chat-sidebar");
        if (sidebar && window.innerWidth <= 768) {
          sidebar.classList.remove("active");
        }
      });

      historyList.appendChild(div);
    });

    if (window.lucide) window.lucide.createIcons();
  }

  function loadHistoryItemIntoChat(item) {
    if (!thread) return;
    thread.innerHTML = ""; // Clear active conversation

    // 1. User original prompt message
    addMessage("user", item.original_prompt, false);

    // 2. Assistant enhanced output reconstruction
    currentAssistantBubble = addMessage("assistant", "", false);

    var formattedOutput = "";
    if (item.enhanced_prompt) {
      formattedOutput += "### Enhanced Prompt\n\n" + item.enhanced_prompt + "\n\n";
    }

    var details = [];
    if (item.intent) details.push("- **Intent:** " + item.intent);
    if (item.domain) details.push("- **Domain:** " + item.domain);
    if (item.original_quality !== null && item.original_quality !== undefined) {
      details.push("- **Original Quality:** " + Math.round(item.original_quality * 100) + "%");
    }
    if (item.enhanced_quality !== null && item.enhanced_quality !== undefined) {
      details.push("- **Enhanced Quality:** " + Math.round(item.enhanced_quality * 100) + "%");
    }
    if (item.improvement !== null && item.improvement !== undefined) {
      details.push("- **Improvement Delta:** +" + Math.round(item.improvement * 100) + "%");
    }
    if (item.processing_time_ms) {
      details.push("- **Processing Time:** " + item.processing_time_ms + "ms");
    }

    if (details.length) {
      formattedOutput += "### Quality Analysis\n" + details.join("\n") + "\n\n";
    }

    setOutput(formattedOutput, false);
    setStatus("Loaded enhancement from history.");
  }

  function autoGrowInput() {
    if (!input) return;
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 180) + "px";
  }

  function formatAnalysis(data) {
    var lines = ["### Quality analysis"];
    lines.push("- **Intent:** " + ((data.intent && data.intent.primary) || "unknown"));
    lines.push("- **Domain:** " + ((data.domain && data.domain.primary) || "general"));
    lines.push("- **Task type:** " + (data.task_type || "unknown"));
    if (data.quality) {
      lines.push("- **Quality:** " + Math.round((data.quality.overall || 0) * 100) + "% (" + data.quality.grade + ")");
    }
    if (data.complexity) {
      lines.push("- **Complexity:** " + data.complexity.level + " | estimated steps: " + data.complexity.estimated_steps);
    }
    if (data.elements && data.elements.missing && data.elements.missing.length) {
      lines.push("");
      lines.push("### Missing elements");
      data.elements.missing.forEach(function (item) {
        lines.push("- " + item);
      });
    }
    return lines.join("\n");
  }

  function formatAbTest(data) {
    var lines = ["### A/B test result", "", "**Original prompt**", data.original || "", "", "**Recommendation**"];
    lines.push("```json");
    lines.push(JSON.stringify(data.recommendation || {}, null, 2));
    lines.push("```");
    lines.push("");
    lines.push("### Variations");
    (data.variations || []).forEach(function (variation, index) {
      lines.push("");
      lines.push("#### Variation " + (index + 1));
      if (typeof variation === "string") {
        lines.push(variation);
      } else {
        lines.push(variation.prompt || variation.text || JSON.stringify(variation, null, 2));
      }
    });
    return lines.join("\n");
  }

  ensureSelectedPlan();
  if (window.lucide) window.lucide.createIcons();

  if (modeSelect) {
    activeMode = modeSelect.value || "generate";
  }

  if (input) {
    input.addEventListener("input", autoGrowInput);
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        if (form && typeof form.requestSubmit === "function") form.requestSubmit();
      }
    });
  }

  if (modeSelect) {
    modeSelect.addEventListener("change", function () {
      activeMode = modeSelect.value || "generate";
      setStatus("");
    });
  }

  // Sidebar interactive event listeners
  var newChatBtn = document.getElementById("new-chat-btn");
  if (newChatBtn) {
    newChatBtn.addEventListener("click", function () {
      if (thread) thread.innerHTML = "";
      currentAssistantBubble = null;
      setStatus("New chat started.");
      var sidebar = document.getElementById("chat-sidebar");
      if (sidebar && window.innerWidth <= 768) {
        sidebar.classList.remove("active");
      }
    });
  }

  // Interactive user profile card popup settings menu (ChatGPT style)
  var userProfileCard = document.getElementById("user-profile-card");
  var profilePopupMenu = document.getElementById("profile-popup-menu");
  
  if (userProfileCard && profilePopupMenu) {
    userProfileCard.addEventListener("click", function (event) {
      event.stopPropagation();
      profilePopupMenu.classList.toggle("active");
      userProfileCard.classList.toggle("active");
    });

    // Close settings popup if clicked outside
    document.addEventListener("click", function (event) {
      if (!profilePopupMenu.contains(event.target) && !userProfileCard.contains(event.target)) {
        profilePopupMenu.classList.remove("active");
        userProfileCard.classList.remove("active");
      }
    });
  }

  var sidebarToggle = document.getElementById("sidebar-toggle");
  var sidebarClose = document.getElementById("sidebar-close");
  var sidebar = document.getElementById("chat-sidebar");
  var body = document.body;

  if (sidebar) {
    if (sidebarToggle) {
      sidebarToggle.addEventListener("click", function (event) {
        event.stopPropagation();
        if (window.innerWidth <= 768) {
          sidebar.classList.toggle("active");
        } else {
          body.classList.toggle("sidebar-collapsed");
        }
      });
    }

    if (sidebarClose) {
      sidebarClose.addEventListener("click", function (event) {
        event.stopPropagation();
        if (window.innerWidth <= 768) {
          sidebar.classList.remove("active");
        } else {
          body.classList.add("sidebar-collapsed");
        }
      });
    }

    // Close mobile sidebar when clicking main content
    document.addEventListener("click", function (event) {
      if (window.innerWidth <= 768 && sidebar.classList.contains("active")) {
        if (!sidebar.contains(event.target) && (!sidebarToggle || !sidebarToggle.contains(event.target))) {
          sidebar.classList.remove("active");
        }
      }
    });
  }

  if (!form) return;

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    var prompt = (input.value || "").trim();
    if (!planReady) {
      setStatus("Checking account...");
      return;
    }
    if (!prompt) {
      setStatus("Enter a prompt first.");
      return;
    }

    addMessage("user", prompt, false);
    input.value = "";
    autoGrowInput();
    currentAssistantBubble = addMessage("assistant", "Working...", true);
    setStatus("Working...");
    setBusy(true);

    try {
      var data;
      if (activeMode === "analyze") {
        data = await postJSON("/api/v1/analyze/", { prompt: prompt });
        setStatus("Analysis complete.");
        setOutput(formatAnalysis(data), false);
        // Refresh history to include new entry
        loadHistory();
        return;
      }

      if (activeMode === "abtest") {
        data = await postJSON("/api/v1/ab-test/", {
          prompt: prompt,
          model: "auto",
        });
        setStatus("A/B test complete.");
        setOutput(formatAbTest(data), false);
        // Refresh history to include new entry
        loadHistory();
        return;
      }

      data = await postJSON("/api/v1/enhance/", {
        prompt: prompt,
        enhancement_level: "expert",
        mode: activeMode === "generate" ? "generate" : "enhance",
        model: "auto",
      });
      setStatus(data.model ? "Model: " + data.model : "Done.");
      setOutput(data.enhanced || data.text || data.enhanced_prompt || JSON.stringify(data, null, 2), false);
      // Refresh history to include new entry
      loadHistory();
    } catch (error) {
      setStatus(error.message);
      setOutput("**Request failed**\n\n" + error.message + "\n\nTry again with a clearer prompt or check the model configuration.", true);
    } finally {
      setBusy(false);
    }
  });
});
