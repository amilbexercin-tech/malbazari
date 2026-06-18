/* HeyvanBazar Admin JS */

function toggleSidebar() {
  const sidebar = document.getElementById('adminSidebar');
  if (sidebar) sidebar.classList.toggle('open');
}

// Close sidebar when clicking outside on mobile
document.addEventListener('click', e => {
  const sidebar = document.getElementById('adminSidebar');
  const toggle = document.querySelector('.topbar-toggle');
  if (sidebar && window.innerWidth < 900) {
    if (!sidebar.contains(e.target) && !toggle?.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  }
});

// Auto-dismiss flash
document.querySelectorAll('.admin-flash').forEach(el => {
  setTimeout(() => el.remove(), 5000);
});

// Confirm dangerous actions
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', e => {
    if (!confirm(el.dataset.confirm)) e.preventDefault();
  });
});
