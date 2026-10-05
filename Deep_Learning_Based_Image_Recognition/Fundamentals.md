# Fundamentals — 영상인식의 기본 원리

## 1. 분류와 표현

**강의 핵심 · PDF 3–58:** 분류는 입력 이미지에서 클래스 점수를 계산하는 문제입니다. kNN은 학습 샘플을 저장하고 가까운 샘플들의 레이블로 예측합니다. 학습은 간단하지만 예측할 때 많은 거리 계산과 저장 공간이 필요합니다. 픽셀 거리만 쓰면 이동·밝기 변화에 취약합니다. k와 거리 척도는 검증 데이터로 선택합니다.

선형 분류기는 `s = Wx + b`를 계산합니다. 모든 픽셀을 펼치면 위치별 가중치는 학습하지만 인접 픽셀의 공간 구조를 직접 활용하지 않습니다. XOR처럼 직선으로 나눌 수 없는 데이터에는 비선형 은닉층이 필요합니다.

## 2. 손실과 출력

**강의 핵심 · PDF 59–94:** 손실은 예측이 정답과 얼마나 다른지 수치화합니다. Softmax는 클래스 점수를 합이 1인 확률로 바꾸며, 교차 엔트로피는 정답 클래스에 낮은 확률을 주면 큰 손실을 냅니다. 정규화는 모델의 복잡성을 제한해 과적합을 줄입니다.

**보완:** 다중 클래스 학습에서 `CrossEntropyLoss`에는 Softmax 이전 logits를 전달합니다. 정답은 보통 클래스 인덱스 `long` 텐서입니다. 이진 분류에는 `BCEWithLogitsLoss`와 하나의 raw logit을 조합하면 Sigmoid와 BCE를 별도로 계산하는 것보다 수치적으로 안정적입니다. 추론 때만 Sigmoid/Softmax를 적용합니다. [CrossEntropyLoss](https://docs.pytorch.org/docs/2.14/generated/torch.nn.CrossEntropyLoss.html), [BCEWithLogitsLoss](https://docs.pytorch.org/docs/2.14/generated/torch.nn.BCEWithLogitsLoss.html)

## 3. 역전파와 최적화

**강의 핵심 · PDF 95–270:** 순전파로 손실을 구하고 연쇄 법칙으로 각 파라미터의 미분을 계산합니다. SGD는 미니배치의 미분을 사용해 갱신합니다. Momentum은 갱신 방향을 누적하고, AdaGrad는 누적 제곱 미분으로 보폭을 조절합니다. RMSProp은 지수 이동 평균을 쓰며, Adam은 미분과 미분 제곱의 이동 평균 및 편향 보정을 결합합니다.

학습 루프는 `zero_grad → forward → loss → backward → step`입니다. 미분은 기본적으로 누적되므로 의도적 gradient accumulation이 아니면 매 배치 초기화합니다. Gradient clipping은 폭주하는 미분의 크기를 제한하지만 잘못된 데이터나 과도한 학습률을 고치는 만능 수단은 아닙니다.

**보완:** Adam에서 L2 페널티와 weight decay를 동일하게 취급하면 적응적 갱신과 상호작용합니다. AdamW는 weight decay를 분리합니다. SGD와 AdamW 중 우열을 고정하지 말고 같은 검증 기준으로 비교합니다. [AdamW](https://docs.pytorch.org/docs/2.14/generated/torch.optim.AdamW.html)

## 4. 일반화

**강의 핵심 · PDF 271–300:** 증강은 레이블을 유지하는 입력 변화를 만들어 데이터 다양성을 늘립니다. Dropout은 학습 중 일부 활성값을 무작위로 끄며, Early Stopping은 검증 성능이 악화되는 시점의 과적합을 제한합니다. 정규화 레이어는 학습을 안정화하는 데 쓰입니다.

**보완:** 모든 변환이 모든 과제에 적합하지는 않습니다. 숫자를 뒤집거나 크게 돌리면 6/9의 의미가 바뀔 수 있습니다. 검증·시험에는 무작위 증강을 적용하지 않습니다. 같은 원본의 증강본을 서로 다른 분할에 넣으면 데이터 누출이 발생합니다.

## 5. CNN

**강의 핵심 · PDF 301–399:** Convolution은 작은 커널을 여러 위치에 공유해 지역 특징을 추출합니다. Pooling/stride는 공간 크기를 줄입니다. 초기층은 경계·질감, 더 깊은 층은 복합 패턴을 학습할 수 있지만 특정 채널의 의미가 항상 고정되는 것은 아닙니다.

Inception은 서로 다른 수용 영역을 병렬로 사용하고 1×1 convolution으로 채널을 줄여 비용을 조절합니다. ResNet은 `y = x + F(x)`의 잔차 연결로 깊은 모델의 최적화를 돕습니다. 단순히 층을 늘리는 것만으로 성능이 개선되지는 않습니다. [ResNet 논문](https://arxiv.org/abs/1512.03385)

## 6. RNN, LSTM, Attention

**강의 핵심 · PDF 401–590:** RNN은 시간마다 같은 가중치를 사용해 이전 은닉 상태와 현재 입력을 처리합니다. BPTT는 시간 축으로 역전파하며 긴 시퀀스에는 미분 소실·폭주 문제가 있습니다. Truncated BPTT는 역전파 길이를 제한합니다. LSTM은 게이트와 셀 상태로 정보의 유지·삭제를 조절합니다.

Attention은 필요한 위치의 정보를 가중합합니다. Scaled dot-product attention은 `softmax(QKᵀ / sqrt(d_k))V`입니다. Transformer는 attention, 위치 정보, MLP, 정규화, 잔차 연결을 조합합니다. Padding mask와 causal mask는 목적이 다릅니다. 영상 패치에 적용할 때도 위치 정보를 보존해야 합니다. [Transformer 논문](https://arxiv.org/abs/1706.03762)

## 7. 검출과 분할

**강의 핵심 · PDF 591–730:** 분류는 이미지 전체의 클래스를, 검출은 클래스와 박스를, semantic segmentation은 픽셀별 클래스를 예측합니다. Instance segmentation은 같은 클래스의 개체도 구분하며 panoptic segmentation은 개체와 배경 영역을 함께 다룹니다.

- IoU: 교집합 면적 / 합집합 면적. 박스 형식과 좌표 기준을 일치시킵니다.
- R-CNN 계열: 후보 영역 기반 검출. Fast R-CNN은 특징 맵을 공유하고 Faster R-CNN은 후보 생성도 학습합니다.
- FPN: 서로 다른 해상도의 특징을 결합해 다양한 크기의 물체를 다룹니다.
- DETR: query와 set prediction 및 matching을 사용합니다. 일반적인 NMS 기반 검출 흐름과 구분합니다.
- Mask R-CNN: 박스·클래스와 함께 개체별 mask를 예측합니다.

**보완:** 검출·분할은 분류 코드의 마지막 Linear만 바꿔 해결되지 않습니다. 박스/마스크 정답, 해당 손실, 증강 시 좌표 변환, mAP/IoU/Dice 등의 평가를 함께 설계해야 합니다.
