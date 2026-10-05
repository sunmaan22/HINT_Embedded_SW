import unittest
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from PIL import Image
from models import build_model, ResidualBlock
from train_mnist import split_indices, transform_for, run_epoch
from detection_ops import box_iou, nms
from xor import fit_xor


class LabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_xor_learning_and_linear_limit(self):
        self.assertEqual(fit_xor("mlp")[1], 1.)
        self.assertLess(fit_xor("linear")[1], 1.)
        self.assertEqual(fit_xor("mlp", lecture_loss=True)[1], 1.)

    def test_classifier_shapes_and_gradients(self):
        for name in ("mlp", "cnn", "residual"):
            model = build_model(name)
            logits = model(torch.randn(3, 1, 28, 28))
            self.assertEqual(tuple(logits.shape), (3, 10))
            nn.functional.cross_entropy(logits, torch.tensor([0, 1, 2])).backward()
            self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all()
                                for p in model.parameters()))

    def test_parameter_counts(self):
        self.assertEqual(sum(p.numel() for p in build_model("mlp").parameters()), 669706)
        self.assertEqual(sum(p.numel() for p in build_model("cnn").parameters()), 19562)

    def test_residual_projection_odd_size(self):
        self.assertEqual(tuple(ResidualBlock(16, 32, 2)(torch.randn(2, 16, 15, 15)).shape),
                         (2, 32, 8, 8))

    def test_dropout_eval(self):
        dropout = nn.Dropout(.5)
        x = torch.ones(1000)
        self.assertFalse(torch.equal(dropout(x), x))
        dropout.eval()
        self.assertTrue(torch.equal(dropout(x), x))

    def test_split_no_leak_and_reproducible(self):
        train, val = split_indices(100, 20, 777)
        self.assertFalse(set(train) & set(val))
        self.assertEqual(len(set(train) | set(val)), 100)
        self.assertEqual((train, val), split_indices(100, 20, 777))

    def test_transforms(self):
        image = Image.new("L", (28, 28), 128)
        for mode in ("none", "source", "balanced"):
            tensor = transform_for(mode)(image)
            self.assertEqual(tuple(tensor.shape), (1, 28, 28))
            self.assertTrue(torch.isfinite(tensor).all())

    def test_weighted_loss_with_uneven_batch(self):
        logits = torch.tensor([[4., 0.], [4., 0.], [0., 4.]])
        labels = torch.zeros(3, dtype=torch.long)
        loader = DataLoader(TensorDataset(logits, labels), batch_size=2)
        loss, accuracy = run_epoch(nn.Identity(), loader, torch.device("cpu"))
        self.assertAlmostEqual(loss, nn.functional.cross_entropy(logits, labels).item(), places=6)
        self.assertAlmostEqual(accuracy, 2 / 3)

    def test_iou_nms(self):
        boxes = torch.tensor([[0., 0., 2., 2.], [0., 0., 2., 2.], [3., 3., 4., 4.]])
        self.assertTrue(torch.equal(box_iou(boxes, boxes),
                                    torch.tensor([[1., 1., 0.], [1., 1., 0.], [0., 0., 1.]])))
        self.assertEqual(nms(boxes, torch.tensor([.9, .8, .7])).tolist(), [0, 2])
        self.assertEqual(nms(torch.empty(0, 4), torch.empty(0)).numel(), 0)
        self.assertEqual(box_iou(torch.zeros(1, 4), torch.zeros(1, 4)).item(), 0.)
        with self.assertRaises(ValueError):
            box_iou(torch.tensor([[2., 0., 1., 3.]]), boxes)


if __name__ == "__main__":
    unittest.main()
