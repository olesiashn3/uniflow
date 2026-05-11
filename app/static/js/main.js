document.addEventListener('DOMContentLoaded', function () {

    document.querySelectorAll('.alert').forEach(function (alert) {
        setTimeout(function () {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(function () { alert.remove(); }, 500);
        }, 4000);
    });

    let current = 0;
    const cards = document.querySelectorAll('.carousel-card');
    const dots = document.querySelectorAll('.dot');

    if (cards.length) {
        setInterval(function () {
            goToSlide((current + 1) % cards.length);
        }, 3500);
    }

    window.goToSlide = function (index) {
        if (!cards.length) return;
        cards[current].classList.remove('active');
        dots[current].classList.remove('active');
        current = index;
        cards[current].classList.add('active');
        dots[current].classList.add('active');
    };

    window.clearSearch = function () {
        document.getElementById('searchInput').value = '';
        document.getElementById('filterForm').submit();
    };

    const favForms = document.querySelectorAll('.heart-form');
    favForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const btn = form.querySelector('.heart-btn');
            const url = form.getAttribute('action');

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.is_favorite) {
                    btn.classList.add('active');
                    btn.innerHTML = '<i class="ph-fill ph-heart"></i>';
                } else {
                    btn.classList.remove('active');
                    btn.innerHTML = '<i class="ph ph-heart"></i>';
                }
            })
            .catch(error => console.error('Favorite toggle failed:', error));
        });
    });
});
