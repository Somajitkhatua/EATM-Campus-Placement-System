# 🎓 NIET Campus Placement Management System

A premium, state-of-the-art web application and backend management system designed for **Noida Institute of Engineering & Technology (NIET), Greater Noida**. 

This system connects a rich, dynamic frontend dashboard to a robust Python data structure backend, enabling seamless administration of student registrations, company recruiters, placement drives, interview coordination, job offers, and real-time statistics.

Live Demo: [http://phoeenixxd.pythonanywhere.com](http://phoeenixxd.pythonanywhere.com)

---

## ✨ Key Features

- **📊 Comprehensive Dashboard**: Real-time stats showing placement rates, highest/average packages, recruiter counts, and top placement highlights from NIET.
- **👨‍🎓 Student Management**: Add, search, and view student records (sorted dynamically by CGPA). Supports recursive searching algorithms.
- **🏢 Company Management**: Register recruiting organizations, track job roles, minimum CGPA eligibility criteria, and salary packages.
- **📅 Placement Drive Scheduler**: Create and track company-specific placement drives.
- **🎤 Interview Coordination**: Schedule and manage interview status between eligible candidates and companies.
- **📜 Job Offer Tracker**: Generate, issue, and keep track of official job offers.
- **✅ Eligibility Checker**: Inline validation tools to instantly check if a student meets a company's CGPA criteria before registration.
- **📈 Report Generation**: Export institutional placement records directly to standard CSV format.

---

## 🎨 Design & Visuals ("Cosmic Dark Luxe")

The interface is built with premium UI/UX standards:
* **WebGL Shaders**: Custom cosmic fire background animated at 60 FPS in the Hero section.
* **Optimized Light Beams**: Floating glow effects inside the dashboard area.
* **Performance Throttling**: Embedded `IntersectionObserver` loops to automatically pause off-screen canvas animations, ensuring 0% idle CPU/GPU overhead.
* **Dynamic Glassmorphic Layout**: Responsive glass cards, hover micro-interactions, custom scrollbars, and modern typography from Google Fonts (`Outfit` and `DM Sans`).

---

## 🛠️ Technology Stack

- **Backend**: Python (Flask REST API, object-oriented custom data structures, serialization)
- **Frontend**: Vanilla JavaScript (ES6+), CSS3 (Custom Variables, GPU animations), HTML5
- **Deployment**: uWSGI Server (PythonAnywhere environment)
- **Database**: Local JSON-based persistent storage (`data.json`)

---

## 🚀 Local Installation & Setup

Ensure you have **Python 3.10+** installed on your system.

1. **Clone the repository**:
   ```bash
   git clone git@github.com:Divyansh-Kashiv07/NIET-Campus-Placement-System.git
   cd NIET-Campus-Placement-System
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Flask server**:
   ```bash
   python app.py
   ```
   Open `http://localhost:5000` in your web browser.

5. **Run the CLI backend (Alternative)**:
   If you want to manage data directly from a command-line interface:
   ```bash
   python main.py
   ```

---

## 📁 Project Structure

```text
├── app.py                  # Flask REST API and page routes
├── main.py                 # Interactive command-line interface (CLI)
├── system.py               # CampusPlacementSystem core business logic class
├── models.py               # OOP Data models (Student, Company, Drive, etc.)
├── utils.py                # Custom exceptions, logging decorators, and helper methods
├── data.json               # Serialized database file (loaded on startup, saved on edit)
├── requirements.txt        # Production-ready dependency file
├── templates/
│   └── index.html          # Dashboard user interface HTML
├── static/
│   ├── css/
│   │   └── style.css       # Custom design system stylesheet
│   └── js/
│   │   └── app.js          # API calls, UI rendering, WebGL animations
```

---

## 📄 License

This project is created as part of the NIET Python Workshop. Licensed under the MIT License.
