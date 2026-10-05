# 레이어는 어디에 어떻게 쌓는가?

아래 구조는 **보완·설계 조언**입니다. 정답인 단일 구조가 아니라 작은 baseline에서 실험을 시작하는 방법입니다.

## 1. 출력부터 결정하기

| 과제 | 마지막 출력 | 손실/후처리 |
|---|---|---|
| 이진 분류 | `[N,1]` raw logit | BCEWithLogitsLoss / 추론 Sigmoid |
| K클래스 단일 분류 | `[N,K]` logits | CrossEntropyLoss / argmax |
| 다중 레이블 | `[N,K]` 독립 logits | BCEWithLogitsLoss / 클래스별 threshold |
| 픽셀 분류 | `[N,K,H,W]` logits | CE / 픽셀별 argmax |
| 검출 | 클래스·박스·선택적 objectness | 모델별 loss와 박스 decode |

다중 클래스 분류와 다중 레이블을 구분합니다. 이 실습의 MNIST는 10개 중 한 클래스이므로 마지막 Linear 뒤에 ReLU/Softmax를 넣지 않습니다.

## 2. 강의 MLP와 그 비용

XOR 강의 구조: `2 → 10 → 10 → 10 → 1`, 각 Linear 뒤 Sigmoid. 출력 Sigmoid+BCELoss가 원자료 방식이며, 코드는 기본적으로 출력 Sigmoid를 손실에 결합한 BCEWithLogitsLoss를 사용합니다. `--lecture-loss`로 원 방식을 재현할 수 있습니다.

MNIST 강의 구조: `Flatten → Linear(784,512) → ReLU → Dropout(.2) → Linear(512,512) → ReLU → Dropout(.2) → Linear(512,10)`.

Linear의 파라미터는 `입력×출력 + 출력 bias`입니다. 위 MNIST MLP는 `401,920 + 262,656 + 5,130 = 669,706`개입니다. 은닉 크기를 늘리기 전에 학습/검증 곡선과 파라미터 비용을 확인합니다.

## 3. 작은 CNN의 권장 출발점

`Conv(1→32,3,pad1) → BN → ReLU → MaxPool(2) → Conv(32→64,3,pad1) → BN → ReLU → MaxPool(2) → GAP → Flatten → Linear(64,10)`.

| 단계 | 배치 제외 shape |
|---|---|
| 입력 | `1×28×28` |
| Conv/BN/ReLU 1 | `32×28×28` |
| Pool 1 | `32×14×14` |
| Conv/BN/ReLU 2 | `64×14×14` |
| Pool 2 | `64×7×7` |
| GAP | `64×1×1` |
| Linear | `10` |

3×3, stride1, padding1은 공간 크기를 유지합니다. Conv 바로 뒤 BN을 쓰면 Conv bias는 생략할 수 있습니다. 이 구조는 학습 가능한 파라미터 **19,562개**입니다. 작은 MLP보다 항상 정확하다는 보장은 없으며 MNIST에서 기본 구조를 비교하기 위한 예제입니다.

출력 공간 크기는 각 축에서 `floor((입력 + 2p − d(k−1) − 1)/s + 1)`입니다. dilation을 고려하고 두 축을 각각 계산합니다. `lab/inspect_layers.py`로 실제 실행 shape와 파라미터를 확인합니다.

## 4. 깊이와 너비 늘리기

- 해상도를 줄이기 전에 1~2개의 Conv로 해당 해상도의 특징을 학습하는 구성을 비교합니다. 28×28 입력을 초반부터 stride를 크게 주어 줄이면 작은 획이 사라질 수 있습니다.
- 채널은 `32→64→128`처럼 해상도가 내려가는 단계에서 늘리는 것이 출발점입니다. 무조건 두 배가 필수는 아닙니다.
- 깊은 plain network가 잘 학습되지 않으면 residual block을 비교합니다. `F(x)`와 skip의 shape가 같아야 add가 가능합니다.
- 채널/stride가 바뀌면 skip에 `1×1 Conv(stride=s)+BN`을 적용합니다. channel이 다른 두 텐서를 임의로 더하지 않습니다.
- 구현의 residual block은 `Conv→BN→ReLU→Conv→BN→Add→ReLU`입니다. pre-activation 구조와 혼동하지 않습니다.
- Dropout은 우선 MLP/head에 적용하고 p를 검증으로 조절합니다. BN과 Dropout을 모든 Conv 사이에 기계적으로 삽입하지 않습니다.

[잔차 연결의 근거: ResNet](https://arxiv.org/abs/1512.03385).

## 5. 과제에 따라 유지해야 하는 정보

**분류:** 마지막 GAP는 위치별 활성값을 요약해 작은 head를 만듭니다. 위치 자체가 정답을 결정하는 과제에서는 정보 손실을 검토합니다.

**검출:** 물체 위치를 예측하므로 backbone의 다중 해상도 특징을 유지합니다. 작은 물체에 필요한 고해상도 특징을 FPN 등으로 결합합니다. 클래스 분류용 GAP 뒤에는 박스 위치가 충분히 남지 않을 수 있습니다.

**분할:** encoder의 해상도 축소 뒤 decoder에서 복원합니다. U-Net의 skip은 보통 encoder 특징을 decoder 특징과 채널 축으로 **concat**합니다. ResNet의 **add**와 다릅니다. 홀수 해상도 입력은 upsampling 시 skip 크기로 맞춥니다. [U-Net](https://arxiv.org/abs/1505.04597)

**동영상:** 프레임별 CNN 특징 뒤 시간 축 모델을 붙일 수 있습니다. RNN/LSTM은 순서가 있는 입력에 사용하고 hidden state를 서로 다른 영상 샘플 사이에 무분별하게 공유하지 않습니다.

**Transformer:** 한 출발점은 `x + Attention(LayerNorm(x))`, 이어서 `x + MLP(LayerNorm(x))`인 pre-norm block입니다. 원 Transformer의 post-norm 구성과 구분합니다. 토큰 수 증가로 attention의 메모리/연산량이 커지므로 패치 크기와 입력 해상도를 함께 정합니다. [원 Transformer 구조](https://arxiv.org/abs/1706.03762)

## 6. 실험 순서

1. 작은 baseline과 입력/출력 shape를 검증합니다.
2. 학습 손실이 높은 경우 구현 오류, 학습률, capacity를 확인합니다.
3. 학습은 좋고 검증이 나쁘면 누출·분포 차이·증강·규제·모델 축소를 확인합니다.
4. 한 번에 깊이·optimizer·증강을 모두 바꾸지 말고 동일 분할로 비교합니다.
5. 정확도와 함께 latency, peak RAM, 모델 크기를 측정합니다.
