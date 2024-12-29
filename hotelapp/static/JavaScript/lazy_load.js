document.addEventListener('DOMContentLoaded', () => {
    // Lazy load hình ảnh
    const lazyImages = document.querySelectorAll('.lazy');

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src; // Tải ảnh khi nó vào viewport
                img.classList.remove('lazy');
                observer.unobserve(img);
            }
        });
    });

    lazyImages.forEach(img => observer.observe(img));
});

// Hàm Play Video
function playVideo(id) {
    const video = document.getElementById(`video${id}`);
    const overlayImage = document.getElementById(`overlayImage${id}`);
    const playButton = document.getElementById(`playButton${id}`);

    video.setAttribute('src', video.dataset.src);
    video.style.display = 'block';
    video.style.opacity = 1;

    overlayImage.style.display = 'none';
    playButton.style.display = 'none';
}

// Lazy load thêm nội dung quảng cáo khi scroll
let offset = 5; // Số phần tử đã tải
const limit = 5;

window.addEventListener('scroll', () => {
    if (window.innerHeight + window.scrollY >= document.body.offsetHeight) {
        fetch(`/api/load-content?offset=${offset}&limit=${limit}`)
            .then(response => response.json())
            .then(data => {
                const carouselInner = document.querySelector('.carousel-inner');
                data.forEach(ad => {
                    const div = document.createElement('div');
                    div.className = 'carousel-item';
                    div.innerHTML = `<img data-src="${ad.url}" class="d-block w-100 carousel-img lazy" alt="${ad.alt}">`;
                    carouselInner.appendChild(div);
                });
                offset += limit;
            })
            .catch(error => console.error(error));
    }
});
