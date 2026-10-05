# PyTorch 실습

## 설치와 실행

Python 3.10 이상에서 이 폴더를 작업 디렉터리로 사용합니다. torch/torchvision은 서로 호환되는 버전을 함께 설치합니다. CPU 기준 명령이며 GPU 설치는 장치에 맞는 공식 PyTorch 패키지를 사용합니다.

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python xor.py
python xor.py --lecture-loss
python inspect_layers.py
python -m unittest -v test_lab.py
```

| 파일 | 역할 |
|---|---|
| `xor.py` | 선형/3개 은닉층 XOR 비교. 기본 logits loss, 옵션으로 강의 BCE |
| `models.py` | 강의 MNIST MLP, 작은 CNN, projection residual CNN |
| `train_mnist.py` | 분할, 증강, 학습, 검증, best checkpoint, 마지막 시험 |
| `inspect_layers.py` | 실제 레이어 출력 shape/전체 파라미터 수 |
| `detection_ops.py` | xyxy IoU와 단일 클래스 NMS 학습용 구현 |
| `test_lab.py` | 학습·shape·미분·분할·증강·손실 집계·박스 연산 테스트 |

## MNIST

첫 실행에서만 `--download`를 지정합니다. 데이터와 checkpoint는 업로드 대상이 아닙니다.

```bash
python train_mnist.py --download --model mlp --output-dir runs/mlp
python train_mnist.py --model mlp --dropout 0 --output-dir runs/no_dropout
python train_mnist.py --model mlp --augmentation source --output-dir runs/source
python train_mnist.py --model cnn --augmentation balanced --output-dir runs/cnn
python train_mnist.py --model residual --output-dir runs/residual
```

기본 SGD lr=.01, batch128, 최대15epoch, patience5, seed777입니다. CNN에도 같은 optimizer를 쓴 것은 구조 비교의 출발점이며 최적의 설정이라는 의미는 아닙니다. Dropout 옵션은 MLP에만 적용됩니다. `history.csv`는 epoch별 train/validation loss·accuracy이고 `best.pt`는 검증 손실 최저 가중치와 설정입니다.

```bash
# 다운로드 없이 실행 경로만 검사: 정확도 해석 금지
python train_mnist.py --model cnn --smoke --epochs 2 --output-dir runs/smoke
# 짧은 실제 데이터 실행: 전체 학습 결과와 구분
python train_mnist.py --download --model cnn --epochs 1 --limit-train 2000 --limit-eval 500 --output-dir runs/quick
```

`--device cuda`는 CUDA 지원 환경에서 선택합니다. augmentation은 학습에만 적용하며 시험 데이터로 hyperparameter를 선택하지 않습니다. 기본 전처리는 강의처럼 0~1 ToTensor이고 Normalize는 넣지 않았습니다.

## IoU/NMS 예제

```python
import torch
from detection_ops import box_iou, nms
boxes = torch.tensor([[0., 0., 10., 10.], [1., 1., 9., 9.], [20., 20., 30., 30.]])
scores = torch.tensor([.9, .8, .7])
print(box_iou(boxes, boxes))
print(nms(boxes, scores, threshold=.5))  # tensor([0, 2])
```

좌표는 연속 `x1,y1,x2,y2`이며 픽셀 포함 규칙의 `+1`을 쓰지 않습니다. 퇴화 박스의 IoU는0입니다. NMS는 단일 클래스이며 다중 클래스에는 클래스별 처리가 필요합니다. Python 루프 구현이므로 실제 서비스용 대규모 박스 처리에는 최적화된 연산을 선택합니다. DETR에 이 후처리를 무조건 붙이는 것은 아닙니다.

## 검증 범위

검증 결과는 [VALIDATION.md](VALIDATION.md)에 기록합니다. 합성 데이터 검사, 작은 실제 데이터 실행, 충분히 학습한 전체 MNIST 성능을 구분합니다. 검출·분할의 전체 모델, MCU/NPU 배포, GPU 성능은 이 실습의 검증 범위에 포함하지 않습니다.
