import sys

chunks = [
    {
        "start": 1, "end": 42,
        "title": "모듈 임포트 및 알고리즘 개요 (Docstring)",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 1--28:} 스크립트 최상단에 위치한 Docstring입니다. 2018년 Eurographics에 발표된 Birsak 등의 논문을 바탕으로 한 기본 아이디어와, 기초 탐욕 알고리즘 대비 본 코드가 가지는 6가지 주요 개선점(물리 기반 곱셈 투과율 모델, 인접 핀 평가, 중요도 맵, 스마트 시작점 지정, 정련 과정, 추세 기반 정지 조건 등)을 설명합니다. 입출력 사양 또한 명세되어 있습니다.
\item \textbf{Line 30--42:} 행렬 연산을 위한 \texttt{numpy}, 이미지 처리를 위한 \texttt{PIL}, 멀티코어를 활용해 연산을 가속하기 위한 \texttt{multiprocessing}과 병렬 스레드풀 모듈을 가져옵니다.
\end{itemize}"""
    },
    {
        "start": 43, "end": 118,
        "title": "안티앨리어싱 선분 래스터화 (Xiaolin-Wu 알고리즘)",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 48--61:} 선을 그릴 때 발생하는 계단 현상(Aliasing)을 방지하는 함수입니다. 가장 먼저 고속 동작을 위해 \texttt{skimage.draw.line\_aa} 임포트를 시도하며, 라이브러리가 없으면 아래의 자체 구현(Fallback)을 사용합니다.
\item \textbf{Line 64--69:} 선분의 기울기가 1보다 큰 가파른(steep) 상태일 경우, 변수 평면의 x와 y를 뒤집어 알고리즘의 대칭성을 보장하고 수치적 안정성을 확보합니다. 
\item \textbf{Line 71--88:} 선분의 시작점과 끝점 좌표를 구하고, \texttt{np.floor}를 통해 실제 픽셀 그리드에 걸치는 비중(\texttt{frac})을 계산하여 위/아래 픽셀에 할당할 가중치를 초기화합니다.
\item \textbf{Line 90--108:} \textbf{Main loop:} 선분의 \(x\)축을 따라 분수 부분(\texttt{frac})을 계속 추적하여 해당 픽셀에 적용될 안티앨리어싱 가중치 2개 쌍(\texttt{1 - frac} 및 \texttt{frac})을 생성해 배열에 저장합니다.
\item \textbf{Line 110--117:} 계산된 좌표열 및 가중치 배열을 \texttt{numpy} 형태로 반환하되, 초기에 가파른 선으로 인해 축을 교환했다면 돌려주기 전 값을 원래대로 복원(\texttt{rr, cc = cc, rr})합니다.
\end{itemize}"""
    },
    {
        "start": 119, "end": 130,
        "title": "병렬 처리용 선분 계산 워커 함수",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 123--130:} 파이썬의 \texttt{multiprocessing.Pool} 객체가 직렬화(pickle)하여 각 코어에 분배할 수 있도록 설계된 전역 레벨 워커(worker) 함수입니다. 
