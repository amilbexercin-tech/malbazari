/* HeyvanBazar — Main JS */

// ── Navbar scroll effect ──
const navbar = document.getElementById('navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    navbar.style.boxShadow = window.scrollY > 10
      ? '0 4px 30px rgba(0,0,0,0.25)'
      : '0 2px 20px rgba(0,0,0,0.2)';
  });
}

// ── User menu dropdown ──
function toggleUserMenu() {
  const dd = document.getElementById('userDropdown');
  if (dd) dd.classList.toggle('open');
}
document.addEventListener('click', e => {
  const menu = document.getElementById('userMenu');
  const dd = document.getElementById('userDropdown');
  if (menu && dd && !menu.contains(e.target)) dd.classList.remove('open');
});

// ── Mobile menu ──
function toggleMobileMenu() {
  const menu = document.getElementById('mobileMenu');
  const btn = document.getElementById('hamburger');
  if (!menu) return;
  const isOpen = menu.classList.toggle('open');
  btn.classList.toggle('open', isOpen);
}

// ── 3D Card tilt effect ──
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.cat-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      card.style.transform = `perspective(1000px) rotateY(${x * 8}deg) rotateX(${-y * 5}deg) translateY(-6px)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) translateY(0)';
    });
  });

  // Listing card subtle tilt
  document.querySelectorAll('.listing-card').forEach(card => {
    card.addEventListener('mousemove', e => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      card.style.transform = `translateY(-4px) rotateY(${x * 3}deg) rotateX(${-y * 2}deg)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });

  // ── Scroll reveal animations ──
  const observerOptions = {threshold: 0.1, rootMargin: '0px 0px -40px 0px'};
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  document.querySelectorAll('.listing-card, .cat-card, .how-card, .stat-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity .5s ease, transform .5s ease';
    observer.observe(el);
  });

  // ── Auto-dismiss flash messages ──
  document.querySelectorAll('.flash').forEach(flash => {
    setTimeout(() => {
      flash.style.animation = 'slideIn .3s ease reverse';
      setTimeout(() => flash.remove(), 300);
    }, 4000);
  });

  // ── Number counter animation ──
  document.querySelectorAll('.stat-num').forEach(el => {
    const target = parseInt(el.textContent.replace(/\D/g, ''));
    if (isNaN(target) || target === 0) return;
    const duration = 1200;
    const start = performance.now();
    const suffix = el.textContent.replace(/[\d,]/g, '').trim();
    const obs = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting) {
        const animate = now => {
          const progress = Math.min((now - start) / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          el.textContent = Math.floor(eased * target) + (suffix ? ' ' + suffix : '');
          if (progress < 1) requestAnimationFrame(animate);
          else el.textContent = target + (suffix ? ' ' + suffix : '');
        };
        requestAnimationFrame(animate);
        obs.disconnect();
      }
    }, {threshold: 0.5});
    obs.observe(el);
  });
});

// ── Smooth anchor scroll ──
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({behavior: 'smooth', block: 'start'});
    }
  });
});
