# Embedded SW Study — 학습에서 영상인식 배포까지

## 데이터 분할과 실험

강의 MNIST 실습은 60,000 train과 10,000 test를 사용합니다. 이 코드의 보완 기본값은 train에서 10,000개를 검증으로 분리하고 나머지 50,000개를 학습에 사용합니다. 먼저 원본 인덱스를 나누고 학습 인덱스에만 증강을 적용합니다.

`source` 증강은 PPT처럼 양의 10~30도 affine와 kernel3 blur를 적용한 최대 20,000개를 원본 학습 항목과 결합합니다. 기본 분할이면 50,000+20,000=70,000 논리 항목입니다. PPT의 80,000과 다른 이유는 검증 세트를 별도로 확보했기 때문입니다. `balanced`는 ±15도 회전과 작은 이동을 각 학습 샘플에 적용하는 추가 예제입니다. 실제 효과는 검증 결과로 판단합니다.

검증 손실이 가장 낮은 가중치를 복사·저장하며 patience 동안 개선되지 않으면 종료합니다. 배치 손실 평균은 배치 크기로 가중해 마지막 작은 배치도 올바르게 반영합니다. 시험 평가는 best 가중치를 복원한 뒤 한 번 수행합니다.

Seed는 데이터 분할과 실행 재현의 출발점입니다. 하드웨어/라이브러리 버전이 바뀌면 완전한 bitwise 재현까지 보장하지 않습니다. 실제 데이터 분포, 클래스별 성능, 혼동 행렬도 배포 전 추가 확인합니다.

## 증강·Dropout 실험표

| 실험 | 모델 | Dropout | 증강 | 질문 |
|---|---|---|---|---|
| A | MLP | 0 | none | baseline |
| B | MLP | .2 | none | Dropout의 일반화 효과 |
| C | MLP | .2 | balanced | 작은 회전/이동 효과 |
| D | CNN | head 없음 | none | 공간 구조 활용 효과 |
| E | residual CNN | head 없음 | balanced | 구조 변경의 비용 대비 효과 |

모든 실험에서 split seed와 평가 기준을 고정합니다. 코드는 결과를 CSV에 기록하며, 예시 구조의 성능 수치를 문서에서 미리 보장하지 않습니다.

## 임베디드 적용

- 카메라의 채널 순서 RGB/BGR, resize, crop, 정규화, CHW/NCHW를 학습과 동일하게 구현합니다. 센서 입력을 MNIST처럼 취급하지 않습니다.
- 모델 파일 크기 외에도 중간 activation과 실행기의 workspace 메모리를 측정합니다. 파라미터가 적다고 peak RAM이 항상 작은 것은 아닙니다.
- CPU/GPU/NPU의 지원 연산을 확인합니다. depthwise convolution의 이론적 비용 절감이 실제 지연 감소로 이어지는지는 장치에서 측정합니다.
- FP16/INT8을 도입하면 대표 데이터로 정확도를 다시 평가합니다. 양자화 calibration에는 시험 정답을 이용한 튜닝을 하지 않습니다.
- 프레임 전처리, 추론, 후처리, 통신을 합친 end-to-end 지연과 최악 지연을 확인합니다. deadline은 평균 FPS만으로 검증하지 않습니다.
- 학습용 PyTorch 코드는 MCU firmware 자체가 아닙니다. MCU에 옮기려면 지원 런타임/변환 도구, 메모리 배치, 센서 인터페이스를 별도로 구현해야 합니다.

전이 학습은 데이터가 작을 때 pretrained backbone을 동결해 head부터 학습하고 일부 블록을 낮은 학습률로 풀어 비교하는 출발점입니다. 이 저장소에는 pretrained weights를 포함하지 않습니다. [공식 전이 학습 예제](https://docs.pytorch.org/tutorials/beginner/transfer_learning_tutorial)
