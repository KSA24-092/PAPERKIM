# AKS 소수 판별 알고리즘 원리 및 수학적 증명

> Agrawal, M., Kayal, N., & Saxena, N. (2004). PRIMES is in P. *Annals of Mathematics*, 160(2), 781–793.

---

## 1. 개요

2002년 인도 IIT 칸푸르의 Manindra Agrawal, Neeraj Kayal, Nitin Saxena 세 명이 발표한 AKS 알고리즘은 **결정적(deterministic)·무조건적(unconditional)·다항 시간(polynomial time)** 소수 판별 알고리즘입니다.

발표 전까지는 다음 두 가지 한계가 있었습니다.

| 기존 방법 | 한계 |
|---|---|
| 에라토스테네스의 체 | 지수적 시간 |
| 밀러-라빈(Miller-Rabin) 등 확률적 알고리즘 | 결과가 확률적 (오류 가능) |
| GRH 가정 하의 결정적 알고리즘 | 리만 가설 등 미증명 가정 필요 |

AKS는 이 세 가지 한계를 모두 극복한 최초의 알고리즘입니다. 시간 복잡도는 원 논문 기준 **O(log^12(n))** 이며, 이후 개선된 버전은 **O(log^6(n) polylog(log(n)))** 입니다.

---

## 2. 핵심 정리 (Key Theorem)

알고리즘 전체는 다음 하나의 정리로부터 출발합니다.

### 정리 (AKS 주정리)

> 정수 n ≥ 2가 주어졌을 때, n이 **소수**인 것은 다음이 성립하는 것과 동치이다:
>
> $$(x - a)^n \equiv x^n - a \pmod{n} \quad \text{(다항식 환 } \mathbb{Z}[x] \text{에서)}$$
>
> 단, a는 n과 서로소인 임의의 정수.

### 증명 (정리의 동치 관계)

**(⇒) n이 소수이면 성립한다**

이항 정리에 의해:

$$(x - a)^n = \sum_{k=0}^{n} \binom{n}{k} x^k (-a)^{n-k}$$

n이 소수이면, 0 < k < n인 모든 k에 대해 이항 계수 $\binom{n}{k} = \frac{n!}{k!(n-k)!}$는 n의 배수입니다(분자의 n이 소수이므로 분모와 약분되지 않음).

따라서 $\mathbb{Z}_n[x]$에서:

$$\binom{n}{k} \equiv 0 \pmod{n} \quad (0 < k < n)$$

$$\Rightarrow (x-a)^n \equiv x^n + (-a)^n \equiv x^n - a^n \pmod{n}$$

페르마 소정리에 의해 n이 소수이고 $\gcd(a,n)=1$이면 $a^n \equiv a \pmod{n}$이므로:

$$\boxed{(x-a)^n \equiv x^n - a \pmod{n}}$$

**(⇐) 위 합동식이 성립하면 n은 소수이다**

대우를 증명합니다. n이 합성수라고 가정하면, n의 어떤 소인수 p에 대해 $p^{\alpha} \| n$ (정확히 p^α이 n을 나눔)입니다.

$x^n - a$에서 x에 0을 대입하면 $(-a)^n$, LHS에서는 $(-a)^n$을 얻습니다.

그러나 계수를 비교하면: 전개식에서 $x^{n-p}$ 항의 계수는 $\binom{n}{p}(-a)^{n-p}$인데,

$$v_p\left(\binom{n}{p}\right) = v_p(n) - v_p(p) = \alpha - 1$$

(여기서 $v_p(m)$은 m의 p진 부치(p-adic valuation))

따라서 $\binom{n}{p} \not\equiv 0 \pmod{n}$ (α = 1인 경우), 즉 해당 계수가 n으로 나누어지지 않으므로 합동식이 성립하지 않습니다. □

---

## 3. 알고리즘 구조 및 각 단계의 수학적 근거

직접 위 정리를 적용하려면 n에 서로소인 모든 a에 대해 검사해야 하여 여전히 지수 시간이 필요합니다. AKS의 핵심은 이를 **다항식 환 $\mathbb{Z}_n[x]/(x^r-1)$로 축소**하여 검사 횟수를 줄이는 것입니다.

### 3.1 완전 거듭제곱수 검사 (1단계)

n = a^b (a, b ≥ 2) 이면 n은 자명하게 합성수입니다.

**구현:** b를 2부터 $\lfloor \log_2 n \rfloor$까지 순회하며 $n^{1/b}$이 정수인지 확인합니다.

---

### 3.2 적절한 r 탐색 (2단계)

