"""Standalone entry point: runs in .venv-paddle, never imports the Flask app."""
import json
import os
from pathlib import Path
import sys


def collect_results(results):
    lines, tokens = [], []
    for result in results:
        texts = result.get("rec_texts")
        polygons = result.get("rec_polys")
        if not isinstance(texts, list) or any(not isinstance(text, str) for text in texts):
            raise ValueError("Unsupported PaddleOCR output")
        lines.extend(texts)
        if polygons is None or len(polygons) != len(texts):
            raise ValueError("PaddleOCR boxes unavailable")
        for text, polygon in zip(texts, polygons):
            points = polygon.tolist() if hasattr(polygon, "tolist") else polygon
            xs, ys = [float(point[0]) for point in points], [float(point[1]) for point in points]
            tokens.append({"text": text, "box": [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]})
    return {"text": "\n".join(lines), "tokens": tokens}


def main():
    image, output, models = map(Path, sys.argv[1:4])
    # No remote models, orientation classifiers, or unwarping downloads at runtime.
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    os.environ["PADDLE_PDX_CACHE_HOME"] = str(output.parent / "paddlex-cache")
    os.environ["OMP_NUM_THREADS"] = "2"
    from paddleocr import PaddleOCR

    pipeline = PaddleOCR(
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_detection_model_dir=str(models / "det"),
        text_recognition_model_name="latin_PP-OCRv5_mobile_rec",
        text_recognition_model_dir=str(models / "rec"),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        device="cpu", cpu_threads=2, enable_mkldnn=False,
    )
    payload = collect_results(pipeline.predict(str(image)))
    output.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
