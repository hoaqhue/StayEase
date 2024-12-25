function playVideo(videoId) {
    // Lấy các phần tử DOM liên quan đến video cụ thể
    const overlayImage = document.getElementById(`overlayImage${videoId}`);
    const playButton = document.getElementById(`playButton${videoId}`);
    const video = document.getElementById(`video${videoId}`);

    // Đảm bảo tất cả các phần tử tồn tại trước khi xử lý
    if (!overlayImage || !playButton || !video) {
        console.error("Một hoặc nhiều phần tử DOM không tồn tại.");
        return;
    }

    // Ẩn ảnh và nút bấm với hiệu ứng mờ
    overlayImage.style.opacity = '0';
    playButton.style.opacity = '0';

    // Hiển thị video sau khi ảnh và nút mờ đi
    setTimeout(() => {
        overlayImage.style.display = 'none';
        playButton.style.display = 'none';
        video.style.display = 'block';
        video.style.opacity = '1';

        // Phát video bằng cách gửi lệnh qua API của YouTube
        video.contentWindow.postMessage('{"event":"command","func":"playVideo","args":""}', '*');
    }, 500);
}