**목표:** $\text{ord}_r(n) > \log_2^2(n)$ 이고 $r \leq \lceil \log_2^5(n) \rceil$를 만족하는 r을 찾습니다.

**곱셈적 위수(multiplicative order):** $\text{ord}_r(n)$은 $n^k \equiv 1 \pmod{r}$를 만족하는 최소 양의 정수 k입니다.

**왜 이 조건이 필요한가?**

이후 5단계의 다항식 합동 검사에서, 검사해야 하는 a의 개수가 $\lfloor\sqrt{\phi(r)} \cdot \log_2 n\rfloor$개입니다. r을 크게 잡을수록 검사 횟수는 늘지만, 합성수를 잘못 소수로 판정할 위험이 줄어듭니다.

$\text{ord}_r(n) > \log_2^2(n)$ 조건은 이 검사가 올바르게 동작하기 위한 충분 조건임이 증명되어 있습니다.

**원 논문의 보조 정리 (Lemma 4.3):**

> $B = \lceil\log_2^5(n)\rceil$, $\{n^j \bmod r : 0 \leq j \leq \lfloor\log_2^2 n\rfloor\}$ 중 서로 다른 원소의 개수를 $t$라 할 때,
> 원하는 r은 $\lceil\log_2^5(n)\rceil$ 이하에서 항상 찾을 수 있다.

증명의 핵심: $\prod_{r \leq B} r$ (B 이하 모든 수의 곱) > $2^B$이고, 이 중 $\text{ord}_r(n) \leq \log_2^2(n)$을 만족하는 r들의 곱은 $n^{O(\log^2 n)}$ 이하이므로, B가 충분히 크면 조건을 만족하는 r이 존재합니다.

---

### 3.3 소인수 검사 (3단계)

$\gcd(a, n)$이 1보다 크고 n보다 작은 a가 $a \leq r$ 범위 내에 존재하면, 해당 값이 n의 진약수이므로 n은 합성수입니다.

---

### 3.4 작은 n 처리 (4단계)

n ≤ r이면: 3단계를 통과한 n은 r 이하의 모든 수와 서로소이거나 n = r입니다. r < n이라면 n의 최소 소인수는 r보다 크므로 n ≤ r이 성립할 때 n은 소수가 됩니다.

---

### 3.5 다항식 합동 검사 (5단계)

이것이 AKS 알고리즘의 핵심 부분입니다.

**검사 조건:**

$$\forall a \in \{1, 2, \ldots, \lfloor\sqrt{\phi(r)} \cdot \log_2 n\rfloor\}: \quad (x+a)^n \equiv x^n + a \pmod{x^r - 1, \, n}$$

여기서 $\phi(r)$는 오일러 토션트 함수입니다.

**수학적 근거 (원 논문 Theorem 4.1의 핵심 아이디어):**

위 검사가 **n이 소수인 경우** 항상 통과됨을 먼저 보입니다.

**보조 정리:** n이 소수이면:

1. $(x+a)^n \equiv x^n + a \pmod{n}$ (3.0절의 정리에서)
2. $x^n \equiv x^{n \bmod r} \pmod{x^r - 1}$ (지수를 r로 환원)

따라서 $(x+a)^n \equiv x^{n \bmod r} + a \pmod{x^r - 1, n}$이 성립하므로 검사를 통과합니다.

**핵심 증명 (합성수이면 검사 실패):**

이 방향이 증명의 어려운 부분입니다. 다음 집합을 정의합니다:

$$\mathcal{P} = \{p : p \text{는 } n \text{의 소인수}, \, p > r\}$$

(3, 4단계를 통과했으므로 n의 모든 소인수는 r보다 큽니다)

**집합 I와 G의 정의:**

$$I = \{n^i \cdot p^j : i \geq 0, j \geq 0\} \subset (\mathbb{Z}/r\mathbb{Z})^*$$

$\text{ord}_r(n) > \log_2^2 n$ 조건에 의해 이 집합 크기: $|I| > \log_2^2 n$

**축소 (Introspective) 수와 다항식:**

m이 *축소적(introspective)*이라는 것은: 모든 검사 대상 다항식 $f(x)$에 대해

$$f(x)^m \equiv f(x^m) \pmod{x^r - 1, n}$$

이 성립하는 것입니다. 핵심 보조 정리:

- n이 소수이면 n은 축소적입니다 (2절의 정리로부터).
- 축소적인 수들의 곱도 축소적입니다.
- 따라서 $I$의 모든 원소가 축소적입니다.

**집합 G의 크기 하한:**

