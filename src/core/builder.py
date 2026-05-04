import time
from src.vision.capture import click_relative_roi, scroll_roi
from src.vision.detection import crop_roi, preprocess_for_ocr
from src.vision.ocr import extract_upgrades_tesseract, extract_upgrades_glm, extract_upgrades_rapid


class BuilderScanner:
    def __init__(self, hwnd, rois):
        self.hwnd = hwnd
        self.rois = rois

    def scan_upgrade_menu(self, capture_callback, ocr_engine, max_pages=25):
        ocr_engine = ocr_engine.lower()
        
        click_relative_roi(self.hwnd, self.rois["builders_icon"])
        time.sleep(1.0)

        master = []
        seen = set()
        combined = ""
        
        empty_scrolls = 0

        for idx in range(max_pages):
            time.sleep(0.5)
            frame = capture_callback()
            if frame is None:
                break

            proc = preprocess_for_ocr(crop_roi(frame, self.rois["upgrades_menu"]), "upgrades_menu")

            if ocr_engine == "tesseract":
                data = extract_upgrades_tesseract(proc)
            elif ocr_engine == "glm":
                data = extract_upgrades_glm(proc)
            elif ocr_engine == "rapid":
                data = extract_upgrades_rapid(proc)
            else:
                data = {"upgrades": [], "raw_text": ""}

            new = 0
            for item in data.get("upgrades", []):
                uid = f"{item['name']}_{item['cost']}"
                if uid not in seen:
                    seen.add(uid)
                    master.append(item)
                    new += 1

            combined += f"\n--- Page {idx+1} ---\n{data.get('raw_text', '')}"
            
            if new == 0:
                empty_scrolls += 1
                if empty_scrolls >= 2:
                    break
            else:
                empty_scrolls = 0

            scroll_roi(self.hwnd, self.rois["upgrades_menu"])
            time.sleep(1.7)

        return {
            "total_items_found": len(master),
            "upgrades": master,
            "raw_text": combined.strip()
        }
