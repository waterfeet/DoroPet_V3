# DoroPet - Windows Desktop Pet Assistant

## Project Introduction

DoroPet is a Windows desktop pet project based on Python+Live2D+LLM+Agent Skill, featuring the virtual character Doro as the main interface to provide users with intelligent interactive experiences.

![DoroPet Logo](opendoro/data/icons/logo.png)

### Core Features

- **Vibrant Live2D Virtual Character**: Based on Live2D technology, Doro has rich expressions and movements
- **Intelligent Dialogue Capability**: Integrated with LLM (Large Language Model), supporting natural language interaction
- **Voice Interaction**: Supports voice recognition and synthesis for voice conversations
- **Agent Skill System**: Extensible skill system, supporting custom and installed skills
- **Personalization**: Customize Doro's experience, personality, and behavior
- **System Monitoring**: Real-time system status monitoring and caring reminders
- **Task Management**: Help users manage daily tasks and reminders

## Technical Architecture

### Technology Stack

- **Frontend**: PyQt5 + PyQt-Fluent-Widgets
- **Core**: Python 3.12.10
- **AI Capability**: OpenAI API
- **Animation**: Live2D Python binding
- **Voice**: sherpa-onnx + sounddevice
- **Data Storage**: SQLite database

### Project Structure

```
opendoro/
├── data/            # Data files
│   ├── icons/       # Application icons
│   ├── *.db         # Database files
├── live2dpy/        # Live2D related code
│   └── Live2D-Python/  # Live2D Python binding
├── install_env.bat  # Environment installation script
├── requirements.txt # Dependencies list
└── start_app_background.bat # Startup script
```

## Installation Guide

### System Requirements

- Windows 10/11 64-bit system
- At least 4GB memory
- Network connection (required for first installation and AI features)

### Installation Steps

1. **Clone or download the project**
   - Clone the project from GitHub/Gitee to your local machine
   - Or directly download the ZIP package and extract it

2. **Run the installation script**
   - Double-click to run `opendoro/install_env.bat`
   - The script will automatically:
     - Download and install Python 3.12.10
     - Configure pip environment
     - Install all dependencies
     - Install Live2D components

3. **Start the application**
   - The application will start automatically after installation
   - You can start it later through `start_app_background.bat`

## Usage Instructions

### Basic Operations

- **Mouse Interaction**:
  - Left-click and drag: Move Doro's position
  - Right-click: Open menu
  - Double-click: Talk to Doro

- **Voice Interaction**:
  - Click on Doro or use hotkey to activate voice
  - Directly speak your question or command

### Feature Introduction

1. **Intelligent Dialogue**:
   - Ask about weather, news, knowledge, etc.
   - Chat, tell stories, play games
   - Provide life advice and help

2. **System Monitoring**:
   - Display CPU, memory usage
   - Remind to rest and protect eyes
   - Monitor network status

3. **Task Management**:
   - Create and manage to-do items
   - Set timed reminders
   - Record important events

4. **Agent Skill System**:
   - Install and manage various skills
   - Customize skill behaviors
   - Extend Doro's capabilities through skills

## Configuration Instructions

### API Configuration

To use LLM features, you need to configure OpenAI API key in settings:

1. Open the settings panel
2. Go to "AI Settings" option
3. Enter your OpenAI API key
4. Save configuration

### Voice Settings

When using voice features for the first time, you need to download voice models:

1. Open the settings panel
2. Go to "Voice Settings" option
3. Click "Download Models" button
4. Wait for download to complete

### Skill Settings

Manage and configure Doro's skills:

1. Open the settings panel
2. Go to "Skill Management" option
3. Browse available skills and click "Install" button
4. Configure parameters for installed skills
5. Enable or disable specific skills

## Common Issues

### Installation Failure
- Check if network connection is normal
- Ensure sufficient system permissions
- Try running the installation script as administrator

### Voice Recognition Not Working
- Check if microphone is working properly
- Ensure voice models have been downloaded
- Adjust microphone volume and sensitivity

### AI Dialogue No Response
- Check if API key is correct
- Ensure network connection is normal
- Try restarting the application

## Contribution

1. **Fork the repository**
2. **Create Feat_xxx branch**
3. **Commit your code**
4. **Create Pull Request**

## License

This project uses the MIT License, see [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Live2D](https://www.live2d.com/) - Provides virtual character technology
- [PyQt](https://www.riverbankcomputing.com/software/pyqt/) - Provides GUI framework
- [OpenAI](https://openai.com/) - Provides LLM technology

---

**DoroPet - Your intelligent desktop companion, making life more interesting!**
