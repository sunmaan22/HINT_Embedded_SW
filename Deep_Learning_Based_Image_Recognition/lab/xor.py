"""Compare linear and sigmoid-hidden-layer XOR classifiers."""
import argparse
import torch
from torch import nn


def fit_xor(kind="mlp", epochs=10000, seed=777, lecture_loss=False):
    torch.manual_seed(seed)
    x = torch.tensor([[0., 0.], [0., 1.], [1., 0.], [1., 1.]])
    y = torch.tensor([[0.], [1.], [1.], [0.]])
    layers = [nn.Linear(2, 1)] if kind == "linear" else [
        nn.Linear(2, 10), nn.Sigmoid(), nn.Linear(10, 10), nn.Sigmoid(),
        nn.Linear(10, 10), nn.Sigmoid(), nn.Linear(10, 1)]
    if lecture_loss:
        layers.append(nn.Sigmoid())
    model = nn.Sequential(*layers)
    criterion = nn.BCELoss() if lecture_loss else nn.BCEWithLogitsLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0)
    for _ in range(epochs):
        optimizer.zero_grad(set_to_none=True)
        loss = criterion(model(x), y)
        loss.backward()
        optimizer.step()
    model.eval()
    with torch.no_grad():
        output = model(x)
        probability = output if lecture_loss else output.sigmoid()
        loss = criterion(output, y).item()
        accuracy = ((probability > .5) == y.bool()).float().mean().item()
    return loss, accuracy, probability.flatten().tolist()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=10000)
    parser.add_argument("--lecture-loss", action="store_true")
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("epochs must be positive")
    torch.set_num_threads(1)
    for kind in ("linear", "mlp"):
        loss, accuracy, probability = fit_xor(kind, args.epochs,
                                               lecture_loss=args.lecture_loss)
        print(f"{kind}: loss={loss:.6f}, accuracy={accuracy:.2%}, probabilities={probability}")
