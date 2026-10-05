# 함수별 특징과 장단점

PyTorch 기준입니다. 기본값 자체보다 입력·출력의 의미를 먼저 확인합니다. 아래 선택 조언은 강의 내용에 대한 보완입니다.

## 활성화 함수

| 함수 | 특징·장점 | 단점·주의 | 위치·선택 |
|---|---|---|---|
| `nn.Sigmoid` | 0~1, 이진 확률 해석 | 큰 절댓값에서 포화·미분 소실 | 이진 추론 출력. 은닉층은 XOR 강의 재현 목적 |
| `nn.Tanh` | -1~1, 0 중심 | 포화하면 미분 소실 | RNN 상태/후보 상태 등에 사용 |
| `nn.ReLU` | 간단하고 양수 영역의 미분 유지 | 음수 영역의 미분 0, 죽은 뉴런 가능 | CNN/MLP 은닉층 기본 출발점 |
| `nn.LeakyReLU` | 음수에서도 작은 미분 | 음수 기울기 선택 필요 | ReLU의 비활성 문제가 관찰될 때 비교 |
| `nn.GELU` | 부드러운 게이팅, Transformer에서 널리 사용 | ReLU보다 계산 복잡 | Transformer MLP 등에 사용 |
| `torch.softmax` | 상호 배타적 클래스 확률 | 차원 오류, CE 앞 중복 적용 | 추론에서 클래스 축 `dim=1` |

## 손실과 최적화

| 함수 | 장점 | 단점·주의 | 입력 |
|---|---|---|---|
| `nn.BCELoss` | 확률 기반 이진 손실, PPT 재현 | 확률을 먼저 계산해야 함 | Sigmoid 출력, float 정답 |
| `nn.BCEWithLogitsLoss` | Sigmoid+BCE를 안정적으로 결합 | 확률을 넣으면 의미가 달라짐 | raw logits, 같은 shape의 float 정답 |
| `nn.CrossEntropyLoss` | 다중 클래스 분류 표준 | 보통 정답이 one-hot이 아닌 long 인덱스 | `[N,C]` logits, `[N]` labels |
| `nn.MSELoss` | 회귀에 단순 | 큰 오차에 민감, 분류 확률용 기본 선택 아님 | 연속값, 동일 shape |
| `optim.SGD` | 단순, 작은 상태 메모리 | 학습률·schedule에 민감 | momentum을 선택적으로 사용 |
| `optim.Adam` | 파라미터별 보폭 적응 | 추가 상태 메모리, 자동 일반화 보장 없음 | 빠른 실험 출발점 |
| `optim.AdamW` | weight decay와 적응적 갱신 분리 | decay 설정 필요 | norm/bias decay 제외는 별도 설계 |
| `clip_grad_norm_` | 전체 미분 norm 상한 | 너무 작은 상한은 학습 방해 | `backward` 뒤, `step` 앞 |

