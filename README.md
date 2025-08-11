<h1 align="center">🧠 Pro DICOM Viewer</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" />
  <img src="https://img.shields.io/badge/DICOM-Viewer-success?logo=dicom" />
</p>

<p align="center"><i>A powerful, interactive, and fun Python-based DICOM Viewer — built for developers, researchers, and radiologists alike!</i></p>

<p align="center">
  <a href="#-features"><b>Features</b></a> •
  <a href="#-installation"><b>Install</b></a> •
  <a href="#-usage"><b>Usage</b></a> •
  <a href="#-controls"><b>Controls</b></a> •
  <a href="#-code-structure"><b>Code</b></a> •
  <a href="#-screenshot"><b>Screenshot</b></a> •
  <a href="#-license"><b>License</b></a>
</p>

---

## ✨ Features

<table>
  <tr><td>🧭</td><td><b>Multi-slice Navigation</b> – Scroll through slices using mouse, slider, or keys</td></tr>
  <tr><td>🌈</td><td><b>Window Width/Level</b> – Adjust WW/WL in real-time</td></tr>
  <tr><td>📜</td><td><b>Metadata Display</b> – View patient name, modality, spacing, and more</td></tr>
  <tr><td>📏</td><td><b>ROI Measurement</b> – Click two points to measure in mm</td></tr>
  <tr><td>🔍</td><td><b>Zoom & Pan</b> – Standard Matplotlib controls & keyboard support</td></tr>
  <tr><td>📸</td><td><b>Image Export</b> – Save slices as PNG</td></tr>
  <tr><td>▶️</td><td><b>Series Playback</b> – Animate your DICOM stack</td></tr>
  <tr><td>🎥</td><td><b>MP4 Export</b> – Turn slices into video using <code>imageio</code></td></tr>
  <tr><td>💻</td><td><b>CLI Ready</b> – Run via terminal with ease</td></tr>
</table>


---

## 🛠️ Installation

```bash
pip install pydicom numpy matplotlib
# Optional for MP4 export
pip install imageio
```
## 📦 Clone the Repository

```bash
git clone https://github.com/your-username/pro-dicom-viewer.git
cd pro-dicom-viewer
```
## 🚀 Usage

```bash
python pro_dicom_viewer_fixed.py /path/to/your/dicom/series
```
> 💡 If no path is provided, it defaults to a placeholder (changeable in `main()`).

---

## 🎮 Controls

| 🕹️ Action           | 🔧 Control                                       |
|---------------------|-------------------------------------------------|
| Change Slice        | Slider, Mouse Wheel, Left/Right Arrow Keys      |
| Adjust Windowing    | WW/WL Sliders                                   |
| Zoom & Pan          | Matplotlib Toolbar, +/- Keys                    |
| Measure Distance    | "Measure" button, then Left-click two points    |
| Clear ROI           | Right-click on the image                        |
| Play/Pause Series   | Play button                                     |
| Save Image          | Save PNG button                                 |

---

## 🧠 Code Structure

<details>
  <summary><b>Click to expand code structure...</b></summary>

- `load_dicom_series(dir)` – Load and sort `.dcm` files  
- `get_image_array(ds)` – Extract pixel array from DICOM  
- `apply_window_level(arr, wl, ww)` – Window level transformation  
- `DicomViewer` – Main interactive viewer class  
  - `_build_figure()` – Build the GUI layout  
  - `_connect_events()` – Connect all buttons & slider callbacks  
  - `set_index()` – Central method to update view state  
  - `_on_scroll()`, `_on_key()`, `_on_measure()`, etc. – Interaction logic  
- `main()` – Entry point: loads directory and runs the app

</details>

---

## 📸 Screenshot

<p align="center">
  <img width="897" height="807" alt="Screenshot From 2025-08-11 12-45-12" src="https://github.com/user-attachments/assets/68edf75a-b35a-487c-96f3-8c0b8a04ad95" />

</p>

> 🖼️ Replace `screenshot.png` with a real screenshot of your DICOM Viewer!

---

## ✅ TODO (Optional Enhancements)

- [ ] Add 3D Volume Rendering (using VTK or pyvista)
- [ ] Add annotation saving
- [ ] PACS integration
- [ ] Multi-modality support

---

## 📃 License

<p align="center">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License Badge" />
  </a>
</p>

<p align="center">
  <i>This project is open source and available under the MIT License.</i><br>
  <strong>Use it. Share it. Improve it.</strong> 🚀
</p>

