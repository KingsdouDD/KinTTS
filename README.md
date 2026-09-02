# KinTTS

Local voice cloning TTS service based on Qwen3-TTS, with an OpenClaw plugin. Can be used standalone or with OpenClaw.

---

## Features

- **Text-to-Speech**: Convert any text into natural speech
- **Voice Cloning**: Upload reference audio + text to create custom voices
- **Multi-Voice Management**: Add, remove, and switch default voices
- **Volume Control**: Gain / anti-clipping limiter / Attack / Release
- **Auto Service Startup**: TTS service wakes automatically if not running
- **Cross-Platform**: macOS launchd auto-start supported; one-command deploy after clone

---

## System Requirements

- macOS (launchd auto-start macOS only)
- Python 3.10+
- Node.js 18+ (only needed for plugin build)
- ffmpeg (for audio post-processing)
- 5GB+ free disk space (model ~3.5GB)

---

## Quick Install

### 1. Clone the Repo

```bash
git clone https://github.com/KingsdouDD/KinTTS.git /opt/kin-tts
cd /opt/kin-tts
```

### 2. Download the Model

```bash
# First run downloads (~3-5GB, cached after first download)
# Optional: set HuggingFace token for private models
export HF_TOKEN="your_huggingface_token"

bash model/download.sh
```

### 3. Install Python Dependencies

```bash
cd /opt/kin-tts/tts_service
pip install -r requirements.txt
```

### 4. Configure Service

```bash
# Copy config from template
cp config_template/config.json tts_service/config/config.json

# Edit config (voice directory, etc.)
vim tts_service/config/config.json
```

### 5. Configure launchd (macOS Auto-Start)

```bash
# Copy plist to LaunchAgents
cp launchd/com.kinlang.kintts.plist ~/Library/LaunchAgents/

# Load service
launchctl load ~/Library/LaunchAgents/com.kinlang.kintts.plist

# Verify
curl http://127.0.0.1:18170/health
```

### 6. Install OpenClaw Plugin (optional)

```bash
cd /opt/kin-tts/openclaw-plugin
npm install
npm run build
openclaw plugins install --entry ./dist/index.js
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KINTTS_PYTHON` | `/usr/local/bin/python3` | Python interpreter path |
| `KINTTS_SERVICE_DIR` | `./tts_service` | TTS service root directory |
| `KINTTS_CONFIG_PATH` | `$KINTTS_SERVICE_DIR/config/config.json` | Config file path |
| `KINTTS_MODEL_DIR` | `./models` | Model storage directory |
| `KINTTS_START_SCRIPT` | `$KINTTS_SERVICE_DIR/scripts/start.py` | Start script path |
| `KINTTS_KILL_SCRIPT` | `$KINTTS_SERVICE_DIR/scripts/force_kill.py` | Force stop script path |
| `KINTTS_ADD_VOICE_SCRIPT` | `$KINTTS_SERVICE_DIR/scripts/add_voice.py` | Voice add script path |
| `KINTTS_REMOVE_VOICE_SCRIPT` | `$KINTTS_SERVICE_DIR/scripts/remove_voice.py` | Voice remove script path |

---

## Project Structure

```
KinTTS/
├── openclaw-plugin/       # OpenClaw plugin (TypeScript)
│   ├── src/              # Plugin source
│   ├── dist/             # Build output (npm run build)
│   ├── package.json
│   └── openclaw.plugin.json
├── tts_service/          # TTS backend Python service
│   ├── scripts/          # Start/stop/voice management scripts
│   ├── openclaw/        # OpenClaw Python tool wrappers
│   ├── requirements.txt
│   └── pyproject.toml
├── config_template/       # Config template (copy after clone)
├── model/
│   └── download.sh       # Model download script
├── launchd/
│   └── com.kinlang.kintts.plist   # macOS launchd auto-start config
└── README.md
```

---

## OpenClaw Tools

The plugin registers the following tools in OpenClaw:

| Tool | Description |
|------|-------------|
| `qwe3_tts` | Synthesize text to speech |
| `qwe3_tts_start` | Manually start service |
| `qwe3_tts_health` | Check service status |
| `qwe3_tts_list_voices` | List all available voices |
| `qwe3_tts_set_default_voice` | Set default voice |
| `qwe3_tts_get_volume` | Query volume settings |
| `qwe3_tts_set_volume` | Adjust volume |
| `qwe3_tts_add_voice` | Add a new voice (clone) |
| `qwe3_tts_remove_voice` | Remove a voice |
| `qwe3_tts_unload` | Unload model to free memory |

---

## Standalone Usage (without OpenClaw)

TTS service runs independently, HTTP interface:

```bash
# Start service
python3 tts_service/scripts/start.py

# Synthesize speech
curl -X POST http://127.0.0.1:18170/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is speech synthesis", "voice": "default"}' \
  --output output.wav

# Health check
curl http://127.0.0.1:18170/health
```

---

## Model Info

- **Base Model**: Qwen3-TTS-12Hz-1.7B-Base
- **Source**: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base
- **Size**: ~3.5GB
- **Download Cache**: Set `KINTTS_MODEL_DIR` to cache directory to avoid re-download on new machines

---

## FAQ

**Q: "port already in use" on startup**
A: Another process is using port 18170. Run `python3 tts_service/scripts/force_kill.py` then retry.

**Q: Speech synthesis is slow**
A: First inference needs to load the model (~10-30s). Subsequent requests reuse the loaded model. Set `lazy_load: false` to keep model resident in memory.

**Q: Cloned voice quality is poor**
A: Reference audio should be 10-60 seconds, clear with no background noise, and text description should be accurate. Reference text is recommended to be 20+ characters.

---

## License

MIT
