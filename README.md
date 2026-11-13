# PDF Diff Studio

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-41CD52?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![License](https://img.shields.io/badge/License-MIT-purple)

**PDF Diff Studio** is a clean, modern, dark-themed desktop application for comparing two PDF documents side-by-side. It detects and highlights both **semantic text edits** and **pixel-level visual changes** (stamps, signatures, images, layout shifts, and font modifications) directly on the rendered pages.

![PDF Diff Studio Screenshot](assets/screenshot.png)

---

## ✨ Features

- **Side-by-Side Workspace** — Load files via file dialog or simply **Drag & Drop** PDFs directly into the left (*Original*) and right (*Modified*) panes.
- **3 Comparison Modes:**
  - **Text Diff** — Compares extracted word sequences and highlights deleted/modified text on the left and added/modified text on the right with clean rounded bounding boxes.
  - **Pixel Diff** — Uses computer vision (`OpenCV`) to spot visual differences such as signatures, stamps, diagrams, spacing shifts, or scanned text changes.
  - **Combined Mode** — Overlays both text and pixel differences simultaneously.
- **Synchronized Scrolling & Zoom** — Panning or zooming one document automatically mirrors the view on the other pane (can be toggled on/off).
- **Jump to Next Diff (`⚡`)** — Instantly skips identical pages and jumps straight to the next page containing differences.
- **100% Offline & Private** — All PDF rendering and comparison happen locally on your machine. Sensitive contracts and documents never leave your computer.

---

## 🎨 Highlight Legend

| Color | Meaning | Mode |
| :--- | :--- | :--- |
| 🔴 **Red Box** | Removed or modified text in Original PDF | `Text` / `Combined` |
| 🟢 **Green Box** | Added or modified text in Modified PDF | `Text` / `Combined` |
| 🟣 **Purple Box** | Visual / pixel-level difference (images, stamps, layout) | `Pixel` / `Combined` |

---

## 🚀 Getting Started

### Option 1: Standalone Windows Executable (No Python Required)
1. Go to the [**Releases**](../../releases) page.
2. Download the latest `PDFDiffStudio.exe`.
3. Run it — no installation or dependencies required.

> **Note:** Since the executable is not signed with a commercial certificate, Windows SmartScreen may display a prompt on first launch. Click **More info → Run anyway**.

---

### Option 2: Run from Source (Windows / macOS / Linux)

**1. Clone the repository:**


**2. Create a virtual environment and install dependencies:**
```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

**3. Launch the app:**
```bash
python pdf_diff_studio.py
```

---

## 📦 Building a Standalone `.exe`

You can package the application into a single portable executable using `PyInstaller`:

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --clean --name "PDFDiffStudio" pdf_diff_studio.py
```

Once completed, your standalone executable will be located in `dist/PDFDiffStudio.exe`.

---

## 🛠️ Tech Stack

- **[PyQt6](https://pypi.org/project/PyQt6/)** — Modern custom-styled dark GUI
- **[PyMuPDF (fitz)](https://pymupdf.readthedocs.io/)** — High-speed PDF rendering and word-coordinate extraction
- **[OpenCV](https://opencv.org/) & [NumPy](https://numpy.org/)** — Image alignment, thresholding, and contour detection for pixel diffs
- **Python `difflib`** — Sequence matching for accurate word-level text comparison

---

## 📄 License

Distributed under the **MIT License**. Feel free to use, modify, and distribute this tool for personal or commercial projects.