\item 두 핀의 인덱스(\texttt{i, j})와 픽셀 좌표, 이미지 크기를 인자로 받아 앞서 정의한 \texttt{\_line\_aa\_builtin} 함수를 호출합니다. 이후 \texttt{good} 마스크를 씌워 캔버스(가로세로 \texttt{img\_size}) 바깥으로 벗어난 픽셀의 오버플로우 좌표를 엄격히 잘라낸 뒤 반환합니다.
\end{itemize}"""
    },
    {
        "start": 131, "end": 192,
        "title": "core StringArt 클래스와 초기화 (__init__)",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 134--155:} 핵심 알고리즘이 구현된 \texttt{StringArt} 클래스에 대한 상세 문서(Docstring)입니다. 핀 개수, 생성할 문자열의 최대 개수, 한 가닥의 불투명도(\texttt{string\_opacity}), 선 유지 최소 핀 거리(\texttt{min\_pin\_distance}), 에지 맵 강조량 등의 주요 파라미터를 설명합니다.
\item \textbf{Line 157--172:} \texttt{\_\_init\_\_} 생성자를 통해 외부로부터 하이퍼파라미터를 입력받고 클래스 내부 상태(self)로 저장합니다. 
\item \textbf{Line 173--192:} 선 작업에 필수적인 여러 가지 사전 단계 매서드들을 순서대로 일괄 실행합니다: 원형 마스크 생성, 내부 데이터 포맷에 맞춘 이미지 로드(흰색=255, 흑색=0 이지만 원 내부의 로직을 거침), 중요도 맵 생성, 핀들의 공간적 배치, 멀티프로세싱을 통한 모든 가능한 핀 쌍(\texttt{line\_cache}) 및 유효 인접 핀(\texttt{pin\_neighbours})의 사전 계산, 그리고 결과 값을 담기 위한 빈 배열들을 할당합니다.
\end{itemize}"""
    },
    {
        "start": 193, "end": 211,
        "title": "이미지 로드 및 전처리 파이프라인",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 196--202:} PIL 이미지 라이브러리를 사용해 컬러/알파 채널 이미지를 완벽한 흑백(\texttt{"L"})으로 변환한 후, \texttt{LANCZOS} 필터로 목표 정사각형 크기에 맞추어 정교하게 리사이즈합니다. 그 다음 \texttt{float64} numpy 배열로 변환합니다.
\item \textbf{Line 204--211:} 단순히 0\string~255로 쓰는 것을 넘어, 화면에 보여지는 원형 마스크 내부 영역만 추출한 후 \textbf{동적 대비 스트레칭(Percentile-based contrast stretching)}을 수행합니다. 어두운 쪽 하위 2\%를 0, 밝은 쪽 상위 98\%를 1로 클리핑하여 조명이 부족한 원본 이미지도 뚜렷한 특징분포를 갖도록 대비를 교정합니다.
\end{itemize}"""
    },
    {
        "start": 212, "end": 241,
        "title": "에지 기반 중요도 맵(Importance Map) 생성",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 214--221:} 알고리즘이 단순한 배경 명암보다 구조적인 형태와 세부 디테일(Edge)에 끈을 더 많이 할당하도록 가중치 지도를 생성합니다. 사용자가 가중치를 0으로 주었다면 마스크와 동일한 균일 맵을 반환합니다.
\item \textbf{Line 223--232:} PIL의 \texttt{ImageFilter.Kernel}을 직접 정의하여 수평(sx), 수직(sy) 방향 소벨(Sobel) 그라디언트를 검출하고 에지의 크기(magnitude) 벡터 맵을 계산합니다. 필터 에러 방지를 위해 기본 제공되는 \texttt{FIND\_EDGES}를 예비 처리용으로 둡니다.
\item \textbf{Line 234--241:} 계산된 에지 맵을 최댓값으로 나누어 점수를 0\string~1로 정규화한 뒤, 사용자의 강조 인자(\texttt{importance\_edge\_weight})를 곱합니다. 결과적으로 평탄한 곳에는 가중치 1.0, 아주 뚜렷한 윤곽이 있는 곳엔 \(1.0 + \text{weight}\) 형태의 가중치가 부여되게 됩니다.
\end{itemize}"""
    },
    {
        "start": 242, "end": 261,
        "title": "기하학적 보조 함수들 (마스크 및 핀 배치)",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 245--250:} 정방형 이미지 내에서 핀들이 박혀 이뤄지는 원 영역을 가리기 위해, 중심점(\texttt{centre}) 기준으로 원 안에 포함되는 픽셀엔 1, 바깥엔 0을 가지는 논리 배열(\texttt{mask})을 생성합니다. Numpy의 \texttt{ogrid}를 써서 고속으로 처리합니다.