$$G = \{(x+a) \bmod (h(x), n) : a \in \{1, \ldots, \lfloor\sqrt{\phi(r)}\log_2 n\rfloor\}\} \cup \{x\}$$

$h(x)$는 $\mathbb{F}_p[x]$에서 $x^r - 1$의 적당한 인수입니다(차수 ≥ $\text{ord}_r(n)$).

**모순 논증:**

만약 n이 5단계를 통과한 합성수라면:

1. 집합 G가 생성하는 군 $\hat{G}$의 크기: $|\hat{G}| \leq n^{\sqrt{\phi(r)}}$
2. 그러나 I의 모든 원소가 $\hat{G}$의 원소에 독립적으로 작용하므로: $|\hat{G}| \geq \binom{|I| + \lfloor\sqrt{\phi(r)}\rfloor}{\lfloor\sqrt{\phi(r)}\rfloor}$

**부등식 비교:**

$|I| > \log_2^2 n$이고 $\lfloor\sqrt{\phi(r)}\rfloor \geq \sqrt{\phi(r)} - 1$이므로:

$$\binom{|I| + \lfloor\sqrt{\phi(r)}\rfloor}{\lfloor\sqrt{\phi(r)}\rfloor} > \binom{\log_2^2 n + \sqrt{\phi(r)}}{\sqrt{\phi(r)}} \geq 2^{\sqrt{\phi(r)} \log_2 n} = n^{\sqrt{\phi(r)}}$$

이는 상한 $n^{\sqrt{\phi(r)}}$을 초과하므로 **모순**이 발생합니다.

따라서 n이 합성수이면 5단계에서 반드시 검사에 실패합니다. □

---

## 4. 전체 알고리즘 의사 코드

```
Input:  정수 n ≥ 2
Output: PRIME 또는 COMPOSITE

1단계: n = a^b (b ≥ 2)이면 COMPOSITE 반환

2단계: ord_r(n) > log₂²(n) 을 만족하는 최소 r을 찾는다

3단계: 어떤 a (2 ≤ a ≤ r)에 대해 1 < gcd(a, n) < n이면 COMPOSITE 반환

4단계: n ≤ r이면 PRIME 반환

5단계: a = 1부터 ⌊√φ(r) · log₂(n)⌋까지:
       if (x + a)^n ≢ x^n + a  (mod x^r - 1, n) then
           COMPOSITE 반환

6단계: PRIME 반환
```

---

## 5. 복잡도 분석

| 단계 | 시간 복잡도 |
|------|------------|
| 1단계 (완전 거듭제곱 검사) | $O(\log^3 n)$ |
| 2단계 (r 탐색) | $O(\log^5 n \cdot \log\log n)$ |
| 3단계 (gcd 검사) | $O(\log^5 n \cdot \log n)$ |
| 4단계 (크기 비교) | $O(1)$ |
| 5단계 (다항식 합동 검사) | $O(\log^{10.5} n \cdot \log\log n)$ |
| **전체** | **$O(\log^{10.5} n \cdot \text{polylog}(\log n))$** |

원 논문은 $\tilde{O}(\log^{12}(n))$으로 표기하였고, 이후 Lenstra-Pomerance의 개선으로 $\tilde{O}(\log^6(n))$이 달성되었습니다.

---

## 6. 역사적 의의

AKS 이전 소수 판별 알고리즘의 계산 복잡도 분류:

- **P**: 결정적 다항 시간 — AKS(2002) 이전에는 미지의 영역
- **BPP**: 확률적 다항 시간 — 밀러-라빈(Miller-Rabin), 소이어-스트라센(Solovay-Strassen)
- **공개 문제**: "PRIMES ∈ P?" — 2002년 AKS 논문 제목 "PRIMES is in P"로 해결

AKS는 **계산 복잡도 이론**에서 가장 오랫동안 열려 있던 문제 중 하나를 해결했습니다. 비록 실용적인 측면에서는 밀러-라빈이 더 빠르지만, AKS는 이론적으로 소수 판별이 다항 시간 내에 결정적으로 해결 가능함을 증명한 이정표입니다.

---

## 7. 참고 자료

1. Agrawal, M., Kayal, N., & Saxena, N. (2004). PRIMES is in P. *Annals of Mathematics*, **160**(2), 781–793.
2. Granville, A. (2004). It is easy to determine whether a given integer is prime. *Bulletin of the American Mathematical Society*, **42**(1), 3–38.
3. Bernstein, D. J. (2002). An exposition of the Agrawal-Kayal-Saxena primality-proving theorem.
