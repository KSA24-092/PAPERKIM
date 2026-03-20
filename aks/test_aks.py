"""
AKS 소수 판별 알고리즘 테스트
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from aks.aks import (
    is_perfect_power,
    multiplicative_order,
    euler_totient,
    poly_mult_mod,
    poly_pow_mod,
    aks_is_prime,
)


# ---------------------------------------------------------------------------
# is_perfect_power 테스트
# ---------------------------------------------------------------------------

class TestIsPerfectPower:
    def test_small_composites_not_perfect_power(self):
        assert is_perfect_power(6) is False
        assert is_perfect_power(10) is False

    def test_perfect_squares(self):
        assert is_perfect_power(4) is True    # 2^2
        assert is_perfect_power(9) is True    # 3^2
        assert is_perfect_power(25) is True   # 5^2

    def test_perfect_cubes(self):
        assert is_perfect_power(8) is True    # 2^3
        assert is_perfect_power(27) is True   # 3^3
        assert is_perfect_power(125) is True  # 5^3

    def test_primes_not_perfect_power(self):
        for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]:
            assert is_perfect_power(p) is False, f"{p}는 완전 거듭제곱수가 아니어야 함"

    def test_higher_powers(self):
        assert is_perfect_power(64) is True    # 2^6, 4^3, 8^2
        assert is_perfect_power(1024) is True  # 2^10


# ---------------------------------------------------------------------------
# multiplicative_order 테스트
# ---------------------------------------------------------------------------

class TestMultiplicativeOrder:
    def test_basic_order(self):
        # 2^1=2, 2^2=4, 2^3=3, 2^4=1 (mod 5) => ord_5(2) = 4
        assert multiplicative_order(2, 5) == 4

    def test_order_one(self):
        # 1^k = 1 (mod r) 이므로 ord(1) = 1
        assert multiplicative_order(1, 7) == 1

    def test_not_coprime_returns_zero(self):
        # gcd(6, 9) = 3 != 1 => 위수 없음
        assert multiplicative_order(6, 9) == 0

    def test_known_orders(self):
        # ord_7(3): 3^1=3, 3^2=2, 3^3=6, 3^4=4, 3^5=5, 3^6=1 => 6
        assert multiplicative_order(3, 7) == 6
        # ord_7(2): 2^1=2, 2^2=4, 2^3=1 => 3
        assert multiplicative_order(2, 7) == 3


# ---------------------------------------------------------------------------
# euler_totient 테스트
# ---------------------------------------------------------------------------

class TestEulerTotient:
    def test_prime_totient(self):
        # φ(p) = p - 1 for prime p
        for p in [2, 3, 5, 7, 11, 13]:
            assert euler_totient(p) == p - 1

    def test_small_values(self):
        assert euler_totient(1) == 1
        assert euler_totient(4) == 2   # φ(4) = 2
        assert euler_totient(6) == 2   # φ(6) = 2
        assert euler_totient(12) == 4  # φ(12) = 4

    def test_prime_power(self):
        # φ(p^k) = p^(k-1) * (p-1)
        assert euler_totient(8) == 4   # φ(2^3) = 4
        assert euler_totient(9) == 6   # φ(3^2) = 6


# ---------------------------------------------------------------------------
# poly_mult_mod 테스트
# ---------------------------------------------------------------------------

class TestPolyMultMod:
    def test_identity(self):
        # 1 * p = p
        r, n = 5, 7
        p = [1, 2, 3, 0, 0]
        one = [1, 0, 0, 0, 0]
        assert poly_mult_mod(one, p, r, n) == p

    def test_simple_multiply(self):
        # (x) * (x) = x^2 mod (x^3 - 1, 7) => [0, 0, 1]
        r, n = 3, 7
        x = [0, 1, 0]
        result = poly_mult_mod(x, x, r, n)
        assert result == [0, 0, 1]

    def test_wrap_around(self):
        # x^2 * x = x^3 ≡ 1 mod (x^3 - 1) => [1, 0, 0]
        r, n = 3, 7
        x2 = [0, 0, 1]
        x1 = [0, 1, 0]
        result = poly_mult_mod(x2, x1, r, n)
        assert result == [1, 0, 0]

    def test_coefficient_mod(self):
        # 계수가 n으로 줄어드는지 확인
        r, n = 2, 3
        p = [2, 2]
        result = poly_mult_mod(p, p, r, n)
        for c in result:
            assert 0 <= c < n


# ---------------------------------------------------------------------------
# aks_is_prime 주요 테스트
# ---------------------------------------------------------------------------

class TestAksIsPrime:
    KNOWN_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
                    53, 59, 61, 67, 71, 73, 79, 83, 89, 97]

    KNOWN_COMPOSITES = [4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 21, 22, 24, 25,
                        26, 27, 28, 30, 32, 33, 34, 35, 36, 38, 39, 40]

    def test_edge_cases(self):
        assert aks_is_prime(0) is False
        assert aks_is_prime(1) is False

    def test_known_primes(self):
        for p in self.KNOWN_PRIMES:
            assert aks_is_prime(p) is True, f"{p}는 소수여야 함"

    def test_known_composites(self):
        for c in self.KNOWN_COMPOSITES:
            assert aks_is_prime(c) is False, f"{c}는 합성수여야 함"

    def test_carmichael_numbers(self):
        # 카마이클 수: 페르마 소수 판별을 통과하지만 합성수인 수
        # 561 = 3 × 11 × 17, 1105 = 5 × 13 × 17
        assert aks_is_prime(561) is False
        assert aks_is_prime(1105) is False

    def test_perfect_power_composites(self):
        assert aks_is_prime(4) is False   # 2^2
        assert aks_is_prime(8) is False   # 2^3
        assert aks_is_prime(25) is False  # 5^2
        assert aks_is_prime(49) is False  # 7^2

    def test_larger_primes(self):
        assert aks_is_prime(101) is True
        assert aks_is_prime(997) is True
        assert aks_is_prime(1009) is True

    def test_primes_up_to_100_match_sieve(self):
        """에라토스테네스의 체와 AKS 결과가 일치하는지 확인"""
        def sieve(limit):
            is_p = [True] * (limit + 1)
            is_p[0] = is_p[1] = False
            for i in range(2, int(limit**0.5) + 1):
                if is_p[i]:
                    for j in range(i*i, limit + 1, i):
                        is_p[j] = False
            return [i for i in range(2, limit + 1) if is_p[i]]

        expected = sieve(100)
        actual = [n for n in range(2, 101) if aks_is_prime(n)]
        assert actual == expected
