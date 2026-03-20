"""
AKS 소수 판별 알고리즘 (Agrawal-Kayal-Saxena Primality Test)

2002년 Manindra Agrawal, Neeraj Kayal, Nitin Saxena가 발표한
최초의 결정적(deterministic) 다항 시간 소수 판별 알고리즘입니다.

참고: Agrawal, M., Kayal, N., & Saxena, N. (2004).
      PRIMES is in P. Annals of Mathematics, 160(2), 781-793.
"""

import math
from math import gcd


def is_perfect_power(n: int) -> bool:
    """
    n이 완전 거듭제곱수(perfect power)인지 확인합니다.
    즉, n = a^b (a >= 2, b >= 2)를 만족하는 정수 a, b가 존재하는지 확인합니다.

    Args:
        n: 확인할 양의 정수 (n >= 2)

    Returns:
        n이 완전 거듭제곱수이면 True, 아니면 False
    """
    if n < 4:
        return False
    # b의 범위: 2 <= b <= log2(n)
    max_b = int(math.log2(n)) + 1
    for b in range(2, max_b + 1):
        # a = n^(1/b)에 가까운 정수를 탐색
        a = round(n ** (1.0 / b))
        for candidate in [a - 1, a, a + 1]:
            if candidate >= 2 and candidate ** b == n:
                return True
    return False


def multiplicative_order(n: int, r: int) -> int:
    """
    n의 r에 대한 곱셈적 위수(multiplicative order) ord_r(n)을 계산합니다.
    ord_r(n)은 n^k ≡ 1 (mod r)을 만족하는 최소 양의 정수 k입니다.

    Args:
        n: 기준 정수
        r: 모듈러스

    Returns:
        ord_r(n). gcd(n, r) != 1이면 0 반환 (위수가 정의되지 않음)
    """
    if gcd(n % r, r) != 1:
        return 0
    order = 1
    current = n % r
    while current != 1:
        current = (current * n) % r
        order += 1
    return order


def euler_totient(n: int) -> int:
    """
    오일러 토션트 함수 φ(n)을 계산합니다.
    φ(n)은 1 이상 n 이하의 정수 중 n과 서로소인 정수의 개수입니다.

    Args:
        n: 양의 정수

    Returns:
        φ(n)
    """
    result = n
    temp = n
    p = 2
    while p * p <= temp:
        if temp % p == 0:
            while temp % p == 0:
                temp //= p
            result -= result // p
        p += 1
    if temp > 1:
        result -= result // temp
    return result


def poly_mult_mod(p1: list, p2: list, r: int, n: int) -> list:
    """
    두 다항식을 (x^r - 1, n)으로 나눈 나머지를 곱합니다.
    즉, Z_n[x] / (x^r - 1) 에서의 다항식 곱셈입니다.

    다항식은 계수 리스트로 표현됩니다: p[i]가 x^i의 계수.

    Args:
        p1: 첫 번째 다항식 (길이 r의 리스트)
        p2: 두 번째 다항식 (길이 r의 리스트)
        r: 다항식 모듈러스 차수 (x^r - 1)
        n: 계수 모듈러스

    Returns:
        곱셈 결과 다항식 (길이 r의 리스트)
    """
    result = [0] * r
    for i, c1 in enumerate(p1):
        if c1 == 0:
            continue
        for j, c2 in enumerate(p2):
            if c2 == 0:
                continue
            result[(i + j) % r] = (result[(i + j) % r] + c1 * c2) % n
    return result


def poly_pow_mod(poly: list, exp: int, r: int, n: int) -> list:
    """
    다항식의 거듭제곱을 (x^r - 1, n)으로 나눈 나머지를 계산합니다.
    제곱-곱셈(square-and-multiply) 방법을 사용하여 효율적으로 계산합니다.

    Args:
        poly: 기저 다항식 (길이 r의 리스트)
        exp: 지수 (양의 정수)
        r: 다항식 모듈러스 차수
        n: 계수 모듈러스

    Returns:
        poly^exp mod (x^r - 1, n)
    """
    # 항등원 다항식: 1 (상수항만 1)
    result = [0] * r
    result[0] = 1
    base = poly[:]
    while exp > 0:
        if exp % 2 == 1:
            result = poly_mult_mod(result, base, r, n)
        base = poly_mult_mod(base, base, r, n)
        exp //= 2
    return result


def aks_is_prime(n: int) -> bool:
    """
    AKS 소수 판별 알고리즘으로 n이 소수인지 판별합니다.

    알고리즘 단계:
      1단계: n이 완전 거듭제곱수이면 합성수(COMPOSITE)
      2단계: ord_r(n) > log2(n)^2 를 만족하는 최소 r을 탐색
      3단계: 어떤 a <= r에 대해 1 < gcd(a, n) < n이면 합성수
      4단계: n <= r이면 소수(PRIME)
      5단계: 다항식 합동 검사: 모든 a in [1, floor(sqrt(φ(r)) * log2(n))]에 대해
             (x + a)^n ≡ x^n + a (mod x^r - 1, n)이면 소수, 아니면 합성수

    Args:
        n: 소수 여부를 판별할 양의 정수

    Returns:
        n이 소수이면 True, 합성수이면 False
    """
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False

    # 1단계: 완전 거듭제곱수 검사
    if is_perfect_power(n):
        return False

    # 2단계: 최소 r 탐색 (ord_r(n) > log2(n)^2)
    log2n = math.log2(n)
    max_k = int(log2n ** 2)

    r = 2
    while True:
        if gcd(r, n) == 1:
            order = multiplicative_order(n, r)
            if order > max_k:
                break
        r += 1

    # 3단계: 1 < gcd(a, n) < n 인 a가 존재하면 합성수
    for a in range(2, min(r, n - 1) + 1):
        g = gcd(a, n)
        if 1 < g < n:
            return False

    # 4단계: n <= r이면 소수
    if n <= r:
        return True

    # 5단계: 다항식 합동 검사
    phi_r = euler_totient(r)
    limit = int(math.floor(math.sqrt(phi_r) * log2n))

    for a in range(1, limit + 1):
        # LHS: (x + a)^n mod (x^r - 1, n)
        lhs_poly = [0] * r
        lhs_poly[0] = a % n   # 상수항
        lhs_poly[1] = 1       # x항
        lhs = poly_pow_mod(lhs_poly, n, r, n)

        # RHS: x^n + a mod (x^r - 1, n)
        rhs = [0] * r
        rhs[n % r] = (rhs[n % r] + 1) % n
        rhs[0] = (rhs[0] + a) % n

        if lhs != rhs:
            return False

    return True


if __name__ == "__main__":
    print("AKS 소수 판별 알고리즘 데모")
    print("=" * 40)
    print("1부터 100까지의 소수:")
    primes = [n for n in range(2, 101) if aks_is_prime(n)]
    print(primes)
    print()
    print("특정 수 판별 예시:")
    test_cases = [2, 3, 4, 17, 97, 100, 101, 561, 1009]
    for n in test_cases:
        result = "소수" if aks_is_prime(n) else "합성수"
        print(f"  {n:5d} -> {result}")
