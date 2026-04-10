<div align="center">
  <img src="https://img.icons8.com/color/120/000000/ticket.png" alt="Eventix Logo" width="100"/>
  <h1>🎫 Eventix - Modern Event Ticketing Platform</h1>
  <p>A comprehensive, full-stack event and ticket management system built with Python, Flask, and Turso.</p>

  <div>
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
    <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
    <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite"/>
    <img src="https://img.shields.io/badge/Turso-000000?style=for-the-badge&logo=turso&logoColor=white" alt="Turso"/>
    <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5"/>
    <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3"/>
  </div>
</div>

<br />

## 🌟 Overview

**Eventix** is an all-in-one e-commerce and event management platform designed to handle the entire lifecycle of an event. From event creation by organizers to ticket purchasing and QR code validation, Eventix delivers a seamless and premium UI/UX. The system is built with a robust role-based access control (RBAC) separating Customers, Organizers, and Admins.

---

## 🔥 Key Features

### 👤 Role-Based Portals
*   **Customer Dashboard**: Browse events, add to wishlist, interactive seat selection, view purchased tickets with scan-ready QR codes.
*   **Organizer Panel**: Create and manage events, track ticket sales, define dynamic seat maps, review financial summaries.
*   **Admin Area**: Approve/reject events, manage system users, global analytics, and reporting.

### 🎟️ Smart Ticketing & Seating
*   **Interactive Seat Selection**: Users can pick their exact row and seat for venues with seating plans.
*   **QR Code Generation**: Every purchased ticket generates a unique, secure QR code sent directly via email.
*   **Promotional Codes**: Built-in support for discount codes (fixed amount or percentage).

### 🚀 Technical Highlights
*   **Turso Cloud Database Integration**: Leverages highly available distributed SQLite for fast and reliable edge database queries (with a local `database.db` fallback).
*   **Secure Authentication**: Passwords hashed and sessions securely managed.
*   **SMTP Email Handling**: Automated ticket delivery and notifications straight to user inboxes.

---

## 📸 Screenshots

*(Replace the image URLs below with actual screenshots of your application)*

| Homepage & Event Discovery | Real-time Seat Selection |
| :---: | :---: |
| <img src="https://placehold.co/600x400/1e1e1e/white?text=Homepage+Screenshot" width="400"/> | <img src="https://placehold.co/600x400/1e1e1e/white?text=Seat+Selection+Screenshot" width="400"/> |

| Customer Dashboard | Organizer / Admin Panel |
| :---: | :---: |
| <img src="https://placehold.co/600x400/1e1e1e/white?text=Customer+Dashboard" width="400"/> | <img src="https://placehold.co/600x400/1e1e1e/white?text=Admin+Panel" width="400"/> |

---

## 🛠️ Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/gorkemcolakk/e-commerce.git
   cd e-commerce
   ```

2. **Create a virtual environment (Recommended)**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   # source venv/bin/activate    # macOS/Linux
   ```

3. **Install the dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables Config**
   Create a `.env` file in the root directory and add your configurations (SMTP, Turso, URL):
   ```ini
   FRONTEND_URL=http://localhost:5000
   SMTP_SERVER=smtp.yourserver.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@example.com
   SMTP_PASSWORD=your_app_password
   # TURSO_DB_URL=libsql://...
   # TURSO_AUTH_TOKEN=ey...
   ```

5. **Initialize the Database & Seed Data**
   ```bash
   python seed.py
   python database.py
   ```

6. **Run the Application**
   ```bash
   python app.py
   ```
   The application will be running at `http://localhost:5000`.

---

## 🏗️ Project Architecture

```
📂 E-commerce
├── 📄 app.py              # Main Flask Application Entry Point
├── 📄 database.py         # Database Connection (Turso & SQLite Config)
├── 📄 payment.py          # Payment Gateway Mock / Handles
├── 📄 seed.py             # Mock Data Generator (Events, Users, Promo codes)
├── 📄 utils.py            # Helpers (QR logic, Mailing, Validation)
├── 📂 routes/             # Blueprint routes (Auth, Events, User, Organizer)
└── 📂 frontend/           # HTML Templates, CSS, JS and Assets
```

---

<div align="center">
  <p>Developed for the comprehensive Event Management capstone project.</p>
</div>
