# 딥러닝 기반 영상인식

공경보 교수님의 이론 PDF와 1일차 실습 PPTX를 바탕으로 정리한 학습 문서와 독립적으로 작성한 PyTorch 실습입니다. 함수의 선택 이유, 레이어의 배치, 학습·검증·배포 흐름을 함께 다룹니다.

## 문서 안내

| 문서 | 내용 |
|---|---|
| [Fundamentals.md](Fundamentals.md) | 분류부터 CNN, RNN, Transformer, 검출·분할까지 이론 |
| [Functions_and_Tradeoffs.md](Functions_and_Tradeoffs.md) | 함수별 특징, 장단점, 선택 기준 |
| [Layer_Design_Guide.md](Layer_Design_Guide.md) | 레이어 순서, 출력 크기, 파라미터 수, 과제별 구조 |
| [Embedded_SW_Study.md](Embedded_SW_Study.md) | 데이터 관리, 학습 실험, 임베디드 적용 |
| [Visual_Overview.md](Visual_Overview.md) | Mermaid 구조도 |
| [lab/README.md](lab/README.md) | 실행 가능한 XOR·MNIST·CNN 및 IoU/NMS 코드 |

## 원자료와 정리 범위

- `딥러닝기반영상인식_공경보.pdf`: 731쪽. 아래 쪽수는 PDF의 물리적 페이지이며 슬라이드 하단 번호와 다를 수 있습니다.
- `딥러닝 기반 영상인식(1일차-실습).pptx`: 64장. XOR의 단층/다층 비교, MNIST MLP, Dropout, 데이터 증강 실습입니다.
- 강의에 연결된 [원 실습 저장소](https://github.com/currycurry915/deeplearning_basics/tree/main)는 참고 링크입니다. 이 폴더의 코드는 강의 개념을 바탕으로 새로 작성했으며 원 노트북을 복사하지 않았습니다. 원 PDF/PPTX는 재배포하지 않습니다.

| PDF 쪽수 | 주제 |
|---|---|
| 3–58 | 이미지 분류, kNN, 선형 분류 |
| 59–94 | 손실, Softmax, 과적합, 정규화 |
| 95–186 | 경사하강법, SGD, Momentum, Adam/AdamW, 학습률 |
| 187–270 | Perceptron, MLP, 역전파 |
| 271–300 | 증강, Dropout, Early Stopping, 정규화, MLP 한계 |
| 301–399 | CNN, Inception, ResNet, CNN 구조 |
| 401–492 | RNN, BPTT, LSTM |
| 493–590 | Attention, Transformer |
| 591–672 | IoU, R-CNN 계열, FPN, DETR |
| 673–730 | Semantic/Instance/Panoptic Segmentation, Keypoints |

본문의 **강의 핵심**은 원자료 요약이며, **보완·설계 조언**은 공식 문서와 논문을 참고한 추가 설명입니다. CNN 구현, 검증 분리, 조기 종료, IoU/NMS 코드는 추가 학습 예제입니다. 검출·분할 모델 전체의 학습 구현은 포함하지 않습니다.

## 실습 자료에서 보완한 부분

- PPT의 `F.relu`에는 `torch.nn.functional as F` import가 필요합니다. 구현은 `nn.ReLU`로 구성했습니다.
- XOR 단층 모델은 손실이 조금 줄어도 비선형 결정 경계를 만들 수 없습니다. “학습이 전혀 안 된다”와는 다릅니다.
- 역전파는 미분 계산이고, 경사하강법은 그 미분으로 가중치를 갱신하는 방법입니다.
- `RandomAffine((10, 30))`은 양의 10~30도 회전입니다. ±30도를 뜻하지 않습니다.
- 증강 데이터 20,000개와 원본 60,000개의 결합은 80,000개의 **논리적 항목**입니다. 독립적인 원본 80,000장이나 고정된 새 이미지 파일이 아닙니다.
- 시험 정확도로 Dropout이나 증강을 고르지 않습니다. 검증 세트로 고르고 시험 세트는 마지막에 평가합니다.
- Colab 이용 시간은 오래된 슬라이드의 숫자를 현재 보장으로 취급하지 않습니다.
