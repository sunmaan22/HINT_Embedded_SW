# 검증 기록

2026-10-05, Windows CPU, Python3.12.14, torch2.14.1+cpu, torchvision0.29.1+cpu에서 실행했습니다. requirements의 모든 하위 버전 조합을 검증한 것은 아닙니다.

## 자동 테스트

`python -m unittest -v test_lab.py`: **9개 통과**.

- XOR MLP는 logits/BCE 두 방식에서 4개 입력을 모두 분류했고 선형 모델은 모두 분류하지 못했습니다.
- MLP/CNN/residual의 출력 shape 및 모든 학습 파라미터의 유한한 gradient를 확인했습니다.
- 문서의 MLP/CNN 파라미터 수를 확인했습니다.
- 홀수 해상도에서 stride2 residual projection의 shape를 확인했습니다.
- Dropout 평가 모드, 재현 가능한 중복 없는 분할, 세 가지 transform의 shape를 확인했습니다.
- 마지막 불균등 배치를 포함한 sample-weighted loss를 확인했습니다.
- IoU, 동일 박스 억제, 떨어진 박스 유지, 빈 입력, 퇴화/역전 좌표를 확인했습니다.

## 실행 경로 검사

Residual CNN 합성 데이터 128/48/48개, 2epoch: 학습·검증·best checkpoint·최종 평가가 정상 완료되었습니다. 합성 데이터의 정확도는 모델 성능 지표가 아닙니다.

실제 MNIST CNN: train2,000 / validation500 / test500, 1epoch, seed777, SGD lr=.01. train loss2.3338, validation loss2.3010, test loss2.3058, test accuracy8.0%. 이는 **짧은 실행 확인 결과**이며 학습이 충분하지 않은 모델입니다. 전체 MNIST의 최종 성능이나 CNN의 구조적 우수성을 입증하지 않습니다. 15epoch 전체 실행 후 별도로 평가해야 합니다.

검증 데이터는 train 원본에서 분리했고 test는 별도 MNIST 시험 데이터의 앞500개입니다. 이 축소 실험은 전체 test의 대표성을 보장하지 않습니다.

원자료 증강 방식의 MLP도 원본256+증강256=512 학습 항목, 검증64, 시험64, 1epoch로 실행을 완료했습니다. 이는 증강의 성능 개선을 입증하는 비교 실험은 아닙니다. CNN·residual·MLP 세 실행에서 생성된 checkpoint를 새 모델로 다시 로딩하고 출력 shape를 확인했습니다.

## 남은 범위

GPU, 완전한15epoch 학습, 검출/분할 전체 모델, 양자화, MCU/NPU 런타임 및 실제 장치 지연은 검증하지 않았습니다. 데이터·checkpoint·로컬 설치 라이브러리는 저장소에 포함하지 않습니다.
