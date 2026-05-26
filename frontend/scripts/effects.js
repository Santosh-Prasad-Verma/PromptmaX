/* ═══════════════════════════════════════════════════
   PROMPTX SHARED ANIMATIONS & EFFECTS — OPTIMIZED
   ═══════════════════════════════════════════════════ */
(function () {
  /* ── Canvas Particles (lightweight, no mouse) ── */
  function setupParticles() {
    var canvas = document.getElementById('fc-canvas-particles');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var PARTICLES = 20;
    var CONNECTION_DIST = 100;
    var particles = [];

    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    for (var i = 0; i < PARTICLES; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.2,
        vy: (Math.random() - 0.5) * 0.2,
        radius: 0.6 + Math.random() * 1.2,
        alpha: 0.08 + Math.random() * 0.2,
      });
    }

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (var i = 0; i < PARTICLES; i++) {
        var p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < -10) p.x = canvas.width + 10;
        if (p.x > canvas.width + 10) p.x = -10;
        if (p.y < -10) p.y = canvas.height + 10;
        if (p.y > canvas.height + 10) p.y = -10;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 255, ' + p.alpha + ')';
        ctx.fill();

        for (var j = i + 1; j < PARTICLES; j++) {
          var q = particles[j];
          var cdx = p.x - q.x;
          var cdy = p.y - q.y;
          var cdist = Math.sqrt(cdx * cdx + cdy * cdy);
          if (cdist < CONNECTION_DIST) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.strokeStyle = 'rgba(255, 255, 255, ' + (0.04 * (1 - cdist / CONNECTION_DIST)) + ')';
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(draw);
    }
    draw();
  }

  /* ── GSAP Animations ── */
  function setupGSAP() {
    gsap.registerPlugin(ScrollTrigger);

    var revealEls = document.querySelectorAll('.reveal');
    if (revealEls.length) {
      gsap.utils.toArray('.reveal').forEach(function (el) {
        gsap.fromTo(el, { opacity: 0, y: 30 }, {
          opacity: 1, y: 0,
          duration: 0.6,
          ease: 'power2.out',
          scrollTrigger: { trigger: el, start: 'top 88%', toggleActions: 'play none none reverse' }
        });
      });
    }

    var pricingCards = document.querySelectorAll('.pricing-card');
    if (pricingCards.length > 0) {
      gsap.fromTo('.pricing-card', { opacity: 0, y: 20 }, {
        opacity: 1, y: 0,
        stagger: 0.1,
        duration: 0.5,
        ease: 'power2.out',
        scrollTrigger: { trigger: '.pricing-grid', start: 'top 85%' }
      });
    }

    var orb1 = document.querySelector('.glow-orb-1');
    var orb2 = document.querySelector('.glow-orb-2');
    if (orb1) {
      gsap.to('.glow-orb-1', { y: -60, scrollTrigger: { trigger: 'body', start: 'top top', end: 'bottom bottom', scrub: 3 } });
    }
    if (orb2) {
      gsap.to('.glow-orb-2', { y: 40, scrollTrigger: { trigger: 'body', start: 'top top', end: 'bottom bottom', scrub: 4 } });
    }
  }

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    setupParticles();
    if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
      setupGSAP();
      window.addEventListener('resize', function () { ScrollTrigger.refresh(); });
    }
  });
})();
