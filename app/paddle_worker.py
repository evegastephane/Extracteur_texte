"""Standalone entry point: runs in .venv-paddle, never imports the Flask app."""
import json
import os
from pathlib import Path
import sys


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
    lines = []
    for result in pipeline.predict(str(image)):
        # PaddleOCR 3.x returns OCRResult mappings in page reading order.
        texts = result.get("rec_texts")
        if not isinstance(texts, list) or any(not isinstance(text, str) for text in texts):
            raise ValueError("Unsupported PaddleOCR output")
        lines.extend(texts)
    output.write_text(json.dumps({"text": "\n".join(lines)}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
