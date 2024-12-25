 // Tải dữ liệu người dùng đã đăng nhập
    document.addEventListener("DOMContentLoaded", () => {
        fetch('/api/current_user') // API giả định trả về thông tin người dùng đã đăng nhập
            .then(response => response.json())
            .then(user => {
                if (user) {
                    document.getElementById('full_name').value = user.full_name || '';
                    document.getElementById('phone_number').value = user.phone_number || '';
                    document.getElementById('email').value = user.email || '';
                    document.getElementById('identification_code').value = user.identification_code || '';
                }
            })
            .catch(error => {
                console.error('Lỗi khi tải dữ liệu người dùng:', error);
            });
    });