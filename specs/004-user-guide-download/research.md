# Nghiên cứu đóng gói User Guide

## File static

Chọn public để Vite đưa nguyên HTML vào dist, không tải guide cùng JS bundle. Không chọn API vì tài liệu cố định, không cần quyền mới hoặc backend. Không trỏ trực tiếp outputs vì build frontend chưa đóng gói nơi này.

## Đồng bộ và vị trí nút

Giữ artifact outputs và bản phát hành public; builder ghi cùng chuỗi vào hai nơi. QA so sánh source/public/dist/download để tránh lệch bản. Dùng ActionLink và URL theo BASE_URL tại workspace-bar; wrap ở mobile, giữ sáu menu.

## Rà soát độc lập theo speckit-plan

Agent nghiên cứu read-only nhất trí lựa chọn; nhắc .dockerignore loại docs, Docker cần COPY public, Nginx có SPA fallback nên HTTP200 chưa đủ. Đã đưa vào plan/contract. Không còn điểm cần hỏi hoặc dependency cần tra web.
