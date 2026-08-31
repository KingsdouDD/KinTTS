#!/bin/bash
# 下载 Qwen3-TTS 模型（带缓存，换电脑不重复下载）

set -e

MODEL_DIR="${KINTTS_MODEL_DIR:-./models}"
MODEL_NAME="Qwen3-TTS-12Hz-1.7B-Base"
HUGGINGFACE_REPO="https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base"

echo "[KinTTS] 检查模型目录: $MODEL_DIR/$MODEL_NAME"

if [ -d "$MODEL_DIR/$MODEL_NAME" ]; then
    echo "[KinTTS] 模型已存在，跳过下载: $MODEL_DIR/$MODEL_NAME"
    exit 0
fi

echo "[KinTTS] 开始下载模型（首次约 3-5GB，请耐心等待）..."
mkdir -p "$MODEL_DIR"

# 方法1: huggingface-cli（推荐，需先 pip install huggingface_hub）
if command -v huggingface-cli &> /dev/null; then
    huggingface-cli download "$MODEL_NAME" \
        --local-dir "$MODEL_DIR/$MODEL_NAME" \
        --local-dir-use-symlinks False \
        --token "$HF_TOKEN"
    echo "[KinTTS] 下载完成: $MODEL_DIR/$MODEL_NAME"
    exit 0
fi

# 方法2: Git LFS 克隆（需先安装 git-lfs）
if command -v git &> /dev/null; then
    echo "[KinTTS] 使用 Git LFS 克隆..."
    git lfs install 2>/dev/null || true
    git clone "$HUGGINGFACE_REPO" "$MODEL_DIR/$MODEL_NAME"
    echo "[KinTTS] 下载完成: $MODEL_DIR/$MODEL_NAME"
    exit 0
fi

echo "[KinTTS] 错误: 请安装 huggingface_hub (pip install huggingface_hub) 或 git-lfs"
exit 1
