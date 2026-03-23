"""
Cartoonification pipeline designed to be robust for low-resolution inputs.

Steps:
1) Optional smart upscale for tiny sources (bicubic + mild sharpening).
2) Edge-preserving smoothing (bilateral/median/gaussian).
3) Color quantization (K-Means via OpenCV OR Median Cut via PIL).
4) Edge extraction with adaptive threshold, thickness control via dilation.
5) Composite edges on quantized base using 'multiply' style darkening.

All operations are in BGR (OpenCV) unless noted.
"""

from typing import Tuple
import cv2
import numpy as np
from PIL import Image


# -----------------------------
# I/O helpers
# -----------------------------
def load_image_bgr(path: str) -> np.ndarray:
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Unable to read image")
    return img


def save_image_bgr(img: np.ndarray, path: str) -> None:
    # Use imencode to handle unicode paths cross-platform
    ext = path.split(".")[-1].lower()
    ok, buf = cv2.imencode(f".{ext}", img)
    if not ok:
        raise ValueError("Failed to encode image")
    buf.tofile(path)


# -----------------------------
# Resizing utilities
# -----------------------------
def resize_long_side(bgr: np.ndarray, long_side: int) -> np.ndarray:
    h, w = bgr.shape[:2]
    if long_side <= 0:
        return bgr
    scale = long_side / max(h, w)
    if abs(scale - 1.0) < 1e-6:
        return bgr
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    interp = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
    return cv2.resize(bgr, (new_w, new_h), interpolation=interp)


def smart_upscale_if_small(bgr: np.ndarray, target_long: int) -> np.ndarray:
    h, w = bgr.shape[:2]
    if max(h, w) >= target_long:
        return bgr
    # 1) upscale to target long side
    up = resize_long_side(bgr, target_long)
    # 2) mild unsharp mask to counter bicubic softness
    blur = cv2.GaussianBlur(up, (0, 0), sigmaX=1.0)
    sharp = cv2.addWeighted(up, 1.10, blur, -0.10, 0)
    return sharp


# -----------------------------
# Smoothing
# -----------------------------
def smooth(bgr: np.ndarray, kind: str) -> np.ndarray:
    kind = (kind or "bilateral").lower()
    if kind == "median":
        # Heavy median for a chunky/oil-paint style
        return cv2.medianBlur(bgr, 13)
    if kind == "gaussian":
        # Strong gaussian for a soft, out-of-focus dreamy style
        return cv2.GaussianBlur(bgr, (21, 21), 0)
    
    # default: bilateral edge-preserving
    # Apply multiple passes for a strong "painted" and "flattened" look
    tmp = bgr.copy()
    for _ in range(2):
        tmp = cv2.bilateralFilter(tmp, d=9, sigmaColor=75, sigmaSpace=75)
    return tmp


# -----------------------------
# Quantization
# -----------------------------
def quantize_kmeans(bgr: np.ndarray, k: int) -> np.ndarray:
    # convert to data for kmeans
    Z = bgr.reshape((-1, 3)).astype(np.float32)
    # Stop either at 10 iterations or epsilon
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    # KMeans++ centers improves stability
    attempts = 1
    flags = cv2.KMEANS_PP_CENTERS
    _, labels, centers = cv2.kmeans(Z, k, None, criteria, attempts, flags)
    centers = np.uint8(np.clip(centers, 0, 255))
    quant = centers[labels.flatten()]
    return quant.reshape(bgr.shape)


def quantize_mediancut(bgr: np.ndarray, k: int) -> np.ndarray:
    # Use PIL's MedianCut via paletted quantize
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    # Apply dithering to Median Cut to make it visually distinct from flat K-Means (Retro/GIF style)
    q = pil.quantize(colors=int(k), method=Image.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
    out = q.convert("RGB")
    return cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)


def quantize(bgr: np.ndarray, k: int, method: str) -> np.ndarray:
    method = (method or "kmeans").lower()
    k = max(2, int(k))
    if method == "mediancut":
        return quantize_mediancut(bgr, k)
    return quantize_kmeans(bgr, k)


# -----------------------------
# Edge extraction + composite
# -----------------------------
def extract_edges(bgr: np.ndarray, thickness: float) -> np.ndarray:
    """
    Return a 0..255 single-channel edge mask where white=edges.
    thickness: ~0.1..1.0 user input. We map to dilation size.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # Edge-friendly blur beforehand to reduce noise
    g = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=5)

    # Adaptive threshold gives inking effect across luminance
    th = cv2.adaptiveThreshold(
        g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 7, 2
    )

    # Invert so edges are black later; but we return white edges mask
    edges = cv2.bitwise_not(th)

    # Control thickness by dilation kernel mapped from thickness
    # Map 0.1..1.0 to kernel 1..3
    k = 1 + int(round(np.interp(thickness, [0.1, 1.0], [0, 2])))
    if k > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        edges = cv2.dilate(edges, kernel, iterations=1)

    return edges


def composite_edges(base_bgr: np.ndarray, edges_white: np.ndarray) -> np.ndarray:
    """
    Darken edges onto base. edges_white=255 on edges.
    Implementation: multiply-like blend with an edge opacity.
    """
    # Convert edges to 0..1 opacity map
    alpha = (edges_white.astype(np.float32) / 255.0)  # 1 at edges, 0 elsewhere
    # Edge darkness factor (how much darker than base)
    edge_dark = 0.65  # keep readable on light themes
    # Build a darkened version of base
    dark = (base_bgr.astype(np.float32) * edge_dark).astype(np.uint8)
    # Linear interpolate: where alpha=1 use dark, else base
    out = (dark.astype(np.float32) * alpha[..., None] +
           base_bgr.astype(np.float32) * (1.0 - alpha[..., None]))
    return np.clip(out, 0, 255).astype(np.uint8)


# -----------------------------
# Main pipeline
# -----------------------------
def cartoonify_image(
    src_bgr: np.ndarray,
    *,
    blur_type: str = "bilateral",
    quantizer: str = "kmeans",
    num_colors: int = 8,
    line_strength: float = 0.5,
    target_long_side: int = 1024,
    upscale_small: bool = True,
) -> np.ndarray:
    """
    Orchestrates a full run. Designed to work well on low-res inputs.
    """
    if src_bgr is None or src_bgr.size == 0:
        raise ValueError("Empty image")

    # 0) Smart upscale for tiny images first (prevents thick pixelation)
    work = src_bgr.copy()
    if upscale_small:
        work = smart_upscale_if_small(work, max(512, target_long_side))

    # 1) Resize to target processing size (stable math for later steps)
    work = resize_long_side(work, target_long_side)

    # 2) Edge-preserving smooth
    sm = smooth(work, blur_type)

    # 3) Color quantization
    quant = quantize(sm, num_colors, quantizer)

    # 4) Edge detection
    edges = extract_edges(sm, thickness=float(line_strength))

    # 5) Composite
    out = composite_edges(quant, edges)

    return out
