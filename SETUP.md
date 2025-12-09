# SETUP INSTRUCTIONS

## PREREQUISITES
-------------
You must have the following installed:

- Python 3.10+
- Node.js 20.19+ or 22.12+
- npm 10+
- Google Chrome
- (Optional) A GPU is NOT required. The system runs on CPU.

You also need an OpenAI API key for translation.

## BACKEND SETUP (PYTHON)
----------------------
1. Navigate to the project root:
   cd <project-root>

2. Create and activate a virtual environment:
   python3 -m venv .venv
   source .venv/bin/activate
   (Windows: .venv\Scripts\activate)

3. Install required backend packages:
   pip install -r requirements.txt

4. Set your OpenAI API key:
   export OPENAI_API_KEY="YOUR_KEY_HERE"
   (Windows PowerShell: setx OPENAI_API_KEY "YOUR_KEY_HERE")

5. Run the FastAPI backend server:
   uvicorn src.new_pipeline:app --reload

The backend will start on:
   http://localhost:8000

## FRONTEND SETUP (REACT APP)
--------------------------
1. Navigate to the React UI:
   cd manga-overlay

2. Install dependencies:
   npm install

3. Run the development server:
   npm run dev

The UI will start on:
   http://localhost:5173

You MUST keep this tab open while using the Chrome extension.

## CHROME EXTENSION SETUP
----------------------
1. Open Chrome and go to:
   chrome://extensions/

2. Enable:
   Developer Mode (toggle in top-right)

3. Click:
   Load unpacked

4. Select the folder:
   manga-extension

This installs the custom extension that injects the React overlay into any manga website.

## HOW TO USE THE SYSTEM
---------------------
1. Navigate to ANY manga website (e.g., ComicWalker, MangaDex, personal images).
2. Click the Chrome extension icon.
3. Press the “Capture Manga Area” button that appears.
4. Click-and-drag to select the region of the screen containing the manga page.
5. The system:
   - Captures the screenshot
   - Sends it to the Python backend
   - Runs YOLO detection, OCR, cleaning, and translation
   - Returns text bubbles + outside-text bounding boxes
   - Renders translated English directly over the page

If enabled, the system also draws speech bubble masks to hide the original Japanese text.

## TESTING WITH A SAMPLE IMAGE (NO EXTENSION REQUIRED)
---------------------------------------------------
1. Run the backend and frontend normally.
2. Place any example manga image inside:
   manga-overlay/public/example.jpg
3. In main.jsx, uncomment:
    ```// import App from "./TestApp";```
This allows you to test overlay rendering without using HTML2Canvas or the Chrome extension.

## OPENAI API USAGE
----------------
Your translation pipeline requires an API key. It is read from:

   OPENAI_API_KEY

The backend calls GPT-5o-mini to translate bubble text and outside text.

## TROUBLESHOOTING

● If html2canvas fails due to CORS:
   - The system falls back to drawing only overlays without capturing images
   - Not all sites allow pixel-level HTML2Canvas extraction (Chrome security)

● If no translation appears:
   - Check OPENAI_API_KEY is set in the backend environment
   - Check FastAPI logs for errors
