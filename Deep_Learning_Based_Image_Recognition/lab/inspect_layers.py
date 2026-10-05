"""Print actual leaf-layer tensor shapes and trainable parameter counts."""
import torch
from models import build_model


if __name__ == "__main__":
    torch.set_num_threads(1)
    for name in ("mlp", "cnn", "residual"):
        model = build_model(name).eval()
        print(f"\n{name}: parameters={sum(p.numel() for p in model.parameters())}")
        handles = []
        for path, layer in model.named_modules():
            if not list(layer.children()):
                def report(module, inputs, output, path=path):
                    print(f"{path:16} {type(module).__name__:18} {tuple(output.shape)}")
                handles.append(layer.register_forward_hook(report))
        with torch.no_grad():
            model(torch.zeros(2, 1, 28, 28))
        for handle in handles:
            handle.remove()
