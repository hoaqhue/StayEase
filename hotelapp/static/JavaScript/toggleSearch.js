// Kiểm tra nếu trang hiện tại là 'index.html'
if (window.location.pathname === '/' || window.location.pathname === '/index.html') {
    // Lấy phần tử thanh tìm kiếm và nút
    const searchBar = document.querySelector('.fixed-search');
    const body = document.body;

    // Đặt giá trị padding-top ban đầu
    body.style.paddingTop = '300px';

    // Khi cuộn trang, kiểm tra vị trí và ẩn/hiện thanh tìm kiếm
    let lastScrollTop = 0;
    window.addEventListener('scroll', function() {
        let currentScroll = window.pageYOffset || document.documentElement.scrollTop;

        // Nếu cuộn xuống và thanh tìm kiếm không ẩn, ẩn thanh tìm kiếm
        if (currentScroll > lastScrollTop && !searchBar.classList.contains('hide')) {
            searchBar.classList.add('hide');
            body.style.paddingTop = '56px'; // Giảm khoảng cách khi thanh tìm kiếm ẩn
        }
        // Nếu cuộn lên và thanh tìm kiếm đang ẩn, hiện lại thanh tìm kiếm
        else if (currentScroll < lastScrollTop && searchBar.classList.contains('hide')) {
            searchBar.classList.remove('hide');
            body.style.paddingTop = '300px'; // Tăng khoảng cách khi thanh tìm kiếm hiện
        }

        lastScrollTop = currentScroll <= 0 ? 0 : currentScroll; // Đảm bảo không bị âm
    });
}
