document.addEventListener("DOMContentLoaded", function () {
  var year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();

  function icon(name) {
    var rawSvg = "";
    if (name === "github") {
      rawSvg = '<svg class="lucide lucide-github" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 18px; height: 18px; flex: 0 0 auto;"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"></path><path d="M9 18c-4.51 2-5-2-7-2"></path></svg>';
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

  function addGithubButtons() {
    document.querySelectorAll(".nav-actions").forEach(function (navActions) {
      if (navActions.querySelector(".github-btn")) return;
      var githubBtn = buildGithubButton();
      if (navActions.firstChild) {
        navActions.insertBefore(githubBtn, navActions.firstChild);
      } else {
        navActions.appendChild(githubBtn);
      }
    });
  }

  addGithubButtons();
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
