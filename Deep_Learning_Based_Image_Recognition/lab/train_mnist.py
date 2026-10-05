"""Train/validation split before augmentation; test once after best restore."""
import argparse
import copy
import csv
from pathlib import Path
import torch
from torch import nn
from torch.utils.data import ConcatDataset, DataLoader, Subset, TensorDataset
from torchvision import datasets, transforms
from models import build_model


def split_indices(size, val_size, seed):
    if not 0 < val_size < size:
        raise ValueError("validation size must be between 1 and dataset size-1")
    order = torch.randperm(size, generator=torch.Generator().manual_seed(seed)).tolist()
    return order[val_size:], order[:val_size]


def transform_for(mode):
    if mode == "source":
        return transforms.Compose([transforms.RandomAffine((10, 30)),
                                   transforms.GaussianBlur(3), transforms.ToTensor()])
    if mode == "balanced":
        return transforms.Compose([transforms.RandomAffine(15, translate=(.08, .08)),
                                   transforms.ToTensor()])
    if mode == "none":
        return transforms.ToTensor()
    raise ValueError(mode)


def make_data(args):
    if args.smoke:
        # Synthetic data checks execution only, not recognition performance.
        generator = torch.Generator().manual_seed(args.seed)
        def fake(n):
            return TensorDataset(torch.rand(n, 1, 28, 28, generator=generator),
                                 torch.randint(10, (n,), generator=generator))
        return fake(128), fake(48), fake(48)
    plain = datasets.MNIST(args.data_dir, train=True, download=args.download,
                           transform=transform_for("none"))
    train_indices, val_indices = split_indices(len(plain), args.val_size, args.seed)
    if args.limit_train:
        train_indices = train_indices[:args.limit_train]
    if args.limit_eval:
        val_indices = val_indices[:args.limit_eval]
    train = Subset(plain, train_indices)
    if args.augmentation != "none":
        augmented = datasets.MNIST(args.data_dir, train=True, download=False,
                                   transform=transform_for(args.augmentation))
        if args.augmentation == "source":
            train = ConcatDataset([train, Subset(augmented, train_indices[:20000])])
        else:
            train = Subset(augmented, train_indices)
    test = datasets.MNIST(args.data_dir, train=False, download=args.download,
                          transform=transform_for("none"))
    if args.limit_eval:
        test = Subset(test, range(min(args.limit_eval, len(test))))
    return train, Subset(plain, val_indices), test


def run_epoch(model, loader, device, optimizer=None):
    training = optimizer is not None
    model.train(training)
    total_loss, correct, count = 0., 0, 0
    with torch.set_grad_enabled(training):
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            if training:
                optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = nn.functional.cross_entropy(logits, labels)
            if training:
                loss.backward()
                optimizer.step()
            count += labels.numel()
            total_loss += loss.item() * labels.numel()
            correct += (logits.argmax(1) == labels).sum().item()
    if not count:
        raise ValueError("empty dataset")
    return total_loss / count, correct / count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["mlp", "cnn", "residual"], default="mlp")
    parser.add_argument("--dropout", type=float, default=.2)
    parser.add_argument("--augmentation", choices=["none", "source", "balanced"], default="none")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=.01)
    parser.add_argument("--seed", type=int, default=777)
    parser.add_argument("--val-size", type=int, default=10000)
    parser.add_argument("--limit-train", type=int, default=0)
    parser.add_argument("--limit-eval", type=int, default=0)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output-dir", default="runs/mnist")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if min(args.epochs, args.patience, args.batch_size, args.threads) < 1 or args.lr <= 0:
        parser.error("epochs/patience/batch-size/threads/lr must be positive")
    if not 0 <= args.dropout < 1 or min(args.limit_train, args.limit_eval) < 0:
        parser.error("dropout must be in [0,1), limits must be nonnegative")
    if args.smoke and args.augmentation != "none":
        parser.error("smoke uses synthetic tensors; augmentation requires MNIST")
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    device = torch.device(args.device)
    train, val, test = make_data(args)
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(train, args.batch_size, shuffle=True, generator=generator)
    val_loader = DataLoader(val, args.batch_size)
    test_loader = DataLoader(test, args.batch_size)
    model = build_model(args.model, args.dropout).to(device)
    optimizer = torch.optim.SGD(model.parameters(), lr=args.lr)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    best_loss, best_state, stale = float("inf"), None, 0
    print(f"sizes: train={len(train)}, val={len(val)}, test={len(test)}, synthetic={args.smoke}")
    with (output / "history.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["epoch", "train_loss", "train_accuracy", "val_loss", "val_accuracy"])
        for epoch in range(1, args.epochs + 1):
            train_metrics = run_epoch(model, train_loader, device, optimizer)
            val_metrics = run_epoch(model, val_loader, device)
            writer.writerow([epoch, *train_metrics, *val_metrics])
            print(f"epoch={epoch} train={train_metrics} val={val_metrics}")
            if val_metrics[0] < best_loss:
                best_loss, stale = val_metrics[0], 0
                best_state = copy.deepcopy(model.state_dict())
                torch.save({"model": {k: v.cpu() for k, v in best_state.items()},
                            "args": vars(args), "epoch": epoch,
                            "val_loss": best_loss}, output / "best.pt")
            else:
                stale += 1
            if stale >= args.patience:
                break
    if best_state is None:
        raise RuntimeError("No finite validation loss; check inputs and learning rate")
    model.load_state_dict(best_state)
    print(f"test_once={run_epoch(model, test_loader, device)}")


if __name__ == "__main__":
    main()
