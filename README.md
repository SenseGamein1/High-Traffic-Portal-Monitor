# 🚨 High-Traffic Portal Monitor

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Selenium](https://img.shields.io/badge/-selenium-%2343B02A?style=for-the-badge&logo=selenium&logoColor=white) 

A robust, multi-threaded web monitor built in Python. It constantly evaluates a target URL and uses JavaScript DOM inspection to ensure the page that loaded is the **actual functioning page**, bypassing server crash errors completely.

## 🎯 Motivation: Why This Exists

During high-traffic events—like national exam result days (CBSE), university portal openings, or limited-stock flash sales—websites frequently crash. Users are met with infinite loading screens, `503 Service Unavailable`, `502 Bad Gateway`, or `err_connection_timed_out` errors.

Normally, users waste hours manually hitting "Refresh," draining their energy and time. Simple ping scripts also fail here because a server might return a "200 OK" status code but still just display a Cloudflare waiting room or a blank error text. I built this script to solve that problem. It runs completely in the background, specifically searching the page for real login forms, text inputs, and submit buttons, alerting you only when the site is genuinely ready to use.

ps: this app also helps you knwo when a newly made or down site comes back live

## ✨ Features

* **🧠 Intelligent Page Evaluation**: Avoids false positives. It injects a snapshot script to check for visible password inputs, text fields, submit buttons, and predefined trigger words.
* **🧵 Multi-Session Staggering**: Spawns 3 independent Chrome instances that refresh on a staggered timeline (e.g., 1.5 seconds apart), maximizing the chances of slipping through server bottlenecks.
* **🔊 Audio-Visual Alerts**: Triggers system-level message boxes and audio beeps the second the page is genuinely live[cite: 2].
* **📸 Auto-Screenshot**: Automatically captures and saves a `.png` snapshot (`cbse_success.png`) of the successful page load[cite: 2].
* **⚙️ Auto-Dependency Resolution**: If you don't have Selenium installed, the script will automatically run `pip install selenium` for you on startup[cite: 2].
* **🪶 Resource Optimized**: Disables images, fonts, GPU, and extensions to keep memory usage low while running multiple instances[cite: 2].

## 🚀 Getting Started

### Prerequisites
* **Python 3.7+** installed on your system.
* **Google Chrome** browser installed.

### Installation & Usage
[📥 Download the Script Here](https://github.com/SenseGamein1/High-Traffic-Portal-Monitor/archive/refs/heads/main.zip)

**Instructions:**
1. Click the link above to download the script.
2. Extract the `.zip` file to your preferred folder.
3. Open your terminal or command prompt in that(inside the main forlder) folder.
4. Run the program using: `python cbse_login.py`
