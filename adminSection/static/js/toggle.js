const toggleSidebarBtn = document.getElementById('toggle-sidebar');
const sidebar = document.getElementById('sidebar');
const mainContent = document.getElementById('main-content');
const closeBtn = document.querySelector('.fa-close');

// Sidebar toggle button (hamburger)
toggleSidebarBtn.addEventListener('click', () => {
  // If sidebar is hidden, show it
  if (sidebar.classList.contains('hidden')) {
    sidebar.classList.remove('hidden');
  } else {
    sidebar.classList.toggle('collapsed');
    mainContent.classList.toggle('collapsed');
    toggleSidebarBtn.classList.toggle('collapsed');
  }
});

// Close (X) button inside sidebar
closeBtn.addEventListener('click', () => {
  sidebar.classList.add('hidden');
});
