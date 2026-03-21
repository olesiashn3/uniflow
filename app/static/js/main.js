document.addEventListener('DOMContentLoaded', function () {

    // Alerts auto-hide
    document.querySelectorAll('.alert').forEach(function (alert) {
        setTimeout(function () {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(function () { alert.remove(); }, 500);
        }, 4000);
    });

    // Carousel
    let current = 0;
    const cards = document.querySelectorAll('.carousel-card');
    const dots = document.querySelectorAll('.dot');
    if (cards.length) {
        setInterval(function () {
            goToSlide((current + 1) % cards.length);
        }, 3500);
    }

    window.goToSlide = function (index) {
        cards[current].classList.remove('active');
        dots[current].classList.remove('active');
        current = index;
        cards[current].classList.add('active');
        dots[current].classList.add('active');
    };

    // Clear search
    window.clearSearch = function () {
        document.getElementById('searchInput').value = '';
        document.getElementById('filterForm').submit();
    };
});