\item \textbf{Line 252--261:} 극좌표계의 원리를 사용해 원 둘레를 \texttt{num\_pins} 개수만큼 균일한 각도(\texttt{np.linspace}) 조각으로 분리하고, 삼각함수(cos, sin)를 사용해 \(x, y\) 픽셀 좌표 공간으로 변환합니다. 이미지 배치를 벗어나지 않도록 \texttt{np.clip}으로 제한하고 결과 좌표를 배열에 담아 저장합니다.
\end{itemize}"""
    },
    {
        "start": 262, "end": 298,
        "title": "사전 계산 (선분 픽셀 캐시 및 이웃 핀 목록)",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 264--284:} 가장 빈번하게 호출되는 후보 평가 구간의 부하를 줄이기 위한 핵심 병렬 로직입니다. 둥글게 배치된 핀 인덱스 \((i, j)\)에 대해 사이 거리(\texttt{arc})를 파악하고 \texttt{min\_pin\_distance} 이상 떨어진 모든 유효 쌍의 픽셀 좌표 래스터화 태스크를 리스트업합니다. 이를 \texttt{multiprocessing.Pool}에 던져 다중 코어로 한 번에 처리한 후, 거대한 \texttt{self.line\_cache} 딕셔너리에 핀 튜플 키 단위로 저장합니다. 10만 개가 넘을 수 있는 쌍을 단 수 초 만에 파싱합니다.
\item \textbf{Line 286--298:} 위 선분 캐싱 조건에서 합격한 쌍들을 바탕으로, 각 핀 \(i\)에 대해 "해당 위치에서 나갈 수 있는 후보 목적지 핀"을 필터링해 둔 \texttt{pin\_neighbours} 이중 리스트를 만듭니다. 탐욕 매 단계에서 후보를 전체 풀 탐색하는 대신 단숨에 쳐낼 수 있도록 합니다.
\end{itemize}"""
    },
    {
        "start": 299, "end": 343,
        "title": "L2 에너지 및 최적화 점수 (Error Reduction) 계산",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 301--306:} 현재 투과율(transmittance) 캔버스가 완벽히 복원됐을 때 목표(target) 대비 화소의 MSE (차이 제곱의 평균, unweighted)를 계산합니다. 로그와 진행 경과 출력에 사용됩니다.
\item \textbf{Line 308--312:} 위에서 미리 구한 중요도 에지 맵을 곱하여 시각적으로 민감한 부분의 오차가 더 높은 에너지 페널티를 받도록 만든 지표 함수입니다.
\item \textbf{Line 314--343:} 한 가닥의 선(\(a \rightarrow b\))을 그을 때 발생하는 전체 \textbf{가중치 에러 감소량(Error Reduction)}을 유도된 폐형식(closed-form) 식으로 단 한 번에 계산하는 가장 핵심적인 수학 연산 최적화 함수입니다. 선이 지나가는 픽셀 위치의 밝기, 가중치를 가져온 뒤 벡터 배열 연산(\texttt{W * s * (2.0 * d - s)})으로 합산하여 양수가 반환되면 에러가 줄어듦(이득), 음수이면 오히려 화질이 훼손됨을 뜻합니다.
\end{itemize}"""
    },
    {
        "start": 344, "end": 373,
        "title": "후보 핀 평가 함수 (병렬 스레드 지원)",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 346--358:} 실 짜기를 시작할 가장 완벽한 0번 핀을 찾기 위한 자동 설정 함수입니다. 스레드풀(\texttt{ThreadPoolExecutor})을 이용, 0번부터 N번까지의 출발선에서 최선의 감소량을 가진 핀을 스캔하여 반환합니다.
\item \textbf{Line 360--373:} 단일 핀 \texttt{current\_pin}에서 나갈 수 있는 타겟 \texttt{candidates} 집단에 대해 스코어를 테스트하는 실무 평가 함수입니다. 단순히 감소량(\texttt{score})만을 보는 게 아니라, 이미 쓴 핀 쌍 정보(\texttt{pair\_usage})를 조회한 뒤 반복 재사용 횟수마다 강한 배수형 감쇠 페널티(\texttt{1.0 - 0.2 * usage})를 맥여 동일 구역이 새까맣게 타는 현상(과암화)을 억제합니다.
\end{itemize}"""
    },
    {
        "start": 374, "end": 455,
        "title": "주 알고리즘(Main: Phase 1) — 탐욕 선택 로직",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 376--408:} \texttt{run} 메인 드라이버의 서두입니다. 캔버스의 투과율 변수를 모든 픽셀에서 1.0(백색)으로 초기화한 후 시작 핀을 결정해 시퀀스 리스트(\texttt{string\_sequence})에 넣고 터미널에 초기 정보를 인쇄합니다.
