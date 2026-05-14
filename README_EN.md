<div align="center">

<img src="opendoro/data/icons/app.ico" alt="DoroPet Logo" width="120" height="120"/>

# DoroPet

### ✨ Your Smart Desktop Companion — Work Never Feels Lonely Again

[![Website](https://img.shields.io/badge/Website-waterfeetbot.top-blue?style=for-the-badge\&logo=google-chrome)](https://www.waterfeetbot.top/)
[![Version](https://img.shields.io/badge/version-3.5.1-blue.svg)](https://gitee.com/waterfeet/DoroPet_V3/releases)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![QQ Group](https://img.shields.io/badge/QQ_Group-695753609-blue.svg)](https://qm.qq.com/q/MbaBoCevaC)

**A desktop app integrating Live2D pet, AI chat, voice interaction, pet simulation, Galgame interactive storytelling, and online music — all in one place**

[🚀 Quick Start](#-quick-start) · [✨ Features](#-features) · [📖 User Guide](#-user-guide) · [🤝 Contributing](#-contributing)

[中文文档](README.md)

</div>

***

## 🎯 Introduction

**DoroPet** is a revolutionary desktop pet application. It's not just an animated pet on your screen — it's your intelligent work companion!

Imagine: while you're working alone at your computer, a cute Live2D character keeps you company — it chases your mouse, peeks out from screen edges, reminds you to take a break when you're tired, and can even chat intelligently with you, play Galgame interactive stories, and play music for you!

### 🌟 Why Choose DoroPet?

| Feature                         | Description                                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------------------------- |
| 🎭 **Live2D Dynamic Characters** | Smooth Live2D v3 model rendering with expressions, motions, mouse tracking, and speech bubbles     |
| 🤖 **Multi-Model AI Chat**       | Supports 8 AI models: OpenAI, DeepSeek, Claude, Gemini, Ollama, and more                          |
| 🎙️ **Voice Interaction**        | Wake word detection + speech recognition + speech synthesis for natural conversations             |
| 🎮 **Pet Simulation System**     | Four attributes — Hunger, Mood, Cleanliness, Energy — with linked mechanics for immersive raising |
| 📖 **Galgame Storytelling**      | AI-driven interactive storytelling with affection system, multiple endings, save/load, inventory  |
| 🎵 **Online Music**              | Multi-platform music search & playback, lyrics & spectrogram, playlist management, VLC engine     |
| 🔌 **Agent Skills**              | 11+ built-in utility skills: document processing, search, weather, web scraping, frontend design, extensible |
| 🧠 **Smart Memory**              | AI automatically extracts long-term memories and analyzes message importance for coherent chats   |
| 🎨 **Theme Switching**           | Light & dark themes with adjustable font scaling                                                  |
| 📌 **Edge Docking**              | Pet docks to any screen edge with auto-hide/peek                                                  |
| 📎 **Attachment Handling**       | Auto-extract text from txt, html, json, md files and send to AI                                   |
| 🔄 **Auto Update**               | Built-in version management, auto-check on startup, one-click update                              |

***

## 📸 Screenshots

### Core Features

<table>
  <tr>
    <td align="center"><b>🖥️ Desktop Pet</b></td>
    <td align="center"><b>💬 AI Chat</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/doro.png" alt="Desktop Pet" width="400"/></td>
    <td><img src="opendoro/data/resourse/img/智能对话.png" alt="AI Chat" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><b>📊 Pet Status</b></td>
    <td align="center"><b>⚙️ Settings</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/主页.png" alt="Pet Status" width="400"/></td>
    <td><img src="opendoro/data/resourse/img/设置界面.png" alt="Settings" width="400"/></td>
  </tr>
</table>

### More Interfaces

<table>
  <tr>
    <td align="center"><b>🤖 Model Config</b></td>
    <td align="center"><b>🎭 Live2D Models</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/模型配置.png" alt="Model Config" width="400"/></td>
    <td><img src="opendoro/data/resourse/img/live2d.png" alt="Live2D Models" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><b>👤 Role Play</b></td>
    <td align="center"><b>🔌 Plugins Demo</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/人格提示词.png" alt="Role Play" width="400"/></td>
    <td><img src="opendoro/data/resourse/img/插件演示.gif" alt="Plugins Demo" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><b>🎨 Agent Skills</b></td>
    <td align="center"><b>📋 Logs</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/agent-skill.png" alt="Agent Skills" width="400"/></td>
    <td><img src="opendoro/data/resourse/img/logpage.png" alt="Logs" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><b>🔄 Update</b></td>
    <td align="center"><b>📱 Context Menu</b></td>
  </tr>
  <tr>
    <td><img src="opendoro/data/resourse/img/更新界面.png" alt="Update" width="400"/></td>
    <td><img src="opendoro/data/resourse/img/右键菜单.png" alt="Context Menu" width="400"/></td>
  </tr>
</table>

***

## 🚀 Quick Start

### 📋 System Requirements

- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.12+ (source install only)
- **RAM**: 4GB or above
- **Storage**: 500MB+ free space
- **GPU**: OpenGL 3.0+ support

### 🔧 Installation

#### Method 1: Download Release (Recommended)

1. **Download the latest version**

   Go to the [Releases Page](https://gitee.com/waterfeet/DoroPet_V3/releases) and download the latest ZIP package
2. **Extract files**

   Extract the downloaded ZIP to any directory (avoid Chinese characters and special characters in the path)
3. **Run the installation script**

   Double-click `install_env.bat` — the script will automatically:
   - Download Python 3.12 embedded edition
   - Install pip package manager
   - Install all dependencies
   - Configure the runtime environment
4. **Launch the application**

   The app starts automatically after installation, or double-click `start_app.bat` to launch manually

#### Method 2: Build from Source (Developers)

For users who want to contribute or customize the application.

1. **Ensure Python 3.12+ is installed**
2. **Clone the repository**
   ```bash
   git clone https://gitee.com/waterfeet/DoroPet_V3.git
   cd DoroPet_V3
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Launch the application**
   ```bash
   python main.py
   ```

### ⚡ First Run

After launching for the first time:

1. **Configure AI Model** — Go to "Model Config" and add your API Key
2. **Select a model** — Choose your AI model from the dropdown menu
3. **Start chatting** — Click the pet or go to the "AI Chat" page to begin interacting

***

## ✨ Features

### 🎭 Live2D Desktop Pet

| Feature               | Description                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------- |
| **Expression System** | 10+ expressions including happy, confused, sleepy, sunglasses, etc.                      |
| **Motion System**     | Supports idle, jump, touch, and other motions                                            |
| **Mouse Tracking**    | Pet's eyes follow your mouse cursor                                                      |
| **Chase Mode**        | Pet chases your mouse cursor, consuming energy                                           |
| **Random Wander**     | Pet wanders randomly across the screen, with pauses                                      |
| **Speech Bubbles**    | Comic-style dialogue bubbles — pets say random lines based on status, auto-dismiss       |
| **Edge Docking**      | Auto-docks and hides when dragged to screen edges                                        |
| **Scroll Resize**     | Use mouse wheel to resize the pet                                                        |
| **Status Overlay**    | Hover to reveal a four-attribute status bar overlay                                      |
| **Context Menu**      | Lock position, open chat, screenshot & send, toggle status overlay, exit                 |

### 🤖 AI Chat System

Supports multiple mainstream AI model providers:

| Provider           | Model Examples      | Highlights                               |
| ------------------ | ------------------- | ---------------------------------------- |
| **OpenAI**         | GPT-4, GPT-3.5      | Industry leader, comprehensive           |
| **DeepSeek**       | DeepSeek-v4-flash   | Chinese excellence, great value          |
| **Google Gemini**  | Gemini Pro          | Multimodal support                       |
| **Moonshot**       | Kimi                | Long-text processing                     |
| **Zhipu AI**       | GLM-5               | Chinese large language model             |
| **Ollama**         | Local models        | Fully local, privacy-first               |
| Custom             |                     | Any OpenAI-compatible API                |

**Chat feature highlights**:

| Feature             | Description                                                                      |
| ------------------- | -------------------------------------------------------------------------------- |
| **Streaming Output** | Real-time AI reply display, no need to wait for full generation                  |
| **Thinking Mode**    | Visualizes the reasoning process for models like DeepSeek-R1                     |
| **Multi-Session**    | Create/delete/rename sessions with persistent chat history                       |
| **Markdown**         | Full Markdown rendering + code syntax highlighting (Pygments)                    |
| **Tool Calling**     | AI can autonomously invoke search, file ops, image generation — process visible  |
| **Image Generation** | Supports AI drawing APIs, generate images directly in conversation               |
| **Attachments**      | Send PDF/Word/Excel/CSV/TXT/HTML files, auto-extract text                        |
| **Screenshot Tool**  | Built-in region screenshot, send directly to chat                                |
| **Voice Input**      | Integrated speech recognition, type with your voice                              |

### 🎙️ Voice Features

| Feature                          | Description                                                                                   |
| -------------------------------- | --------------------------------------------------------------------------------------------- |
| **Wake Word Detection (KWS)**    | Local wake word "Hey Doro" detection, based on sherpa-onnx                                     |
| **Speech Recognition (ASR)**    | Real-time speech-to-text with BPE tokenization                                                |
| **Speech Synthesis (TTS)**       | Multiple engines: Edge-TTS (Microsoft free) / OpenAI TTS / Gemini TTS / Gradio TTS / Qwen TTS |
| **TTS Caching**                  | Auto-caches synthesized speech to avoid redundant requests                                    |

### 🎮 Pet Simulation System

Four core attributes for an immersive nurturing experience:

| Attribute             | Description                       | Effect                                     |
| --------------------- | --------------------------------- | ------------------------------------------ |
| 🍖 **Hunger**         | Decreases over time, needs feeding| Low hunger accelerates mood decay          |
| 😊 **Mood**           | Boosted through interaction       | Affects pet reactions and dialogue         |
| 🛁 **Cleanliness**    | Declines periodically             | Needs cleaning to maintain                 |
| ⚡ **Energy**          | Consumed by chasing/wandering     | Rest recovers it; affects activity ability |

**Companion gameplay**:

| Category    | Actions                      | Effect                       |
| ----------- | ---------------------------- | ---------------------------- |
| **Feeding** | Snack / Meal / Feast         | Restores hunger              |
| **Playing** | Light / Fun / Intense        | Boosts mood, consumes energy |
| **Cleaning** | Wipe / Bath                | Restores cleanliness         |
| **Resting** | Nap / Deep Sleep             | Restores energy              |
| **Interacting** | Pet / Scold / Comfort    | Affects mood                 |

> 💡 The four attributes have **linked mechanics**: low hunger accelerates mood decay, low mood slows energy recovery, etc. Nurture strategically!

### 📖 Galgame Interactive Storytelling

AI-driven immersive visual novel experience — beyond just "chatting," you enter a complete story world:

| System                 | Description                                                                   |
| ---------------------- | ----------------------------------------------------------------------------- |
| **AI-Driven Narrative** | AI generates story in real-time; every choice branches the plot infinitely    |
| **Protagonist Customization** | Customize name, gender, personality, and backstory                     |
| **Character System**    | Create and manage multiple story characters with traits, appearance, relationships |
| **World Setting**       | Customize world view, era, magic/sci-fi elements, etc.                        |
| **Affection System**   | Interactions affect affection values, influencing character reactions and endings |
| **Economy System**      | Virtual currency, shop, inventory system                                      |
| **Multiple Endings**   | Different endings triggered by accumulated choice conditions                  |
| **Save & Load**        | Full save system — save/load game progress anytime                            |
| **Event Triggers**     | Exclusive events, dynamic events, special date events to make the world alive |
| **HTML Export**        | Export your gameplay journey as an HTML file to share your story              |

### 🎵 Online Music

| Feature               | Description                                                       |
| --------------------- | ----------------------------------------------------------------- |
| **Multi-Platform Search** | Supports Netease / QQ / Kugou and more                        |
| **Playback Engine**    | Based on VLC, supports mainstream audio formats                  |
| **Lyrics Display**     | LRC parsing, synchronized scrolling lyrics                       |
| **Spectrogram Visualization** | Real-time audio spectrum effects                         |
| **Vinyl Record UI**    | Switches to a spinning vinyl record animation during playback     |
| **Playlist Management** | Create and manage local playlists                                |
| **Playback Modes**     | List loop / Shuffle / Single repeat                              |
| **Mini Player**        | A compact player card also appears on the pet status page         |
| **Global Playback**    | Cross-page shared playback state, uninterrupted when switching UI |

### 🔌 Agent Skill System

Built-in tools and skills the AI can invoke, extending AI capabilities from "chatting" to "doing":

**Agent Tools** (AI can invoke autonomously):

| Tool                        | Function                              |
| --------------------------- | ------------------------------------- |
| 🔍 `search_baidu`          | Baidu search                          |
| 🔍 `search_bing`           | Bing search                           |
| 🌐 `visit_webpage`         | Visit webpage and extract content     |
| 🖼️ `generate_image`       | AI image generation                   |
| 📁 `read_file`             | Read file contents                    |
| 📝 `write_file`            | Write to a file                       |
| 📂 `list_files`            | List directory contents               |
| 🔎 `search_files`          | Search for files                      |
| ✏️ `edit_file`             | Edit file (precise replace)           |
| 🎭 `set_expression`        | Control pet expressions               |
| 📊 `modify_pet_attribute`  | Modify pet attribute values           |

**Built-in Skills** (requires self-configuration of runtime environment):

| Skill                        | Purpose                            |
| ---------------------------- | ---------------------------------- |
| 📄 **Word Processing**       | Word document creation & editing   |
| 📊 **Excel Processing**      | Excel spreadsheet handling         |
| 📑 **PDF Processing**        | PDF document processing            |
| 🎞️ **PPT Processing**       | PPT presentation handling          |
| 🌤️ **Weather Query**        | Real-time weather info             |
| 📰 **Daily Hot Topics**      | Aggregated trending topics         |
| 🎨 **Frontend Design**       | Web/UI design generation           |
| 🕸️ **Web Scraping**         | Web content retrieval              |
| 🛠️ **Skill Creator**        | Create custom skills               |

### 🎨 Other Features

| Feature                | Description                                                                             |
| ---------------------- | --------------------------------------------------------------------------------------- |
| 🧠 **Smart Memory**    | AI auto-analyzes message importance (5 levels), extracts long-term memory & keywords    |
| 👤 **Role Play**       | Custom AI persona (System Prompt), bindable to Live2D models for unique characters      |
| 🔌 **Plugin System**   | Dynamic third-party plugin loading; examples: calculator, Ludo, memo, 2048 game         |
| 💬 **Immersive Chat**  | Standalone quick chat window with simplified UI focused on conversation                 |
| 🗄️ **Data Persistence**| SQLite storage for chat history, character settings, pet attributes, Galgame saves      |
| 🗑️ **Cache Management**| Image cache (500MB/7-day auto-cleanup), TTS cache, one-click purge                      |
| 📝 **Runtime Logs**    | Tiered logging (DEBUG~ERROR), real-time log viewer in UI                                |
| 🔤 **Font Scaling**    | Global font size adjustment (90%~150%), adapt to different screens and preferences      |
| 🖥️ **Shortcut**        | Auto-detect and create desktop shortcut                                                  |
| 📌 **Always on Top**   | One-click toggle main window always-on-top status                                        |

***

## 📖 User Guide

### 🖱️ Pet Interaction

| Action            | Effect                                                                |
| ----------------- | --------------------------------------------------------------------- |
| **Single Click**  | Triggers interaction — different body parts have different effects    |
| **Double Click**  | Opens the main interface                                              |
| **Right Click**   | Opens context menu (lock/chat/screenshot/status overlay, etc.)        |
| **Drag**          | Move pet position                                                     |
| **Scroll**        | Resize pet                                                            |
| **Drag to Edge**  | Auto-dock and hide                                                    |
| **Mouse Hover**   | Shows attribute status overlay                                        |

### 📱 Main Interface Navigation

```
┌──────────────────────────────────────────┐
│  🏠 Pet Status  - View attributes, quick actions, mini player  │
│  💬 AI Chat     - Multi-session AI conversations               │
│  🎵 Music Player - Online music search & playback              │
│  🎮 Galgame     - AI interactive storytelling                  │
│  ──────────────────────────────────────  │
│  🤖 Model Config - Configure AI model providers               │
│  🎤 Voice Settings - Configure wake word/ASR/TTS               │
│  🖼️ Live2D Models - Switch/manage/download models             │
│  👤 Role Play   - Customize AI persona settings                │
│  📚 Plugin Manager - Manage installed plugins                  │
│  🎨 Skill Manager - View/install/enable skills                 │
│  📋 Logs        - View application runtime logs                │
│  ──────────────────────────────────────  │
│  🔄 Updates     - Check/install updates (bottom)               │
│  ⚙️ Settings    - Startup/cache/font, etc. (bottom)            │
└──────────────────────────────────────────┘
```

### ⌨️ System Tray

Right-click the tray icon for quick access to:

- Open immersive chat window
- Show/Hide pet
- Show/Hide main interface
- Lock/Unlock pet position
- Exit application

### 🔑 Configure AI Model

1. Go to the "Model Config" page
2. Click "Add Config"
3. Select provider type (OpenAI / DeepSeek / Claude / Gemini / Kimi / Zhipu / Groq / Ollama)
4. Enter API Key and related settings (Base URL, model name, etc.)
5. Save and activate

### 🎮 Start Galgame

1. Go to the "Galgame" page
2. Click the top config panel to set up world view, protagonist, and characters
3. Click "Start New Game" or "Continue"
4. AI generates story in real-time; make choices when options appear
5. Every choice affects story direction, character affection, and ultimately leads to different endings

> 💡 Affection, currency, and items in Galgame are persisted. View items in "Inventory" and character affection in "Affection".

<br />

***

## 🛠️ Development Guide

### Project Structure

```
opendoro/
├── main.py                     # Entry point (dependency check, splash screen, module init)
├── requirements.txt            # Python dependencies
├── install_env.bat             # One-click environment setup script
├── start_app.bat               # Launch script
├── data/
│   ├── icons/                  # Icon resources
│   └── resourse/               # Image resources (screenshots, etc.)
├── md/                         # Project documentation
├── models/
│   └── Doro/                   # Default Live2D model
│       ├── Doro.model3.json    # Model config file
│       ├── expressions/        # Expression files
│       └── motions/            # Motion files
├── plugin/                     # User plugin directory
│   ├── calculation/            # Calculator plugin
│   ├── memo/                   # Memo plugin
│   ├── ludo/                   # Ludo plugin
│   └── DemoDirPlugin/          # Plugin dev demo + 2048 game
├── src/
│   ├── agent/                  # Agent framework
│   │   ├── core/               # Agent core (tool definitions, pipeline, orchestrator, sandbox)
│   │   ├── tools/              # Tool implementations (search, image, file ops, code execution)
│   │   ├── skills/             # Skill system (load, register, validate, status management)
│   │   ├── pipeline/           # Execution pipeline
│   │   └── middleware/         # Middleware
│   ├── core/                   # Core business logic
│   │   ├── pet_attributes_manager.py  # Pet attributes manager
│   │   ├── database.py                # SQLite database (chat, characters, saves)
│   │   ├── voice.py                   # Voice interaction (wake word + ASR)
│   │   ├── tts.py                     # TTS speech synthesis
│   │   ├── memory_manager.py          # AI memory manager
│   │   ├── stream_processor.py        # Stream response processor
│   │   ├── message_parser.py          # Message parser
│   │   ├── mouse_chaser.py            # Mouse chaser
│   │   ├── random_wanderer.py         # Random wanderer
│   │   ├── version_manager.py         # Version update manager
│   │   ├── skill_manager.py           # Skill manager
│   │   └── ...
│   ├── provider/               # AI provider adapter layer
│   │   ├── manager.py          # Provider manager (singleton)
│   │   ├── provider.py         # Abstract base classes (LLM/TTS/STT/Image)
│   │   └── sources/            # Provider implementations
│   ├── services/               # Service layer
│   │   ├── llm_service.py      # LLM invocation service (multi-threaded, tool call loop)
│   │   ├── global_music_player.py  # Global music player (VLC)
│   │   └── extended_music_service.py  # Music search/playlist service
│   ├── skills/                 # Built-in skills directory
│   ├── ui/                     # UI components
│   │   ├── main_window.py      # Main window (FluentWindow navigation)
│   │   ├── pages/              # 12 feature pages
│   │   ├── galgame/            # Galgame subsystem (story gen, save, endings, events)
│   │   ├── music/              # Music UI (search, playlist, spectrogram, lyrics)
│   │   ├── widgets/            # Common UI widgets
│   │   └── windows/            # Standalone windows (immersive chat, pet status overlay)
│   └── utils/                  # Utility functions
├── themes/
│   ├── dark.qss                # Dark theme stylesheet
│   └── light.qss               # Light theme stylesheet
└── tools/                      # Utility scripts
```

### Tech Stack

| Layer                | Technology                                              |
| -------------------- | ------------------------------------------------------- |
| **GUI Framework**    | PyQt5 + PyQt-Fluent-Widgets (Fluent Design)             |
| **Live2D Rendering** | live2d-py + OpenGL (v3)                                 |
| **AI Interface**     | OpenAI SDK (multi-provider compatible), Provider adapter|
| **Voice Processing** | sherpa-onnx (wake word + ASR) + edge-tts / OpenAI TTS   |
| **Database**         | SQLite (chat history, characters, pet data, Galgame saves)|
| **Music Engine**     | VLC + musicdl (multi-platform music search)             |
| **Code Highlighting**| Pygments                                                |

### Extension Development

#### Adding a New AI Provider

1. Create a new provider file in `src/provider/sources/`
2. Inherit from the `LLMProvider` base class
3. Implement required methods (`chat`, `stream_chat`, etc.)
4. Register provider metadata in `src/provider/register.py`

#### Adding a New Skill

1. Create a skill directory in `src/skills/`
2. Write a `SKILL.md` config file (following skill specification)
3. Add execution scripts (optional, for complex skills)
4. Restart the app to auto-load, or refresh from the "Skill Manager" page

#### Developing a Plugin

1. Create a new folder under `plugin/`
2. Create a `main.py` containing a `Plugin` class that inherits from `QWidget`
3. Restart the app — the plugin will auto-appear on the "Plugin Manager" page

***

## ❓ FAQ

<details>
<summary><b>Q: Environment installation failed?</b></summary>

A: Please check the following:

- **Path issues**: Ensure the installation path contains no Chinese characters, spaces, or special characters (e.g., `D:\Software\DoroPet` ❌ → `D:\DoroPet` ✅)
- Check network connectivity
- Check if blocked by antivirus or firewall
- Try running the installation script as administrator

</details>

<details>
<summary><b>Q: Network error when downloading dependencies?</b></summary>

A: The script has built-in multiple mirror sources (Tsinghua, Alibaba, USTC, etc.). If all fail, please check:

- Network connectivity
- Firewall settings
- Try using a VPN or switch network environment

</details>

<details>
<summary><b>Q: Live2D model display issues?</b></summary>

A: Please ensure:

- Graphics driver is up to date
- OpenGL 3.0+ is supported
- Model files are complete and uncorrupted (must include a `.model3.json` config file)

</details>

<details>
<summary><b>Q: AI chat not responding?</b></summary>

A: Please check:

- API Key is correctly configured
- Network can reach the corresponding API address
- Base URL is correct (when using a custom proxy)
- Check the "Logs" page for detailed error information

</details>

<details>
<summary><b>Q: How to add custom Live2D models?</b></summary>

A: Place the model folder in the `models/` directory, ensure it contains a `.model3.json` config file along with related expression/motion/physics files, then select and load it from the "Live2D Models" page.

</details>

<details>
<summary><b>Q: Wake word detection not sensitive enough?</b></summary>

A: Wake word detection uses the local sherpa-onnx model. Recommendations:

- Use in a relatively quiet environment
- Clearly speak the wake word "Hey Doro"
- Ensure microphone permissions are granted
- Adjust parameters in "Voice Settings"

</details>

<details>
<summary><b>Q: How to use Ollama local models?</b></summary>

A:

1. Install [Ollama](https://ollama.com/) locally and pull a model
2. Select the Ollama provider in "Model Config"
3. Set Base URL to `http://localhost:11434/v1` (default address)
4. Enter the model name you pulled in Ollama (e.g., `qwen2.5:7b`)

</details>

<details>
<summary><b>Q: Galgame saves lost?</b></summary>

A: Galgame saves are stored in the SQLite database under the app data directory. They shouldn't be lost under normal circumstances. To back up, check the data directory path in "Settings" and manually back up the relevant data files.

</details>

***

<br />

## 🤝 Contributing

We welcome all forms of contributions!

### Ways to Contribute

- 🐛 Submit bug reports
- 💡 Propose new features
- 📝 Improve documentation
- 🔧 Submit code PRs
- 🎨 Share Live2D models
- 🔌 Develop and share plugins

### Development Workflow

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Submit a Pull Request

***

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

***

## 🙏 Acknowledgments

Thanks to the following open source projects:

- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - GUI Framework
- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) - Fluent Design component library
- [live2d-py](https://github.com/Arkueid/live2d-py) - Live2D Python bindings
- [OpenAI](https://openai.com/) - AI API
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) - Speech recognition & wake word detection
- [edge-tts](https://github.com/rany2/edge-tts) - Microsoft free TTS
- [musicdl](https://github.com/CharlesPikachu/musicdl) - Multi-platform music search

***

<div align="center">

**If this project helps you, please give it a ⭐ Star!**

Made with ❤️ by DoroPet Team

</div>