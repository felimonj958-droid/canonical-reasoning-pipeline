from pathlib import Path
from PIL import Image
import pytesseract
import sys
import cv2
import numpy as np  # still here in case you use it later


def main():
    if len(sys.argv) < 2:
        print("Usage: python ocr_page_to_text.py <image_path>")
        sys.exit(1)

    image_path = Path(sys.argv[1])

    if not image_path.exists():
        print(f"Image not found: {image_path}")
        sys.exit(1)

    # ---- NEW: derive pt / section and output path ----
    # Expect filenames like reasoning_set_a_q02_clean.jpeg
    stem = image_path.stem                      # 'reasoning_set_a_q02_clean'
    parts = stem.split("_")                     # ['reasoning','set','a','q02','clean']
    pt_id = parts[0]                            # 'reasoning'
    section_id = parts[1]                       # 'lr2'

    out_dir = Path("data") / pt_id / section_id
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"{stem}.txt"
    # --------------------------------------------------

    # Read with OpenCV
    img_cv = cv2.imread(str(image_path))

    # Convert to grayscale
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # Try rotating 90 degrees clockwise and counterclockwise,
    # run OCR on each, and keep the one with more A–E letters.
    def ocr_on(mat):
        # simple thresholding to improve contrast
        thr = cv2.threshold(mat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        pil_im = Image.fromarray(thr)
        return pytesseract.image_to_string(pil_im, lang="eng")

    candidates = []
    # original
    candidates.append(ocr_on(gray))
    # rotated 90 CCW
    candidates.append(ocr_on(cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE)))
    # rotated 90 CW
    candidates.append(ocr_on(cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)))

    # pick the text with most ASCII letters as a crude quality heuristic
    def score(t):
        return sum(c.isalpha() for c in t)

    text = max(candidates, key=score)

    out_path.write_text(text, encoding="utf-8")
    print(f"OCR written to {out_path}")


if __name__ == "__main__":
    main()
