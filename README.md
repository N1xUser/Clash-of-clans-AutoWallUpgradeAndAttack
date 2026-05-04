Here is the content converted into clean, GitHub-flavored Markdown.

***

# AutoWall – Clash of Clans Automation System

AutoWall is a sophisticated automation framework for Clash of Clans that leverages computer vision, multi‑engine optical character recognition, and generative AI to perform unattended resource farming, base upgrading, and attack deployment. It interacts with the game entirely through simulated window messages, never moving the physical mouse or requiring the game to be in the foreground.

## How It Works

The bot captures the Clash of Clans window using the Win32 API (`PrintWindow` with `PW_RENDERFULLCONTENT`), reads the current screen state, and sends mouse clicks and scrolls via `PostMessage`. All logic runs in a Python loop that cycles through:

1. Scanning home resources (Gold, Elixir, Dark Elixir) and builder availability
2. Checking the upgrades cache and scanning the builder menu if stale
3. Navigating to multiplayer, searching for a match that meets configured loot criteria
4. Deploying troops, spells, and heroes using one of several deployment algorithms
5. Monitoring the battle until victory stars appear, then returning home
6. Automatically upgrading walls with excess resources
7. Repeating the entire loop

Everything is configurable from a Tkinter dashboard, which also provides real‑time resource displays, terminal logs, and live OCR previews.

## Core Modules

### Window Capture (`src/vision/capture.py`)

The capture module finds the CoC window by searching for a window title containing “Clash of Clans” (excluding browser windows). Once identified it obtains the window DC, creates a compatible bitmap, and uses `PrintWindow` to blit the entire window content (including areas that might be off‑screen or behind overlays) into a NumPy array. The frame is then cropped to the client area, with a configurable header offset to ignore the title bar. All rendering is done without activating the window.

Clicks and scrolls are performed relative to the client area: the code translates ROI coordinates (0‑1 relative to the capture size) to screen coordinates, converts them to client coordinates for the target window (and any child windows), and posts `WM_LBUTTONDOWN` / `WM_LBUTTONUP` or `WM_MOUSEWHEEL` messages.

### Computer Vision & Preprocessing (`src/vision/detection.py`)

Before OCR is invoked, the relevant ROI is extracted and colour‑filtered to isolate the text. Each resource type has its own HSV/BGR range mask, carefully tuned for the exact pixel colours used in the game. For example:

