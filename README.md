# KinTTS

基于 Qwen3-TTS 的本地语音合成插件，支持语音克隆。为 OpenClaw 设计，也可独立使用。

---

## 功能特性

- **文字转语音**：将任意文本合成为自然语音
- **语音克隆**：上传参考音频 + 文字，创建自定义音色
- **多音色管理**：添加、删除、切换默认音色
- **音量调控**：Gain / 防破音 limiter / Attack / Release
- **服务自动拉起**：TTS 服务未启动时自动唤起
- **跨平台部署**：macOS 支持 launchd 自动启动，换电脑 clone 后一键部署

---

## 系统要求

- macOS（launchd 自动启动仅支持 macOS）
- Python 3.10+
- Node.js 18+（仅插件构建需要）
- ffmpeg（音频后处理用）
- 剩余磁盘空间 5GB+（模型约 3.5GB）

---

## 快速安装

### 1. 克隆仓库

```bash
git clone https://github.com/KingsdouDD/KinTTS.git /opt/kin-tts
cd /opt/kin-tts
```

### 2. 下载模型

```bash
# 首次需要网络下载（约 3-5GB，有缓存后不再重复下载）
# 设置 HuggingFace Token（可选，私有模型需要）
export HF_TOKEN="your_huggingface_token"

# 下载模型
bash model/download.sh
```

### 3. 安装 Python 依赖

```bash
cd /opt/kin-tts/tts_service
pip install -r requirements.txt
```

### 4. 配置服务

```bash
# 从模板复制配置文件
cp config_template/config.json tts_service/config/config.json

# 编辑配置（音色目录等）
vim tts_service/config/config.json
```

### 5. 配置 launchd（macOS 自动启动）

```bash
# 复制 plist 到 LaunchAgents
cp launchd/com.kinlang.kintts.plist ~/Library/LaunchAgents/

# 加载服务
launchctl load ~/Library/LaunchAgents/com.kinlang.kintts.plist

# 验证服务状态
curl http://127.0.0.1:18170/health
```

### 6. 安装 OpenClaw 插件（可选）

```bash
cd /opt/kin-tts/openclaw-plugin
npm install
npm run build
openclaw plugins install --entry ./dist/index.js
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `KINTTS_PYTHON` | `/usr/local/bin/python3` | Python 路径 |
| `KINTTS_SERVICE_DIR` | `./tts_service` | TTS 服务根目录 |
| `KINTTS_CONFIG_PATH` | `$KINTTS_SERVICE_DIR/config/config.json` | 配置文件路径 |
| `KINTTS_MODEL_DIR` | `./models` | 模型存放目录 |
| `KINTTS_START_SCRIPT` | `$KINTTS_SERVICE_DIR/scripts/start.py` | 启动脚本路径 |
| `KINTTS_KILL_SCRIPT` | `$KINTTS_SERVICE_DIR/scripts/force_kill.py` | 强制停止脚本路径 |
| `KINTTS_ADD_VOICE_SCRIPT` | `$KINTTS_SERVICE_DIR/scripts/add_voice.py` | 添加音色脚本 |
| `KINTTS_REMOVE_VOICE_SCRIPT` | `$KINTTS_SERVICE_DIR/scripts/remove_voice.py` | 删除音色脚本 |

---

## 项目结构

```
KinTTS/
├── openclaw-plugin/       # OpenClaw 插件（TypeScript）
│   ├── src/              # 插件源码
│   ├── dist/             # 编译产物（npm run build 生成）
│   ├── package.json
│   └── openclaw.plugin.json
├── tts_service/          # TTS 后端 Python 服务
│   ├── scripts/          # 启动/停止/音色管理脚本
│   ├── openclaw/        # OpenClaw Python 工具封装
│   ├── requirements.txt
│   └── pyproject.toml
├── config_template/       # 配置模板（clone 后复制使用）
├── model/
│   └── download.sh       # 模型下载脚本
├── launchd/
│   └── com.kinlang.kintts.plist   # macOS launchd 自动启动配置
└── README.md
```

---

## OpenClaw 工具

插件在 OpenClaw 中注册了以下工具：

| 工具 | 说明 |
|------|------|
| `qwe3_tts` | 文字合成语音 |
| `qwe3_tts_start` | 手动启动服务 |
| `qwe3_tts_health` | 检查服务状态 |
| `qwe3_tts_list_voices` | 列出所有音色 |
| `qwe3_tts_set_default_voice` | 设置默认音色 |
| `qwe3_tts_get_volume` | 查询音量设置 |
| `qwe3_tts_set_volume` | 调节音量 |
| `qwe3_tts_add_voice` | 添加音色（克隆） |
| `qwe3_tts_remove_voice` | 删除音色 |
| `qwe3_tts_unload` | 卸载模型释放内存 |

---

## 独立使用（不依赖 OpenClaw）

TTS 服务独立运行，HTTP 接口直接调用：

```bash
# 启动服务
python3 tts_service/scripts/start.py

# 合成语音
curl -X POST http://127.0.0.1:18170/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，这是语音合成", "voice": "default"}' \
  --output output.wav

# 健康检查
curl http://127.0.0.1:18170/health
```

---

## 模型信息

- **基础模型**：Qwen3-TTS-12Hz-1.7B-Base
- **来源**：https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base
- **大小**：约 3.5GB
- **下载缓存**：设置 `KINTTS_MODEL_DIR` 指向缓存目录，换电脑不重复下载

---

## 常见问题

**Q: 启动报错 "port already in use"**
A: 已有进程占用 18170 端口，执行 `python3 tts_service/scripts/force_kill.py` 后重试。

**Q: 合成声音很慢**
A: 模型首次推理需加载（约 10-30 秒），后续请求会复用已加载模型。设置 `lazy_load: false` 可让模型常驻内存。

**Q: 克隆音色效果不好**
A: 参考音频建议 10-60 秒，清晰无背景音，文字描述准确。参考文本建议 20 字以上。

---

## License

MIT
