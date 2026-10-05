"""Educational single-class NMS; continuous xyxy coordinates, no +1."""
import torch


def box_iou(boxes1, boxes2):
    for boxes in (boxes1, boxes2):
        if boxes.ndim != 2 or boxes.shape[1] != 4:
            raise ValueError("boxes must have shape [N,4]")
        if not torch.isfinite(boxes).all() or (boxes[:, 2:] < boxes[:, :2]).any():
            raise ValueError("coordinates must be finite ordered xyxy")
    a, b = boxes1.float(), boxes2.float()
    top_left = torch.maximum(a[:, None, :2], b[None, :, :2])
    bottom_right = torch.minimum(a[:, None, 2:], b[None, :, 2:])
    intersection = (bottom_right - top_left).clamp(min=0).prod(-1)
    area_a = (a[:, 2:] - a[:, :2]).prod(-1)
    area_b = (b[:, 2:] - b[:, :2]).prod(-1)
    union = area_a[:, None] + area_b[None, :] - intersection
    return torch.where(union > 0, intersection / union.clamp_min(1e-12), 0.)


def nms(boxes, scores, threshold=.5):
    box_iou(boxes, boxes[:0])  # Validate without allocating an NxN matrix.
    if scores.shape != (len(boxes),) or not torch.isfinite(scores).all():
        raise ValueError("scores must be finite [N]")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in [0,1]")
    if boxes.device != scores.device:
        raise ValueError("boxes and scores must share a device")
    order = scores.argsort(descending=True, stable=True)
    keep = []
    while order.numel():
        current = order[0]
        keep.append(current)
        remaining = order[1:]
        overlap = box_iou(boxes[current].unsqueeze(0), boxes[remaining])[0]
        order = remaining[overlap <= threshold]
    return torch.stack(keep) if keep else torch.empty(0, dtype=torch.long, device=boxes.device)
