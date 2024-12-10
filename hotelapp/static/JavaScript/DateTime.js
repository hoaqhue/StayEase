
   function updateCheckoutMinDate() {
    const checkinDate = document.getElementById('check_in_date');
    const checkoutDate = document.getElementById('check_out_date');

    // Đặt ngày tối thiểu cho check-in là hôm nay
    const today = new Date();
    checkinDate.min = today.toISOString().split('T')[0];

    if (checkinDate.value) {
        // Lấy ngày check-in từ input
        const minCheckoutDate = new Date(checkinDate.value);

        // Tăng ngày checkout tối thiểu lên 1 ngày
        minCheckoutDate.setDate(minCheckoutDate.getDate() + 1);

        // Cập nhật giá trị tối thiểu cho ngày checkout
        checkoutDate.min = minCheckoutDate.toISOString().split('T')[0];

        // Xóa giá trị checkout cũ nếu không hợp lệ
        if (new Date(checkoutDate.value) <= new Date(checkinDate.value)) {
            checkoutDate.value = '';
        }
    } else {
        // Reset ngày tối thiểu cho check-out nếu check-in chưa chọn
        checkoutDate.min = '';
    }
}