\item \textbf{Line 411--427:} 지정된 \texttt{max\_strings} 값만큼 루프를 도는 \textbf{Phase 1 탐욕(Greedy)} 알고리즘 구간입니다. 코어 수(\texttt{\_num\_workers})를 계산해 후보 리스트(\texttt{candidates})를 \texttt{chunk\_sz} 단위로 쪼개 각 스레드에 던져 병렬 평가합니다. 파이썬 GIL 한계에서도 I/O 대기가 아닌 Numpy C모듈 기반 계산을 사용해 어느정도 스레드풀 이점을 취합니다.
\item \textbf{Line 429--442:} 평가 결과 최고의 점수가 0 이하라면 실을 그어도 손해만 난다는 의미로, 지능적 즉시 중단(break) 기준을 발동시킵니다. 합격했다면 찾은 핀 선분의 픽셀 좌표마다 투과율을 비율로 감소시킵니다. 가산적 뺄셈(\(-\))이 아닌 투과율 복사 법칙에 의한 곱셈(\texttt{*(1.0 - opacity*val)})임이 이 알고리즘의 정체성입니다.
\item \textbf{Line 444--455:} 사용한 라인 쌍을 카운팅하고 핀을 이동합니다. 점수를 \texttt{score\_history}에 기록해 최근 800번의 점수 평균이 극초기 평균 대비 0.5\% 아래로 80회 이상 떨어졌다면 이미 완전한 채도 포화(정체)에 빠졌다고 통계적으로 확신하여 조기 종료(Early stopping)를 시킵니다.
\end{itemize}"""
    },
    {
        "start": 456, "end": 542,
        "title": "정련(Phase 2 Refinement) 단계 및 실행 마무리",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 458--499:} 전체 문자열이 놓인 이후 초기에 그렸던 실들에는 편향이 존재할 가능성이 높습니다. 사용자가 설정한 \texttt{refinement\_rounds} 횟수만큼 반복하며 새 하얀 캔버스를 임시로 두고 초기 순서대로 핀을 지나는 시뮬레이션을 재현합니다. 단, 다음 핀으로 움직일 때 \textbf{기존 선택지(\texttt{orig\_dest})} 점수와 변경된 현재 문맥에서의 \textbf{완전한 새로운 최적 목적지(\texttt{cand\_pin})} 대안을 비교 평가합니다.
\item \textbf{Line 501--517:} 새로운 대처안의 L2 감소 점수가 원본보다 크다면 핀 선로를 교체(Swap)함으로써 후처리 최적화를 단행합니다. 대안이건 기존값이건 모두 마이너스 점수라면 스킵하지만, 물리적으로 실의 연결 통로는 유지해야 하기 때문에 투과율은 안 내리고 위치만 유지합니다.
\item \textbf{Line 519--542:} 알고리즘이 결정한 총 누적 투과율을 255.0에 곱하여 눈에 띄는 정수 흑백 이미지(\texttt{result\_image})로 생성 및 복원합니다. 객관적 화질 평가 지표인 종료 MSE와 PSNR (dB 데시벨)을 계산하여 콘솔에 띄운 후 스레드풀 서버를 닫으며 알고리즘 동작을 완전히 매듭짓습니다.
\end{itemize}"""
    },
    {
        "start": 543, "end": 580,
        "title": "렌더링 시각화 모듈 (Matplotlib & PIL)",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 545--553:} \texttt{render\_pil} 파트입니다. 투과율 곱 알고리즘이 계산용 가상 이미지였다면, 이 메서드는 도출된 수천 개의 핀 순서(\texttt{string\_sequence}) 정보를 토대로 Python \texttt{ImageDraw}를 이용해 가장 선명성이 높은 정통 벡터형(Aliasing free) 직선 아트로 그림을 복원하고 평가용 매트릭스로 추출합니다.
