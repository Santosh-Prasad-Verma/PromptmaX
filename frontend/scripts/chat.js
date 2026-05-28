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
    var response = await fetch(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Token " + token(),
      },
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
    try {
      var response = await fetch("/api/v1/auth/me/", {
        headers: { Authorization: "Token " + token() },
        credentials: "same-origin",
      });
      var data = await response.json().catch(function () {
        return {};
      });
      if (!response.ok || !data.user) throw new Error("Session expired.");
      localStorage.setItem("promptmax_user", JSON.stringify(data.user));
      if (!data.user.plan || !data.user.plan.plan) {
        window.location.href = "/pricing?first=1";
        return;
      }
      planReady = true;
      setStatus("");
    } catch (error) {
      localStorage.removeItem("promptmax_token");
      localStorage.removeItem("promptmax_user");
      window.location.href = "/login";
    }
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

  if (!token()) {
    window.location.href = "/login";
    return;
  }

  ensureSelectedPlan();

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
        return;
      }

      if (activeMode === "abtest") {
        data = await postJSON("/api/v1/ab-test/", {
          prompt: prompt,
          model: "auto",
        });
        setStatus("A/B test complete.");
        setOutput(formatAbTest(data), false);
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
    } catch (error) {
      setStatus(error.message);
      setOutput("**Request failed**\n\n" + error.message + "\n\nTry again with a clearer prompt or check the model configuration.", true);
    } finally {
      setBusy(false);
    }
  });
});
