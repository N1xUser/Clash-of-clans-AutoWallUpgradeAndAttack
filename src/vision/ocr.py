import pytesseract
import re
import cv2
import numpy as np
import requests
import base64
import json
import os
from pathlib import Path

try:
    from rapidocr_onnxruntime import RapidOCR
    rapid_engine = RapidOCR()
except ImportError:
    rapid_engine = None
    print("[WARN] rapidocr-onnxruntime is not installed. Please run: pip install rapidocr-onnxruntime")

OLLAMA_MODEL = "maternion/LightOnOCR-2:latest" 
OLLAMA_URL = "http://localhost:11434/api/generate"

DIC_FILE = Path("config/dic.json")

def load_resource_dict() -> dict:
    if not DIC_FILE.exists():

        DIC_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        default_dic = {
            "Elixir Collector": "Gold", "Hero Hall": "Elixir", "Royal Champion": "Dark Elixir",
            "Minion Prince": "Dark Elixir", "Monolith": "Dark Elixir", "Laboratory": "Elixir",
            "Blacksmith": "Elixir", "Archer Queen": "Dark Elixir", "Barbarian King": "Dark Elixir"
        }
        with open(DIC_FILE, "w", encoding="utf-8") as f:
            json.dump(default_dic, f, indent=2)
        return default_dic
    try:
        with open(DIC_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[DIC ERROR] Failed to load dic.json: {e}")
        return {}

def parse_raw_upgrades_text(raw_text: str) -> list[dict]:
    res_dict = load_resource_dict()
    res_dict_lower = {k.strip().lower(): v for k, v in res_dict.items()}
    upgrades = []
    raw_pairs =[]

    if "<table" in raw_text.lower() or "<td>" in raw_text.lower():
        rows = re.findall(r'<tr.*?>(.*?)</tr>', raw_text, re.DOTALL | re.IGNORECASE)
        for row in rows:
            cols = re.findall(r'<td.*?>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
            if len(cols) >= 2:
                if "cost" in cols[1].lower(): continue
                raw_pairs.append((cols[0], cols[1]))
                
    elif "|" in raw_text and ("|-" in raw_text or "---" in raw_text):
        for line in raw_text.split('\n'):
            line = line.strip()
            if line.startswith("|") and line.endswith("|"):
                cols =[c.strip() for c in line.strip("|").split("|")]
                if len(cols) >= 2:
                    if "cost" in cols[1].lower() or "---" in cols[1]: continue
                    raw_pairs.append((cols[0], cols[1]))
                    
    else:
        lines =[line.strip() for line in raw_text.split('\n') if line.strip() and not line.startswith("---")]
        pending_name = None
        
        for line in lines:
            line = re.sub(r'(\$\\bullet\$|\\bullet|[\u25cf\u26ab\u2022\*\~_])', '', line).strip()
            if not line: continue

            match_single = re.search(r'^([a-zA-Z\s\']+(?:\s*[xX]\s*[a-zA-Z0-9]+)?)\s*[^a-zA-Z0-9]+\s*([0-9lLoOiIsS][0-9lLoOiIsS\s]{2,})$', line)
            if match_single:
                raw_pairs.append((match_single.group(1).strip(), match_single.group(2).strip()))
                pending_name = None
                continue
                
            if re.search(r'[a-zA-Z]{2,}', line):
                pending_name = line
            elif pending_name and re.search(r'\d', line):
                raw_pairs.append((pending_name, line))
                pending_name = None

    for raw_name, raw_cost in raw_pairs:
        raw_name = re.sub(r'<[^>]+>', '', raw_name)
        raw_cost = re.sub(r'<[^>]+>', '', raw_cost)

        qty = 1
        qty_match = re.search(r'\s+[xX]\s*([a-zA-Z0-9]+)$', raw_name)
        if qty_match:
            q_str = qty_match.group(1).upper()
            q_str = q_str.replace('S', '5').replace('I', '1').replace('L', '1').replace('O', '0').replace('B', '8')
            try:
                clean_q = re.sub(r'\D', '', q_str)
                if clean_q: qty = int(clean_q)
            except ValueError:
                pass

        raw_name = re.sub(r'\s+[xX]\s*[a-zA-Z0-9]+$', '', raw_name).strip()
        clean_name = re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', raw_name).strip()
        
        if clean_name.lower().startswith("new "): clean_name = clean_name[4:].strip()
        if clean_name.lower().endswith(" request"): clean_name = clean_name[:-8].strip()
        
        clean_cost_str = raw_cost.upper().replace('O', '0').replace('I', '1').replace('L', '1').replace('S', '5')
        clean_cost_str = re.sub(r'\D', '', clean_cost_str)
        
        resource = res_dict_lower.get(clean_name.lower(), "n/d")
        
        if clean_cost_str:
            try:
                upgrades.append({"name": clean_name, "qty": qty, "cost": int(clean_cost_str), "resource": resource})
            except ValueError: pass
            
    return upgrades

def extract_builders_tesseract(image: np.ndarray) -> str:
    custom_config = r'--psm 7 -c tessedit_char_whitelist=0123456789/'
    try:
        text = pytesseract.image_to_string(image, config=custom_config).strip()
        match = re.search(r'\d+/\d+', text)
        return match.group(0) if match else "?/?"
    except: return "?/?"

def extract_numbers_tesseract(image: np.ndarray) -> int:
    custom_config = r'--psm 7 -c tessedit_char_whitelist=0123456789'
    try:
        text = pytesseract.image_to_string(image, config=custom_config)
        cleaned = re.sub(r'\D', '', text)
        return int(cleaned) if cleaned else 0
    except Exception as e: return 0

def extract_upgrades_tesseract(image: np.ndarray) -> dict:
    try:
        text = pytesseract.image_to_string(image, config='--psm 6').strip()
        return {"engine": "tesseract", "upgrades": parse_raw_upgrades_text(text), "raw_text": text}
    except Exception as e: return {"error": str(e)}

def extract_builders_rapid(image: np.ndarray) -> str:
    if rapid_engine is None: return "?/?"
    try:
        if len(image.shape) == 2: image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        res, _ = rapid_engine(image)
        if res:
            text = " ".join([item[1] for item in res])
            match = re.search(r'\d+/\d+', text)
            return match.group(0) if match else "?/?"
        return "?/?"
    except: return "?/?"

def extract_all_rapid(crops: list[np.ndarray]) -> list[int]:
    if rapid_engine is None: return [0] * len(crops)
    results =[]
    for c in crops:
        try:
            if len(c.shape) == 2: c = cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)
            res, _ = rapid_engine(c)
            if res:
                text = " ".join([item[1] for item in res])
                cleaned = re.sub(r'\D', '', text)
                results.append(int(cleaned) if cleaned else 0)
            else: results.append(0)
        except: results.append(0)
    return results

def extract_upgrades_rapid(image: np.ndarray) -> dict:
    if rapid_engine is None: return {"error": "RapidOCR not loaded"}
    try:
        if len(image.shape) == 2: image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        res, _ = rapid_engine(image)
        if res:
            text = "\n".join([item[1] for item in res])
            return {"engine": "rapid", "upgrades": parse_raw_upgrades_text(text), "raw_text": text}
        return {"engine": "rapid", "upgrades":[], "raw_text": ""}
    except Exception as e: return {"error": str(e)}

def extract_builders_glm(image: np.ndarray) -> str:
    try:
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        _, buffer = cv2.imencode('.png', image)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        prompt_text = "Extract the fraction (e.g. 5/5 or 2/6) from this image. Return ONLY the fraction and nothing else."
        payload = {"model": OLLAMA_MODEL, "prompt": prompt_text, "images":[img_b64], "stream": False, "options": {"temperature": 0.0}}
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        text = response.json().get("response", "").strip()
        match = re.search(r'\d+/\d+', text)
        return match.group(0) if match else "?/?"
    except: return "?/?"

def extract_all_glm(crops: list[np.ndarray]) -> list[int]:
    try:
        padded_crops =[]
        max_width = 0
        for c in crops:
            if len(c.shape) == 2:
                c = cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)
            padded = cv2.copyMakeBorder(c, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=[255, 255, 255])
            padded_crops.append(padded)
            if padded.shape[1] > max_width: max_width = padded.shape[1]
                
        uniform_crops =[]
        for pc in padded_crops:
            diff = max_width - pc.shape[1]
            if diff > 0: 
                pc = cv2.copyMakeBorder(pc, 0, 0, 0, diff, cv2.BORDER_CONSTANT, value=[255, 255, 255])
            uniform_crops.append(pc)
            
        combined_img = np.vstack(uniform_crops)
        _, buffer = cv2.imencode('.png', combined_img)
        img_b64 = base64.b64encode(buffer).decode('utf-8')

        num_crops = len(crops)
        prompt_text = f"This image contains a vertical list of {num_crops} numbers. Read all {num_crops} numbers from top to bottom. Ignore any spaces or text. Output the numbers separated by a semicolon (;)."
        payload = {"model": OLLAMA_MODEL, "prompt": prompt_text, "images":[img_b64], "stream": False, "options": {"temperature": 0.0}}
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        text = response.json().get("response", "").replace(" ", "").replace(",", "")
        parts = re.split(r'[;\n]+', text)
        results =[int(re.sub(r'\D', '', p)) for p in parts if re.sub(r'\D', '', p)]
        while len(results) < num_crops: results.append(0)
        return results[:num_crops]
    except Exception as e: return[0] * len(crops)

