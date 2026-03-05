# -*- coding: utf-8 -*-
"""
Q라이트(Q-Light) ST45L-ETN / ST56(M)EL, ST80(M)EL-ETN 시리즈 네트워크 경광등 제어.
- 프로토콜: "Data format of Socket Program_V01(ENG).pdf" 기준.
- TCP 포트: 20000 (Ethernet Tower Lamp Library 매뉴얼).
- 10바이트: W(0x57) + Type + R,Y,G,B,W(0=Off,1=On,2=Blink) + Sound(0~5) + Spare 2바이트.
※ Library 매뉴얼은 1=Blink 2=ON 이라 다름. 동작 안 하면 LAMP_ON/LAMP_BLINK 값 맞춰볼 것.
※ 본 프로젝트는 2색만 사용: trigger_ok(녹색+사운드1), trigger_alert(빨강+사운드2). 사운드 끄려면 sound=0 전달.
"""
import socket

# 매뉴얼 기준 포트
QLIGHT_PORT = 20000
DEFAULT_TIMEOUT = 3.0

# 램프 제어값 (Socket Program 문서)
LAMP_OFF = 0
LAMP_ON = 1
LAMP_BLINK = 2

# 사운드: 0=Off, 1~5=Sound 선택 (톤이 다름)
SOUND_OFF = 0
SOUND_OK = 1      # 녹색용
SOUND_ALERT = 2   # 빨강용


def trigger_ok(host: str, port: int = QLIGHT_PORT, blink: bool = True, sound: int = SOUND_OK, timeout: float = DEFAULT_TIMEOUT) -> bool:
    """2색 사용 시 '정상/완료'용: 녹색 + 사운드(기본 1번)."""
    return write_lamp(host, port, LAMP_OFF, LAMP_OFF, LAMP_BLINK if blink else LAMP_ON, LAMP_OFF, LAMP_OFF, sound, timeout)


def trigger_alert(host: str, port: int = QLIGHT_PORT, blink: bool = True, sound: int = SOUND_ALERT, timeout: float = DEFAULT_TIMEOUT) -> bool:
    """2색 사용 시 '알림/에러'용: 빨강 + 사운드(기본 2번)."""
    return write_lamp(host, port, LAMP_BLINK if blink else LAMP_ON, LAMP_OFF, LAMP_OFF, LAMP_OFF, LAMP_OFF, sound, timeout)


def _make_write_packet(
    red: int = LAMP_OFF,
    yellow: int = LAMP_OFF,
    green: int = LAMP_OFF,
    blue: int = LAMP_OFF,
    white: int = LAMP_OFF,
    sound: int = SOUND_OFF,
    sound_type: int = 0,
) -> bytes:
    """
    10바이트 Write 패킷 생성.
    sound_type: 0=5 sound model, 0~4=25 sound model 그룹.
    """
    return bytes([
        0x57,  # 'W' Write
        sound_type & 0xFF,
        red & 0xFF,
        yellow & 0xFF,
        green & 0xFF,
        blue & 0xFF,
        white & 0xFF,
        sound & 0xFF,
        0x00,
        0x00,
    ])


def write_lamp(
    host: str,
    port: int = QLIGHT_PORT,
    red: int = LAMP_OFF,
    yellow: int = LAMP_OFF,
    green: int = LAMP_OFF,
    blue: int = LAMP_OFF,
    white: int = LAMP_OFF,
    sound: int = SOUND_OFF,
    timeout: float = DEFAULT_TIMEOUT,
) -> bool:
    """
    경광등 램프/사운드 제어 (10바이트 TCP 전송).
    램프: 0=Off, 1=On, 2=Blink. sound: 0=Off, 1~5=Sound 선택.
    """
    try:
        payload = _make_write_packet(red, yellow, green, blue, white, sound)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.sendall(payload)
        s.close()
        return True
    except Exception:
        return False


def trigger(
    host: str,
    port: int = QLIGHT_PORT,
    lamp: str = "green",
    blink: bool = True,
    sound: int = 0,
    timeout: float = DEFAULT_TIMEOUT,
) -> bool:
    """
    식사 인증 등 알림용 트리거: 지정 램프를 켜거나 깜빡임.
    lamp: 'red','yellow','green','blue','white'. blink=True면 Blink, False면 On.
    """
    r = y = g = b = w = LAMP_OFF
    v = LAMP_BLINK if blink else LAMP_ON
    if lamp == "red":
        r = v
    elif lamp == "yellow":
        y = v
    elif lamp == "green":
        g = v
    elif lamp == "blue":
        b = v
    elif lamp == "white":
        w = v
    else:
        g = v  # 기본 녹색
    return write_lamp(host, port, r, y, g, b, w, sound, timeout)


def trigger_off(
    host: str,
    port: int = QLIGHT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
) -> bool:
    """모든 램프·사운드 끄기."""
    return write_lamp(host, port, LAMP_OFF, LAMP_OFF, LAMP_OFF, LAMP_OFF, LAMP_OFF, SOUND_OFF, timeout)
