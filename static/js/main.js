const navToggle = document.querySelector('.nav-toggle');
const navMenu = document.querySelector('.nav-menu');

if (navToggle && navMenu) {
    const closeMenu = () => {
        navToggle.setAttribute('aria-expanded', 'false');
        navToggle.setAttribute('aria-label', 'Open Navigation Bar');
        navMenu.classList.remove('is-open');
    };

    navToggle.addEventListener('click', () => {
        const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';
        navToggle.setAttribute('aria-expanded', String(!isExpanded));
        navToggle.setAttribute('aria-label', isExpanded ? 'Open Navigation Bar' : 'Close Navigation Bar');
        navMenu.classList.toggle('is-open', !isExpanded);
    });

    navMenu.addEventListener('click', (event) => {
        if (event.target.closest('a')) closeMenu();
    });

    document.addEventListener('click', (event) => {
        if (!navMenu.contains(event.target) && !navToggle.contains(event.target)) closeMenu();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && navToggle.getAttribute('aria-expanded') === 'true') {
            closeMenu();
            navToggle.focus();
        }
    });

    window.addEventListener('resize', () => {
        if (window.matchMedia('(min-width: 769px)').matches) closeMenu();
    });
}
