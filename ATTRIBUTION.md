# Attribution

## Machine Learning & AI Libraries
- **YOLOv8 (Ultralytics)**  
  Used for manga panel, bubble, and text-region detection.  
  Repository: https://github.com/ultralytics/ultralytics  

- **MangaOCR**  
  Used for Japanese OCR text extraction.  
  Repository: https://github.com/kamyu104/manga-ocr  

- **OpenAI GPT Models**  
  Used for Japanese to English translation and text refinement.  
  Documentation: https://platform.openai.com/docs  
  API key required.

## Python Libraries
- **FastAPI** – used to build the backend API server.  
- **Pydantic** – used for request/response validation.  
- **OpenCV (cv2)** – used for image loading, preprocessing, and cropping.  
- **Pillow (PIL)** – used for image decoding and transformations.  
- **uvicorn** – ASGI web server for FastAPI.  

## JavaScript / Frontend Libraries
- **React**  
  Used for building the overlay UI, rendering translated text, and implementing the screenshot and cropping interface.

- **html2canvas**  
  Used for capturing portions of the webpage as screenshots for backend inference.  

- **Vite**  
  Used as the React build tool / dev server.  

## Chrome Extension Components
This project includes a self-built Chrome extension for injecting the translation overlay into manga reader sites. The extension architecture follows Chrome MV3 guidelines:  
https://developer.chrome.com/docs/extensions/mv3/

## Datasets
- **Manga109 Dataset (for training bubble/text detectors)**  
  Used under Manga109 dataset terms of use.  
  Website: http://www.manga109.org/en/  

- **Custom Annotated Dataset for Speech Bubbles**  
  Manually annotated using Roboflow / CVAT for training YOLOv8 models.

## Fonts
- **Anime Ace / Comic Neue**  
  Used for rendering translated manga-style text.  
