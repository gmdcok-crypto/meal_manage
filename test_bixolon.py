# -*- coding: utf-8 -*-
"""빅솔론 SRP-350III: 텍스트 먼저 → 다음 식권용 이미지 → 컷. 실행: python test_bixolon.py"""
from datetime import datetime
from bixolon_print import test_connection, print_image_only

# 프린터 IP (같은 네트워크 대역에 맞게 수정)
PRINTER_IP = "192.168.0.107"
PORT = 9100
# NV 메모리 이미지 번호 (1~255)
STORED_IMAGE_NUMBER = 1

if __name__ == "__main__":
    print(f"연결 시도: {PRINTER_IP}:{PORT}")
    if not test_connection(PRINTER_IP, PORT):
        print("포트 연결 실패 (방화벽, 프린터 전원/네트워크, 포트 9100 확인)")
        exit(1)
    print("포트 연결: OK")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ok = print_image_only(
        PRINTER_IP,
        PORT,
        stored_image_number=STORED_IMAGE_NUMBER,
        emp_no="12345",
        name="테스트",
        date_time_str=now,
        meal_type="중식",
    )
    print("출력: OK" if ok else "출력 실패")
