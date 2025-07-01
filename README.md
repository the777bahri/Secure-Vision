# 🔒 Secure Vision – AI Surveillance System

Welcome to **Secure Vision**!  
An AI-powered, real-time surveillance platform blending deep learning, computer vision, and interactive UI for next-gen human detection and security monitoring.  
Developed for UTS 42028 – Deep Learning and Convolutional Neural Networks (Autumn 2025).

---
## 🖇️Links
- **Whole Project**:(https://drive.google.com/drive/folders/1gEeS6lK2Q9SdUoSl_3FIWFkDMYch7y1w?usp=sharing)
- **🏬Dataset**:(https://drive.google.com/drive/folders/1oc7sqFQttazod-Qq30nEVXEdTz2pv2CQ?usp=sharing)
## 🚀 Features

- **YOLO12n Object Detection**: Fast, accurate human detection using transfer learning on custom datasets.
- **Face Recognition**: Multi-person face identification with [InsightFace](https://github.com/deepinsight/insightface) and custom embeddings.
- **Drone & CCTV Simulation**: Live video feeds, drone dispatch (Futurework), and area monitoring.
- **Interactive Dashboard**: Real-time event logs, drone status, and analytics.
- **Streamlit UI**: Modern, responsive interface for seamless user experience.

---

## 🗂️ Project Structure

```
bytrack/           # ByteTrack config for multi-object tracking
data collection/   # Scripts for collecting and augmenting datasets
face_data/         # Saved face encodings (per person)
face_models/       # Pretrained face recognition models (ONNX)
facial_recognition/# Face recognition & data collection scripts
human_face/        # SecureVision main app (YOLO + Face + Tracking)
sounds/            # Alert/notification sounds
Training/          # Training script for the YOLO 12n
ui/                # Streamlit app, templates, static files
yolo/              # YOLO training notebooks and configs
yolo models/       # Trained YOLO model weights
```

---

## 🧠 How It Works

1. **Detection**: YOLO12n detects humans in video streams.
2. **Tracking**: ByteTrack assigns consistent IDs to detected persons.
3. **Recognition**: InsightFace matches faces to known identities.
4. **Action**: UI displays alerts, allows drone dispatch, and logs events.

---

## 🖥️ Quick Start

### 1. Clone & Install

```sh
git clone <your-repo-url>
cd <project-folder>
pip install -r requirements.txt
```

### 2. add face data for new people

- Collect face data using:
  ```sh
  python facial_recognition/face_reco.py
  ```

### 3. Launch the App

```sh
$env:PYTHONPATH="."    
streamlit run ui/main.py
```

---

## 🛠️ Key Components

- **ui/main.py**: Streamlit UI logic and navigation
- **human_face/securevision.py**: Main detection, tracking, and recognition pipeline
- **facial_recognition/face_infereance.py**: face recognition inferance to double check
- **facial_recognition/face_reco.py**: Face data collection utility

---

## 👨‍💻 Team

- 🆔 13384589 – [Abdullah.I.Bahri@student.uts.edu.au](mailto:Abdullah.I.Bahri@student.uts.edu.au)
- 🆔 25176811 – [Hayrambhrajesh.monga@student.uts.edu.au](mailto:Hayrambhrajesh.monga@student.uts.edu.au)
- 🆔 25093295 – [Yohan.EdiriweeraArakkattuPatabandige@student.uts.edu.au](mailto:Yohan.EdiriweeraArakkattuPatabandige@student.uts.edu.au)

---

## 📢 Acknowledgements

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
- [InsightFace](https://github.com/deepinsight/insightface)
- UTS 42028 – Deep Learning and Convolutional Neural Networks

---

## 📸 Screenshots

> _Add screenshots of your UI, detection results, and dashboard here!_
![image](https://github.com/user-attachments/assets/3da9f691-ecf6-4b59-880d-ac6e853babc2)
> ![image](https://github.com/user-attachments/assets/6e657109-765b-4223-a879-950ae492fe8e)
> ![image](https://github.com/user-attachments/assets/eecdd107-fa21-4bf8-916d-6d1e022b7e24)
> ![image](https://github.com/user-attachments/assets/fa0a4d21-ee39-41b3-9b27-c28abbd1ae5c)
> ![image](https://github.com/user-attachments/assets/5852223c-a201-487f-a37c-b92b47e41a24)

---

## 📝 License

MIT License (or specify your license here)

---

**Enjoy Secure Vision!** 🚨🛡️

---

# ⚙️ Setup Guide: Install C++ Build Tools for `insightface` (Windows & macOS)

This guide explains how to install the required C++ tools to enable successful installation of Python packages like `insightface` that include native C++ code.

---

## 🪟 Windows: Install MSVC v143 + Windows SDK

### ✅ Steps:

1. **Download Visual Studio Installer:**
   - Visit: [https://visualstudio.microsoft.com/downloads](https://visualstudio.microsoft.com/downloads)
   - Click **"Free Download"** under **Visual Studio 2022 Community**.

2. **Run the installer (`VisualStudioSetup.exe`)**

3. **In the Workloads tab:**
   - ✅ Select **"Desktop development with C++"**

4. **In the right panel (Installation Details):**
   Ensure the following components are selected:
   - ✅ **MSVC v143 - VS 2022 C++ x64/x86 build tools**
   - ✅ **Windows 10 SDK** *(or Windows 11 SDK if you're on Win11)*
   - ✅ **C++ CMake tools for Windows** *(optional but helpful)*

5. **Click "Install"** (or **"Modify"** if already installed)

6. Wait for the installation to complete.

---

## 🍎 macOS: Install Xcode Command Line Tools

### ✅ Steps:

1. **Open Terminal**

2. **Run the following command:**
   ```bash
   xcode-select --install
   ```
3. **Click "Install" in the dialog that appears.**

4. **Wait for installation to finish.**
**✅ Done**

---

## 🧑‍💻 Face Models Download

The required face recognition models are **auto-downloaded** when you run the application.  
If the auto-download fails or you need to manually set up the models, download them from the link below:

- [Download face_models folder (Google Drive)](https://drive.google.com/drive/folders/1gEeS6lK2Q9SdUoSl_3FIWFkDMYch7y1w?usp=sharing)

Place the downloaded folder in your project directory as `face_models`.

---
