import numpy as np
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
import os

def generate_fibonacci_sequence(num_pins, max_steps):
    """
    피보나치 수열을 기반으로 핀 번호(인덱스)를 생성합니다.
    F(n) = (F(n-1) + F(n-2)) % num_pins
    """
    seq = [0, 1]
    for _ in range(max_steps - 2):
        next_pin = (seq[-1] + seq[-2]) % num_pins
        seq.append(next_pin)
    return seq

def draw_string_art(sequence, num_pins, img_size=1000, line_opacity=100):
    """
    생성된 핀 시퀀스를 기반으로 스트링 아트를 그립니다.
    """
    # 캔버스 생성 (흰색 배경)
    img = Image.new("RGB", (img_size, img_size), "white")
    draw = ImageDraw.Draw(img, "RGBA")
    
    # 핀의 좌표 계산 (원형 배치)
    center = img_size / 2
    radius = (img_size / 2) * 0.95 # 여백 약간
    
    pin_coords = []
    for i in range(num_pins):
        angle = 2 * np.pi * i / num_pins - (np.pi / 2) # 위쪽(12시)부터 시작
        x = center + radius * np.cos(angle)
        y = center + radius * np.sin(angle)
        pin_coords.append((x, y))
        
    # 선 그리기
    for i in range(len(sequence) - 1):
        p1 = sequence[i]
        p2 = sequence[i+1]
        x1, y1 = pin_coords[p1]
        x2, y2 = pin_coords[p2]
        
        # 선 색상 (검정색, 투명도 조절)
        draw.line([(x1, y1), (x2, y2)], fill=(0, 0, 0, line_opacity), width=1)
        
    return img

def main():
    NUM_PINS = 300 
    MAX_STRINGS = 2000 # 피보나치 수열을 생성할 횟수
    
    print("피보나치 스트링 아트 생성 시작...")
    
    # 1. 시퀀스 생성
    seq = generate_fibonacci_sequence(NUM_PINS, MAX_STRINGS)
    
    # 2. 이미지 그리기
    img = draw_string_art(seq, NUM_PINS, img_size=1200, line_opacity=50)
    
    # 3. 결과 저장 및 출력
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "fibonacci_string_art.png")
    img.save(output_path)
    
    print(f"완료! 결과 이미지가 저장되었습니다: {output_path}")
    
    # 화면에 보여주기
    plt.figure(figsize=(8, 8))
    plt.imshow(img)
    plt.axis('off')
    plt.title(f"Fibonacci String Art (Pins: {NUM_PINS}, Strings: {len(seq)})")
    plt.show()

if __name__ == "__main__":
    main()
