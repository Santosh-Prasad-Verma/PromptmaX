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
      var chip = buildLink("user-chip", "/pricing", "circle-user-round", getDisplayName(user));
      var plan = buildLink("button secondary", "/pricing", null, "Plan");
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
