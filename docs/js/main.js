document.addEventListener('DOMContentLoaded', () => {
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');
    if (hamburger && navLinks) {
        hamburger.addEventListener('click', () => {
            const expanded = navLinks.classList.toggle('active');
            hamburger.setAttribute('aria-expanded', String(expanded));
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
                hamburger.setAttribute('aria-expanded', 'false');
                hamburger.focus();
            }
        });
    }

    document.querySelectorAll('.copy-btn').forEach(button => {
        button.addEventListener('click', async () => {
            const code = button.closest('.code-block').querySelector('pre code');
            button.disabled = true;
            try {
                await navigator.clipboard.writeText(code.textContent);
                button.textContent = 'Copied!';
            } catch {
                button.textContent = 'Copy failed';
            } finally {
                setTimeout(() => {
                    button.textContent = 'Copy';
                    button.disabled = false;
                }, 2000);
            }
        });
    });
});