공식 입력 정의: [CE](https://docs.pytorch.org/docs/2.14/generated/torch.nn.CrossEntropyLoss.html), [BCE logits](https://docs.pytorch.org/docs/2.14/generated/torch.nn.BCEWithLogitsLoss.html), [AdamW](https://docs.pytorch.org/docs/2.14/generated/torch.optim.AdamW.html).

## 레이어와 정규화

| 함수 | 장점 | 단점·주의 | 배치 방법 |
|---|---|---|---|
| `nn.Linear` | 특징 벡터 결합 | 큰 이미지 flatten 시 파라미터 급증 | MLP 또는 분류 head |
| `nn.Conv2d` | 공간 구조와 가중치 공유 | 커널·stride·padding 계산 필요 | backbone의 지역 특징 추출 |
| 1×1 `Conv2d` | 채널 혼합·축소, projection | 단독으로 공간 이웃을 보지 않음 | bottleneck/skip 채널 맞춤 |
| depthwise + pointwise | 일반 conv보다 곱셈/파라미터 절약 가능 | 실제 속도는 런타임 지원에 좌우 | 모바일 backbone, 측정 후 선택 |
| `nn.MaxPool2d` | 강한 활성 보존, 다운샘플 | 위치·작은 특징 손실 | 몇 개 conv 뒤, 과도한 축소 금지 |
| `nn.AdaptiveAvgPool2d(1)` | 입력 크기에 덜 종속적인 작은 head | 공간 배치 정보 손실 | 분류 마지막, 검출/분할 출력에는 부적합 |
| `nn.Flatten` | 이미지→벡터 변환 | 공간 관계를 펼침 | MLP 입력 또는 head 앞 |
| `nn.Dropout` | 과적합 완화 | 학습 지연·과도하면 underfit | MLP 은닉 활성 뒤, 최종 logits 뒤에는 보통 넣지 않음 |
| `nn.BatchNorm2d` | 채널별 정규화, CNN 학습 안정화 | batch 통계에 영향, train/eval 차이 | 보통 Conv→BN→ReLU |
| `nn.LayerNorm` | 샘플 내부 마지막 차원 정규화 | normalized_shape 지정 중요 | Transformer 토큰 특징 축 |
| `nn.GroupNorm` | batch 크기에 덜 의존 | 채널 수가 그룹 수로 나누어져야 함 | 작은 batch CNN의 비교 후보 |
| `nn.InstanceNorm2d` | 샘플·채널별 공간 정규화 | 색/강도 통계가 중요한 과제에 불리할 수 있음 | 스타일 변환 등 목적에 맞춰 선택 |
| `F.interpolate` | 출력 해상도 복원, 간단 | 새로운 세부정보를 스스로 만들지 않음 | decoder에서 skip과 해상도 맞춤 |
| `nn.ConvTranspose2d` | 학습 가능한 upsampling | 설정에 따라 checkerboard artifact | decoder, interpolate+conv와 비교 |

BatchNorm은 학습 통계와 평가 시 running statistics의 차이를 이해해야 합니다. [공식 BatchNorm2d](https://docs.pytorch.org/docs/2.14/generated/torch.nn.BatchNorm2d.html). 경량 convolution 개념: [MobileNet](https://arxiv.org/abs/1704.04861).

## 데이터와 증강

| 함수 | 특징·장점 | 단점·주의 |
|---|---|---|
| `transforms.Compose` | 변환 순서를 명시 | PIL/텐서 변환 순서 오류 가능 |
| `ToTensor` | 일반 uint8 이미지를 float CHW, 0~1로 변환 | 모든 dtype 입력을 동일하게 scale하는 것은 아님 |
| `Normalize(mean,std)` | 채널별 scale 표준화 | mean/std와 순서를 배포에도 동일 적용 |
| `RandomAffine` | 회전·이동·크기 변화 | 레이블 보존 범위를 선택, `(10,30)`은 양의 회전 |
| `GaussianBlur` | 흐림 변화 | kernel은 영역, sigma가 blur 강도; 숫자 획 소실 가능 |
| `RandomCrop` | 위치 변화 | 물체를 잘라 정답 의미 훼손 가능 |
| `ColorJitter` | 밝기/대비 등 변화 | 색이 클래스 의미인 과제에서는 제한 |
| `RandomInvert` | 명암 반전 | 실제 운용 분포와 다르면 성능 악화 |
| `RandomErasing` | 가림에 대한 강건성 비교 | 텐서 입력 필요, 적용 후 정규화 권장 |
| `Subset` | 같은 dataset의 일부 인덱스 선택 | 원본/증강 dataset의 인덱스 분할 일치 필요 |
| `ConcatDataset` | 여러 dataset을 논리적으로 연결 | 독립 표본 수 증가와 혼동하지 않음 |
| `DataLoader` | 배치·shuffle·worker 관리 | Windows worker 사용 시 main guard 필요 |

PPT의 `p=1` 예시는 항상 적용되는 변환 시연입니다. 그대로 모두 학습에 추가하지 않습니다. [RandomAffine](https://docs.pytorch.org/vision/stable/generated/torchvision.transforms.RandomAffine.html), [GaussianBlur](https://docs.pytorch.org/vision/stable/generated/torchvision.transforms.GaussianBlur.html), [변환 예제](https://docs.pytorch.org/vision/stable/auto_examples/transforms/index.html).

## 학습 API

| API | 용도 | 흔한 실수 |
|---|---|---|
| `model.train()` | Dropout/BN의 학습 동작 | gradient 활성화와 동일하다고 생각 |
| `model.eval()` | 평가 동작으로 전환 | 자동으로 미분 계산을 끈다고 생각 |
| `torch.no_grad()` | 미분 그래프 없이 평가 | eval 호출을 대체한다고 생각 |
| `loss.backward()` | 미분 계산 | 파라미터 갱신까지 된다고 생각 |
| `optimizer.step()` | 계산된 미분으로 갱신 | backward보다 먼저 호출 |
| `detach().cpu().numpy()` | 그래프 분리 후 CPU 배열 | GPU/미분 텐서에서 바로 numpy 호출 |
| `state_dict()` | 가중치·buffer 저장 | 참조만 보관하면 이후 학습에 함께 바뀜; best 복사 필요 |
