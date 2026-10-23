function updateTranslations() {
    const lang = localStorage.getItem('lang') || 'en';
    const langSelector = document.getElementById('langSwitch');

    if (langSelector) {
        langSelector.value = lang;
    }

    fetch(`locales/${lang}.json`)
        .then(res => res.json())
        .then(translations => {
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (translations[key]) {
                    el.innerText = translations[key];
                }
            });

            document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
                const key = el.getAttribute('data-i18n-placeholder');
                if (translations[key]) {
                    el.placeholder = translations[key];
                }
            });

            // Update HTML dir for Arabic
            document.documentElement.lang = lang;
            document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
        })
        .catch(err => console.error('Translation error:', err));
}

// Initialize language switcher
document.addEventListener('DOMContentLoaded', () => {
    const langSwitch = document.getElementById('langSwitch');
    if (langSwitch) {
        langSwitch.addEventListener('change', (e) => {
            localStorage.setItem('lang', e.target.value);
            updateTranslations();
        });
    }
    updateTranslations();
});

// Export to window for app.js to use
window.updateTranslations = updateTranslations;
