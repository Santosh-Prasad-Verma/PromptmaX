document.addEventListener("DOMContentLoaded", function () {
  var year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();

  function getStoredUser() {
    try {
      return JSON.parse(localStorage.getItem("promptmax_user") || "null");
    } catch (error) {
      return null;
    }
  }

  function getDisplayName(user) {
    if (!user) return "";
    var name = (user.name || "").trim();
    if (name) return name;
    var email = (user.email || "").trim();
    return email ? email.split("@")[0] : "User";
  }

  function icon(name) {
    var rawSvg = "";
    if (name === "github") {
      rawSvg = '<svg class="lucide lucide-github" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 18px; height: 18px; flex: 0 0 auto;"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"></path><path d="M9 18c-4.51 2-5-2-7-2"></path></svg>';
    } else if (name === "circle-user-round") {
      rawSvg = '<svg class="lucide lucide-circle-user-round" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 18px; height: 18px; flex: 0 0 auto;"><path d="M18 20a6 6 0 0 0-12 0"></path><circle cx="12" cy="10" r="4"></circle><circle cx="12" cy="12" r="10"></circle></svg>';
    } else if (name === "sparkles") {
      rawSvg = '<svg class="lucide lucide-sparkles" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 18px; height: 18px; flex: 0 0 auto;"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"></path><path d="m5 3 1 2.5L8.5 6 6 7 5 9.5 4 7 1.5 6 4 5 5 3Z"></path><path d="m19 17 1 2.5 2.5.5-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1 1-2.5Z"></path></svg>';
    } else if (name === "menu") {
      rawSvg = '<svg class="lucide lucide-menu" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 20px; height: 20px; flex: 0 0 auto;"><line x1="4" x2="20" y1="12" y2="12"></line><line x1="4" x2="20" y1="6" y2="6"></line><line x1="4" x2="20" y1="18" y2="18"></line></svg>';
    }
    
    if (rawSvg) {
      var div = document.createElement("div");
      div.innerHTML = rawSvg;
      var svgNode = div.firstChild;
      svgNode.setAttribute("aria-hidden", "true");
      return svgNode;
    }
    
    var node = document.createElement("i");
    node.setAttribute("data-lucide", name);
    node.setAttribute("aria-hidden", "true");
    return node;
  }

  function buildLink(className, href, iconName, text) {
    var link = document.createElement("a");
    link.className = className;
    link.href = href;
    if (iconName) link.appendChild(icon(iconName));
    if (className === "user-chip") {
      var span = document.createElement("span");
      span.className = "user-chip-text";
      span.textContent = text;
      link.appendChild(span);
    } else {
      link.appendChild(document.createTextNode(text));
    }
    return link;
  }

  function buildGithubButton() {
    var link = document.createElement("a");
    link.className = "button secondary github-btn";
    link.href = "https://github.com/Santosh-Prasad-Verma/PromptX";
    link.target = "_blank";
    link.rel = "noreferrer";
    link.appendChild(icon("github"));
    
    var span = document.createElement("span");
    span.id = "github-stars";
    span.className = "github-stars-count";
    var cachedStars = sessionStorage.getItem("github_stars");
    span.textContent = cachedStars ? "★ " + cachedStars : "★ Star";
    link.appendChild(span);
    
    return link;
  }

  function fetchAndCacheGithubStars() {
    fetch("https://api.github.com/repos/Santosh-Prasad-Verma/PromptX")
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (data && typeof data.stargazers_count === "number") {
          var count = data.stargazers_count;
          sessionStorage.setItem("github_stars", String(count));
          document.querySelectorAll(".github-stars-count").forEach(function (span) {
            span.textContent = "★ " + count;
          });
        }
      })
      .catch(function (err) {
        console.warn("Failed to fetch GitHub stars:", err);
      });
  }

  function updateAuthenticatedNav() {
    var token = localStorage.getItem("promptmax_token");
    var user = getStoredUser();
    
    if (!token || !user) {
      document.querySelectorAll(".nav-actions").forEach(function (navActions) {
        if (!navActions.querySelector(".github-btn")) {
          var githubBtn = buildGithubButton();
          if (navActions.firstChild) {
            navActions.insertBefore(githubBtn, navActions.firstChild);
          } else {
            navActions.appendChild(githubBtn);
          }
        }
      });
      return;
    }

    document.querySelectorAll(".nav-actions").forEach(function (navActions) {
      navActions.textContent = "";

      var githubBtn = buildGithubButton();
      var launch = buildLink("button primary", "/chat", "sparkles", "Launch PromptmaX");
      var menu = document.createElement("button");
      menu.className = "menu-button";
      menu.id = "menu-button";
      menu.type = "button";
      menu.setAttribute("aria-label", "Open menu");
      menu.setAttribute("aria-controls", "nav-links");
      menu.setAttribute("aria-expanded", "false");
      menu.appendChild(icon("menu"));

      navActions.appendChild(githubBtn);
      navActions.appendChild(chip);
      navActions.appendChild(plan);
      navActions.appendChild(launch);
      navActions.appendChild(menu);
    });

    if ((window.location.pathname === "/" || window.location.pathname === "/index.html")) {
      var banner = document.querySelector(".top-banner strong");
      if (banner) banner.textContent = "Welcome back, " + getDisplayName(user) + ". Continue your PromptmaX workspace.";
    }
  }

  updateAuthenticatedNav();
  fetchAndCacheGithubStars();

  var menuButton = document.getElementById("menu-button");
  var navLinks = document.getElementById("nav-links");
  if (menuButton && navLinks) {
    menuButton.addEventListener("click", function () {
      var open = navLinks.classList.toggle("open");
      menuButton.setAttribute("aria-expanded", String(open));
    });
  }

  var revealItems = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    revealItems.forEach(function (item) {
      observer.observe(item);
    });
  } else {
    revealItems.forEach(function (item) {
      item.classList.add("visible");
    });
  }

  if (window.lucide) {
    window.lucide.createIcons();
  }
});