* **Home Gold** numbers use a white tone (approx. #E0E0E0) with a tolerance of 23.
* **Enemy Gold** uses two close colour variants that both match the gold resource bar.
* **Enemy Elixir** similarly uses two ranges to capture slightly different shades.

The Upgrades menu uses a combination of a white mask, a red mask (for the cost text), and a green mask (for “available” indicators), all combined and then inverted so that text becomes white on a black background. Finally, a morphological open operation removes small noise.

The `is_main_screen` checker looks for the blue “i” button by counting non‑white pixels in the inverted mask. `check_match_found` looks for the bright cyan “Next” button after a battle search.

All these functions work on regions defined during the calibration step.

### Multi‑Engine OCR (`src/vision/ocr.py`)

Three OCR engines are available, selected independently for home resources, enemy resources, upgrades menu, wall upgrade text, and builder status.

* **Tesseract** – classic local engine; used with `--psm 6` for multi‑line upgrades and `--psm 7` for builder fractions. Resource numbers are extracted using `extract_all_tesseract`: crops are padded to equal width, vertically stacked, and the combined image is processed with a numeric whitelist. This drastically improves throughput compared to per‑crop calls.
* **RapidOCR** – ONNX‑runtime based OCR (via `rapidocr-onnxruntime`); provides line‑level results and is extremely fast. The multi‑crop method works similarly by concatenating lines.
* **GLM (Ollama)** – uses a local Ollama instance serving a vision model (e.g., `maternion/LightOnOCR-2`) to perform OCR. Images are base64‑encoded and sent to the API. For resource numbers, all crops are vertically stacked and a single prompt asks for all numbers separated by semicolons. For the upgrades menu, the raw text of each page is sent for parsing.

The parsed upgrades text is processed by `parse_raw_upgrades_text`, which attempts to handle HTML tables, Markdown tables, or plain text. It extracts the building name, quantity (if an “x3” suffix is present), cost, and maps the resource using a dictionary (`dic.json`). Unknown resources are marked as “n/d”.

### Calibration (`src/utils/calibration.py`)

A full GUI‑based calibration tool runs when no ROIs file is found (or when forced with `python main.py calibrate`). It displays the live game frame, dims the area outside the selection, and provides sliders to adjust the bounding box for each required region. A real‑time OCR preview shows how the preprocessed image will look. Regions are saved to `config/rois.json` as relative coordinates (0‑1).

The calibration includes descriptions tailored to each region, and the process can be stepped forward or backward. Pressing Escape cancels and exits; the spacebar locks the current ROI and advances.

### State Management & Caching (`src/core/state_manager.py`, `src/core/builder.py`)

The bot maintains an in‑memory dictionary (`latest_data`) holding all current resource values, builder fraction, and upgrades information. This is continuously updated by scans. The `BuilderScanner` encapsulates the “open builder menu, scroll through all pages, aggregate unique upgrades” logic. It uses a deduplication key (`name + cost`) and stops after two consecutive pages yield no new items. The full raw text of all pages is preserved for debugging.

### Attack System (`src/core/attack.py`)

Attacks follow a battle plan that can be sourced from:

* **Static JSON** (`config/static_attack.json`) – a pre‑defined list of deployment actions, possibly with advanced deployment modes.
* **Dynamic AI** – a screenshot of the enemy base is sent to Google Gemini AI (via the `google-genai` library) with a strict Pydantic schema. The AI returns bounding boxes for air defences and troops, plus an optimal deployment plan. The code then translates bounding boxes to screen coordinates and queues the actions.

Deployment is executed as an action queue that interleaves troop selection and map drops. Three deployment algorithms are implemented:

* `"human"` – Deploys each troop type sequentially along a red‑line perimeter (four linear segments). Troops are spaced evenly along the line; the bot selects the troop card once, then drops all units of that type before moving to the next.
* `"random"` – Randomly picks a troop type and drops up to 3 units at a random point on the red line before possibly switching troop type.
* `"robot"` – Creates an interleaved sequence where troop indices are cycled (troop1, troop2, troop3, …) and the drops are distributed equally across the four map segments. The troop card is only re‑clicked when the troop type changes, minimising redundant selections.

Spells and heroes are deployed after troops. The bot waits for heroes to land (configurable `HERO_DELAY_BEFORE_ABILITY`), then cycles back to activate their abilities.

Every drop coordinates are saved and a debug screenshot is generated (if enabled) showing a numbered overlay of all planned drop points. The high‑speed deployment loop only performs the expensive `safe_capture` (which checks for reload popups) once per second to avoid throttling the rapid clicks.

### Wall Upgrade System (`src/core/upgrade.py`)

The wall upgrade manager is triggered after a successful attack. It:

1. Fetches the list of wall upgrades from the cache (or from a fresh scan).
2. Sorts walls by cost (cheapest first).
3. For each wall type, checks the player’s current gold and elixir. Elixir is used for walls costing ≥ 500,000; otherwise gold is used.
4. If multiple walls can be afforded, the bot opens the builder menu (via the builder icon), scans the visible rows using the chosen OCR engine (Tesseract, RapidOCR, or GLM) to locate the wall with the matching cost, clicks it, and then clicks the “Add More” button the required number of times.
5. Chooses the upgrade button based on the resource type, confirms the upgrade, and zooms out.
6. The virtual resources are immediately deducted, and the cache is updated (zero‑quantity walls removed).
7. If after upgrading, no walls remain, the bot can be automatically stopped.

A “deselector sequence” is used before each wall type to ensure the builder menu is in a known state: zoom out, click the builder icon, scroll the menu, and click a corner to close any previous selection. Wall selection is verified by checking for a white pixel at a known coordinate (the cost text colour is #E0E0E0, threshold 210‑255).

### Bot Pipeline (`src/core/bot.py`)

The orchestrator runs the main loop in a separate thread. It constantly checks whether the bot is still running and catches `ReloadGameException` to restart the cycle. The `_safe_capture` function monitors for the “Reload Game” popup (checking pixel colours at two screen coordinates) and handles it by clicking “Reload” and waiting for the main village to reappear, then raising the exception to restart the loop.

The pipeline includes a 30‑minute cache for upgrades, meaning the builder menu is only re‑scanned if the cache is older than that or doesn’t exist. After each attack and wall upgrade, the loop repeats.

### User Interface (`src/ui/main_window.py`, `src/ui/widgets.py`)

The UI is built with Tkinter and features:

* Custom‑styled cards for live resource display (with sparklines for recent values).
* A scrollable body layout with three columns: Home Resources, Enemy Loot & AI Integration, Pipeline Configuration.
* Clickable scan buttons per OCR engine, plus separate buttons for upgrades.
* Checkboxes for Auto Wall Upgrade, Auto Donate, Anti‑AFK, and Debug Screenshots.
* A terminal log with colour‑coded messages (system, bot, gold, elixir, etc.).
* A “Preview” mode that opens a live OpenCV window showing the preprocessed OCR crops.
* A “Debug JSON” window to load and test static attack plans.

The Anti‑AFK system, when enabled, periodically zooms the camera in/out and pans the view to prevent the game from going idle.

## Installation

### Requirements

* Windows 10/11
* Python 3.8 or later
* Clash of Clans running on any platform (native Windows Store version is the primary target, but emulators may work after calibration)
* Tesseract OCR (optional, only if you want the Tesseract engine). Download from [GitHub](https://github.com/tesseract-ocr/tesseract) and ensure it is in your PATH.
* Ollama (optional, for GLM OCR). Download from [ollama.ai](https://ollama.ai) and pull a vision model, e.g. `ollama pull maternion/LightOnOCR-2`. Update `OLLAMA_MODEL` in `ocr.py` to match.
* Google Gemini API key (optional, for Dynamic AI mode)

### Setup Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/AutoWallsUpgrade.git
   cd AutoWallsUpgrade
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. (Optional) Install RapidOCR for the fastest local engine:
   ```bash
   pip install rapidocr-onnxruntime
   ```
5. Copy your Gemini API key into a `.env` file or directly into the UI later.

## Running the Bot

### Initial Calibration

On first launch, the bot will automatically enter calibration mode because no `config/rois.json` exists. You can also force recalibration at any time:

```bash
python main.py calibrate
```

Follow the on‑screen instructions to draw a box around each required region. The preview panel shows the processed image; adjust the sliders until the text is clearly visible. Press SPACE to confirm each step, B to go back, or ESC to quit.

After calibration, the ROIs are saved and the main UI will start next time.

### Normal Launch

Simply run:

```bash
python main.py
```

Configure the pipeline:

* **Home Pipeline** → Select the OCR engine for resources and for upgrades.
* **Attack Config** → Select the OCR engine for enemy loot and for wall OCR during upgrades.
* **Min Targets** → Set minimum gold, elixir, gold+elixir, or dark elixir. Use the checkbox state (✓ = AND, • = OR) to combine conditions.
* **AI Integration** → Choose “STATIC” to use `config/static_attack.json` or “DYNAMIC AI” to use Gemini. Enter your API key.
* **Attack Settings** → Enable **AUTO WALLS**, **ANTI AFK**, and **SAVE DEBUG SCREENSHOTS** as needed.

Press the green **START BOT** button to begin the automation loop.

## Configuration Files

### `config/rois.json`

Stores the calibrated region coordinates for resources, UI elements, and menus. Manual editing is possible but must follow the format:

```json
{
  "gold": {"x": 0.8700, "y": 0.0367, "w": 0.0840, "h": 0.0237},
  "elixir": {"x": 0.8700, "y": 0.1157, "w": 0.0840, "h": 0.0237},
  ...
}
```

### `config/dic.json`

Maps building names to their resource type. For example, “Elixir Collector” → “Gold”, “Hero Hall” → “Elixir”. If a building is missing, a default “n/d” is assigned. You can extend this file manually.

### `config/static_attack.json`

Defines the attack plan for STATIC mode. The structure is:

```json
{
  "deployment_mode": "robot",
  "available_troops": [
    {"name": "Electro Dragon", "x": 0.49, "y": 0.90, "quantity": 10}
  ],
  "available_spells": [],
  "available_heros": [],
  "deployment_positions": []
}
```

If `deployment_positions` is empty, the deployment mode (human/random/robot) will use the built‑in perimeter logic with the available troops. If `deployment_positions` contains items, each entry specifies an explicit drop coordinate and quantity. You can also use the “DEBUG JSON” button in the UI to load and test a plan without starting the full bot.

### `config/status.json`

Saved automatically when the bot is stopped or the UI is closed. Contains the current state, including the upgrades cache and the last selected configuration.

## Fine‑Tuning Deployment Speed

Inside `src/core/attack.py`, there are class‑level constants that control the timing of every action:

```python
ROBOT_DELAY_AFTER_SELECT = 0.05   # wait after selecting a troop card
ROBOT_DELAY_AFTER_DROP   = 0.03   # wait after dropping a single unit
SPELL_DELAY_AFTER_SELECT  = 0.2
SPELL_DELAY_AFTER_DROP    = 0.1
HERO_DELAY_AFTER_SELECT   = 0.15
HERO_DELAY_AFTER_DROP     = 0.1
HERO_DELAY_BEFORE_ABILITY = 3.0   # time for heroes to fully land
```

Increase these if your system has noticeable latency; lower them if the emulator can handle faster inputs (minimum ~0.02 s is usually safe).

## Troubleshooting

* **“CoC window not found”** – Make sure the game window title contains “Clash of Clans”. Exclude browser windows (the code already filters Firefox, Chrome, Edge). Try restarting the game.
* **OCR returns wrong values** – Recalibrate the ROIs, or try a different engine (RapidOCR is generally the most accurate for numbers). Ensure the game is not in a scaled or blurred state.
* **Clicks not registering** – The bot uses `PostMessage`; some emulators may ignore those messages. Make sure the emulator’s window is not minimised and that no other program is capturing input. You can test by manually sending clicks using a tool like Spy++.
* **Bot gets stuck in a loop** – Check the terminal log for exceptions. The most common cause is a reload popup that was not handled. Ensure `PW_RENDERFULLCONTENT` is set to `2` (which is default).
* **Dynamic AI fails** – Verify your Gemini API key and internet connection. The model used is selected in the UI; try the latest “gemini-3.1-flash-lite-preview”.

## Project Architecture

```text
AutoWallsUpgrade/
├── src/
│   ├── ui/                # Tkinter UI components
│   ├── core/              # Bot pipeline, attack, upgrades, state
│   ├── vision/            # Capture, detection, OCR
│   └── utils/             # Config, calibration, ROI management
├── config/                # Runtime configuration files
├── response/              # Saved AI requests and debug screenshots
├── main.py                # Entry point
└── requirements.txt
```

## Notes

This project is strictly for educational and research purposes. Using automation software may violate the game’s Terms of Service. The developers assume no liability for account actions taken by users.