def extract_upgrades_glm(image: np.ndarray) -> dict:
    try:
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        _, buffer = cv2.imencode('.png', image)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        prompt_text = "Extract all the text from this image exactly as it appears. Include the names and costs of the items. Do not add any explanations, formatting, or markdown, just the raw text."
        payload = {"model": OLLAMA_MODEL, "prompt": prompt_text, "images":[img_b64], "stream": False, "options": {"temperature": 0.0}}
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        text_response = response.json().get("response", "").strip()
        return {"engine": "glm", "upgrades": parse_raw_upgrades_text(text_response), "raw_text": text_response}
    except Exception as e: return {"error": f"Connection error: {e}"}

def extract_all_tesseract(crops: list[np.ndarray]) -> list[int]:
    try:
        padded_crops =[]
        max_width = 0
        for c in crops:
            if len(c.shape) == 3:
                c = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
            padded = cv2.copyMakeBorder(c, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=255)
            padded_crops.append(padded)
            if padded.shape[1] > max_width:
                max_width = padded.shape[1]
        
        uniform_crops = []
        for pc in padded_crops:
            diff = max_width - pc.shape[1]
            if diff > 0:
                pc = cv2.copyMakeBorder(pc, 0, 0, 0, diff, cv2.BORDER_CONSTANT, value=255)
            uniform_crops.append(pc)
        
        combined_img = np.vstack(uniform_crops)
        custom_config = r'--psm 6 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(combined_img, config=custom_config)
        
        lines =[line.strip() for line in text.split('\n') if line.strip()]
        results =[]
        for line in lines:
            cleaned = re.sub(r'\D', '', line)
            results.append(int(cleaned) if cleaned else 0)
        
        while len(results) < len(crops):
            results.append(0)
        return results[:len(crops)]
    except Exception as e:
        return[0] * len(crops)