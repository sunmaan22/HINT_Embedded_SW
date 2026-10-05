"""Lecture MLP and supplementary CNNs. All classifiers return raw logits."""
from torch import nn


class MNISTMLP(nn.Sequential):
    def __init__(self, dropout=0.2):
        super().__init__(nn.Flatten(), nn.Linear(784, 512), nn.ReLU(),
                         nn.Dropout(dropout), nn.Linear(512, 512), nn.ReLU(),
                         nn.Dropout(dropout), nn.Linear(512, 10))


def conv_block(cin, cout, stride=1):
    return nn.Sequential(nn.Conv2d(cin, cout, 3, stride, 1, bias=False),
                         nn.BatchNorm2d(cout), nn.ReLU())


class SmallCNN(nn.Sequential):
    def __init__(self):
        super().__init__(conv_block(1, 32), nn.MaxPool2d(2),
                         conv_block(32, 64), nn.MaxPool2d(2),
                         nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(64, 10))


class ResidualBlock(nn.Module):
    def __init__(self, cin, cout, stride=1):
        super().__init__()
        self.main = nn.Sequential(conv_block(cin, cout, stride),
                                  nn.Conv2d(cout, cout, 3, padding=1, bias=False),
                                  nn.BatchNorm2d(cout))
        self.skip = (nn.Identity() if cin == cout and stride == 1 else
                     nn.Sequential(nn.Conv2d(cin, cout, 1, stride, bias=False),
                                   nn.BatchNorm2d(cout)))
        self.activation = nn.ReLU()

    def forward(self, x):
        return self.activation(self.main(x) + self.skip(x))


class ResidualCNN(nn.Sequential):
    def __init__(self):
        super().__init__(conv_block(1, 16), ResidualBlock(16, 16),
                         ResidualBlock(16, 32, 2), ResidualBlock(32, 64, 2),
                         nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(64, 10))


def build_model(name, dropout=0.2):
    if name == "mlp":
        return MNISTMLP(dropout)
    if name == "cnn":
        return SmallCNN()
    if name == "residual":
        return ResidualCNN()
    raise ValueError(f"Unknown model: {name}")