\item \textbf{Line 555--580:} \texttt{show\_results} 함수가 세 개의 서브플롯(Original, Algorithm Simulated, Vector Render) 이미지를 나란히 배치해 시각적으로 비교해 주는 matplotlib 플롯(Dashboard)을 렌더링하고 유저가 원할 경우 PNG에 자동 저장시킵니다.
\end{itemize}"""
    },
    {
        "start": 581, "end": 680,
        "title": "작업 파일 내보내기 (TXT 및 좌표 Export)",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 583--592:} 생성된 작품을 실제 못-실 조립 자동화 기계나 손으로 직접 만들기 위해서, 노드 인덱스가 순서대로 적힌 텍스트 지시서(\texttt{pin\_sequence.txt})를 출력합니다.
\item \textbf{Line 594--634:} 로봇 팔 작동이나 AutoCAD CAM 도면화를 위해 좌표계 내보내기(\texttt{save\_coordinates})를 수행합니다. 좌하단 구석이 아닌 물리 정중앙 중심 좌표계(0, 0)와 실제 밀리미터(mm) 단위를 적용, 직교 벡터 좌표 위치(\(x, y\))로 핀 번호와 시작/도착 세트 위치를 매핑해 문서로 떨굽니다.
\item \textbf{Line 636--680:} CNC 가공이나 수동 제작용 작업 베이스 판으로 쓰일 스케일업(\(2000\times2000\) 픽셀 사이즈) 템플릿(pin\_template.png)을 포맷 렌더링합니다. 윤곽 외각선, 각 핀의 스폿 서클뿐만 아니라 번호 겹침을 방지하고자 규칙적인 주기(\texttt{label\_every})별로 인덱스 아라비아 숫자를 투사해 넣습니다.
\end{itemize}"""
    },
    {
        "start": 681, "end": 745,
        "title": "CLI 메인 동작부 (Entry Point)",
        "explanation": r"""\begin{itemize}
\item \textbf{Line 683--691:} 사용자가 \texttt{python 1st review.py} 를 바로 칠 때 작동하는 공간으로 메인 기본 파라미터 변수들을 하드코딩해 세팅해 주고 있습니다.
\item \textbf{Line 693--703:} 커맨드 라인 실행인자(sys.argv)가 있다면 입력 파라미터를 파싱해 사용하며, 만약 없다면 스크립트 실행 경로를 획득한 후 기본적으로 하드 코딩된 샘플 원본 사진 이미지 파일을 찾아 대상으로 연결시킵니다.
\item \textbf{Line 705--745:} 현재 세팅된 파라미터를 예쁘게 꾸며진 CLI 배너로 띄워 주며 \texttt{StringArt} 클래스 인스턴스(\texttt{sa})를 만들어 주입합니다. 그런 다음 \texttt{sa.run()}을 호스트하고 이어서 위에서 정의했던 \texttt{sequence}, \texttt{coordinates}, \texttt{template} 3종 세트와 화상 결과 파일을 파일 시스템에 써서 사용자에게 결과물 패키지를 제공해 줍니다.
\end{itemize}"""
    }
]

import os
with open("1st review.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

output_tex = r"""\clearpage
\section{부록: 전체 소스 코드 라인별 분해 및 구조 주석}

본 부록에서는 \texttt{1st review.py} 파일 안의 전체 소스 코드(총 745라인)를 기능적 모듈 및 블록으로 나누고, દરેક 블록의 역할을 상세한 주석과 함께 서술합니다. 
생략(Omission) 없이 전체 구현 코드를 빠짐없이 포함하였으며, 코드 블록 바로 아래에 상세한 Annotation을 달아 실제 구현 로직과 본문의 수식 모델 간의 논리적 연결성을 명확히 입증합니다.

"""

for i, chunk in enumerate(chunks):
    start = chunk["start"]
    end = chunk["end"]
    # Adjust 0-based index
    chunk_lines = "".join(lines[start-1:min(end, len(lines))])
    
    output_tex += f"\\subsection*{{블록 {i+1}: {chunk['title']} (Lines {start}--{end})}}\n"
    output_tex += f"\\begin{{lstlisting}}[firstnumber={start}]\n"
    output_tex += chunk_lines
    if not chunk_lines.endswith("\n"):
         output_tex += "\n"
    output_tex += "\\end{lstlisting}\n"
    output_tex += chunk["explanation"] + "\n\n"

with open("code_appendix.tex", "w", encoding="utf-8") as f:
    f.write(output_tex)

print("Generated code_appendix.tex successfully.")
