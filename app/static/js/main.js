document.addEventListener('DOMContentLoaded', function () {

    // 1. Автоматичне приховування повідомлень (Alerts auto-hide)
    document.querySelectorAll('.alert').forEach(function (alert) {
        setTimeout(function () {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(function () { alert.remove(); }, 500);
        }, 4000);
    });

    // 2. Логіка Каруселі (Carousel)
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

    // 3. Очищення пошуку (Clear search)
    window.clearSearch = function () {
        document.getElementById('searchInput').value = '';
        document.getElementById('filterForm').submit();
    };

    // 4. AJAX для кнопки "Вибране" (сердечко без перезавантаження)
    const favForms = document.querySelectorAll('.heart-form');
    favForms.forEach(form => {
        form.addEventListener('submit', function (e) {
            e.preventDefault(); // Зупиняємо перезавантаження сторінки

            const btn = form.querySelector('.heart-btn');
            const url = form.getAttribute('action');

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest' // Кажемо Flask, що це AJAX
                }
            })
            .then(response => response.json())
            .then(data => {
                // Змінюємо іконку залежно від того, що повернув сервер
                if (data.is_favorite) {
                    btn.classList.add('active');
                    btn.innerHTML = '<i class="ph-fill ph-heart"></i>'; // Зафарбоване серце
                } else {
                    btn.classList.remove('active');
                    btn.innerHTML = '<i class="ph ph-heart"></i>'; // Пусте серце
                }
            })
            .catch(error => console.error('Помилка додавання у вибране:', error));
        });
    });
});