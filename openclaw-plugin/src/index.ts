import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";
import { spawn, spawnSync } from "child_process";
import { existsSync, readFileSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

// ── 路径配置（全部通过环境变量或相对路径，兼容所有部署路径）────────────
// KINTTS_PYTHON        → Python 解释器路径（默认: python3）
// KINTTS_TTS_DIR       → TTS 服务根目录（默认: ../qwe3 TTS，相对于 workspace）
// KINTTS_CONFIG_PATH   → config.json 路径（默认: {TTS_DIR}/config/config.json）
// KINTTS_SERVICE_DIR   → 服务根目录别名，等同 TTS_DIR

const __dirname = dirname(fileURLToPath(import.meta.url));

function resolveTtsDir(): string {
  if (process.env.KINTTS_TTS_DIR || process.env.KINTTS_SERVICE_DIR) {
    return process.env.KINTTS_TTS_DIR || process.env.KINTTS_SERVICE_DIR!;
  }
  // 插件装在 openclaw-workspace/xxx-plugin/ 下，workspace 是父目录的父目录
  const workspace = resolve(__dirname, "../../..");
  return resolve(workspace, "qwe3 TTS");
}

const TTS_DIR = resolveTtsDir();

function getEnv(key: string, fallback: string): string {
  return process.env[key] || fallback;
}

const PYTHON = getEnv("KINTTS_PYTHON", "python3");
const START_SCRIPT = getEnv("KINTTS_START_SCRIPT", resolve(TTS_DIR, "scripts/start.py"));
const FORCE_KILL_SCRIPT = getEnv("KINTTS_KILL_SCRIPT", resolve(TTS_DIR, "scripts/force_kill.py"));
const CONFIG_PATH = getEnv("KINTTS_CONFIG_PATH", resolve(TTS_DIR, "config/config.json"));
const ADD_VOICE_SCRIPT = getEnv("KINTTS_ADD_VOICE_SCRIPT", resolve(TTS_DIR, "scripts/add_voice.py"));
const REMOVE_VOICE_SCRIPT = getEnv("KINTTS_REMOVE_VOICE_SCRIPT", resolve(TTS_DIR, "scripts/remove_voice.py"));
const UNLOAD_SCRIPT = getEnv("KINTTS_UNLOAD_SCRIPT", resolve(TTS_DIR, "scripts/unload_model.py"));

// ── 服务地址 ─────────────────────────────────────────────────
const TTS_URL = "http://127.0.0.1:18170/tts";
const HEALTH_URL = "http://127.0.0.1:18170/health";
const VOICES_URL = "http://127.0.0.1:18170/voices";

// ── 默认音色策略 ─────────────────────────────────────────────
// 不硬编码任何音色名，优先从 config.voices.default 读，
// 读不到则取音色列表第一项，再读不到才用 "default"
async function getDefaultVoice(): Promise<string> {
  try {
    const cfg = JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
    if (cfg.voices?.default) return cfg.voices.default;
  } catch { /* ignore */ }
  try {
    const res = await fetch(VOICES_URL, { signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      const json = await res.json() as { voices?: string[] };
      if (json.voices?.length) return json.voices[0];
    }
  } catch { /* ignore */ }
  return "default";
}

function setDefaultVoice(voiceId: string): void {
  try {
    const cfg = JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
    cfg.voices = cfg.voices ?? {};
    cfg.voices.default = voiceId;
    writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2), "utf-8");
  } catch (e) {
    throw new Error(`更新默认音色失败: ${e}`);
  }
}

// ── 音量配置 ─────────────────────────────────────────────────

function getVolumeSettings() {
  try {
    const cfg = JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
    const vol = cfg.volume ?? {};
    return {
      gain: vol.gain ?? 1.5,
      limit: vol.limit ?? 0.95,
      attack: vol.attack ?? 5,
      release: vol.release ?? 20,
    };
  } catch {
    return { gain: 1.5, limit: 0.95, attack: 5, release: 20 };
  }
}

function setVolumeSettings(gain: number, limit: number, attack: number, release: number): void {
  try {
    const cfg = JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
    cfg.volume = { gain, limit, attack, release };
    writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2), "utf-8");
  } catch (e) {
    throw new Error(`更新音量设置失败: ${e}`);
  }
}

// ─── helpers ─────────────────────────────────────────────────────────────────

function runPython(scriptPath: string, args: string[] = []): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn(PYTHON, [scriptPath, ...args], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (d) => (stdout += d));
    child.stderr?.on("data", (d) => (stderr += d));
    child.on("close", (code) => {
      if (code === 0) resolve(stdout.trim());
      else reject(new Error(stderr || `exit ${code}`));
    });
    child.on("error", reject);
  });
}

async function isServiceRunning(): Promise<boolean> {
  try {
    const res = await fetch(HEALTH_URL, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function isServiceHealthy(): Promise<boolean> {
  try {
    const res = await fetch(HEALTH_URL, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return false;
    const body = await res.json();
    return body && body.status === "ok";
  } catch {
    return false;
  }
}

async function ensureService(): Promise<void> {
  if (await isServiceHealthy()) return;
  await runPython(FORCE_KILL_SCRIPT);
  await runPython(START_SCRIPT);
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    if (await isServiceHealthy()) return;
  }
  throw new Error("服务启动超时，请检查 logs/qwe3-tts.log");
}

async function ensureModelLoaded(): Promise<void> {
  await ensureService();
  const res = await fetch(HEALTH_URL, { signal: AbortSignal.timeout(2000) });
  if (!res.ok) throw new Error(`健康检查失败：${res.status}`);
  const health = await res.json() as { model_loaded?: boolean };
  if (health.model_loaded) return;
  const loadRes = await fetch("http://127.0.0.1:18170/load", {
    signal: AbortSignal.timeout(120000),
  });
  if (!loadRes.ok) throw new Error(`模型加载失败：${loadRes.status}`);
}

// ─── plugin ──────────────────────────────────────────────────────────────────

export default defineToolPlugin({
  id: "qwe3-tts",
  name: "qwe3 TTS",
  description: "qwe3 TTS 语音合成服务，支持语音克隆。服务未启动时自动拉起。",
  tools: (tool) => [
    // 语音合成
    tool({
      name: "qwe3_tts",
      label: "qwe3 TTS 语音合成",
      description: "将文字合成为语音。voice 不传则使用当前默认音色（可用 qwe3_tts_set_default_voice 切换）。",
      parameters: Type.Object({
        text: Type.String({ description: "要合成的文字内容" }),
        voice: Type.Optional(
          Type.String({ description: "音色 ID，不传则使用当前默认音色" })
        ),
        language: Type.Optional(
          Type.String({ description: "语言 Chinese 或 English（默认 Chinese）" })
        ),
      }),
      execute: async ({ text, voice, language }) => {
        await ensureModelLoaded();
        const v = voice ?? (await getDefaultVoice());
        const l = language ?? "Chinese";
        const res = await fetch(TTS_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, voice: v, language: l }),
        });
        if (!res.ok) throw new Error(`TTS 请求失败：${res.status}`);
        const json = await res.json() as { success?: boolean; output?: string; duration?: number; error?: string };
        if (!json.success) throw new Error(`TTS 合成失败：${json.error}`);

        const vol = getVolumeSettings();
        const gainDb = (Math.log10(vol.gain) * 20).toFixed(1) + "dB";
        const path = json.output!;
        const boosted = path.replace(".wav", "_boosted.wav");
        const af = `volume=${gainDb},alimiter=limit=${vol.limit}:attack=${vol.attack}:release=${vol.release}`;
        spawnSync("ffmpeg", ["-i", path, "-af", af, "-y", boosted], { stdio: "ignore" });
        spawnSync("mv", ["-f", boosted, path]);

        return { audioPath: json.output, duration: json.duration, voice: v };
      },
    }),

    // 启动服务
    tool({
      name: "qwe3_tts_start",
      label: "qwe3 TTS 启动服务",
      description: "启动本地 qwe3 TTS 服务（如果已启动则无操作）。",
      parameters: Type.Object({}),
      execute: async () => {
        if (await isServiceRunning()) return { status: "already_running" };
        await runPython(START_SCRIPT);
        for (let i = 0; i < 30; i++) {
          await new Promise((r) => setTimeout(r, 1000));
          if (await isServiceRunning()) return { status: "started" };
        }
        throw new Error("服务启动超时，请检查 logs/qwe3-tts.log");
      },
    }),

    // 健康检查
    tool({
      name: "qwe3_tts_health",
      label: "qwe3 TTS 健康检查",
      description: "检查本地 qwe3 TTS 服务运行状态。",
      parameters: Type.Object({}),
      execute: async () => {
        const running = await isServiceRunning();
        if (!running) return { running: false };
        try {
          const res = await fetch(HEALTH_URL, { signal: AbortSignal.timeout(2000) });
          return await res.json();
        } catch {
          return { running: false };
        }
      },
    }),

    // 列出所有音色
    tool({
      name: "qwe3_tts_list_voices",
      label: "qwe3 TTS 列出音色",
      description: "列出本地 qwe3 TTS 所有已注册的音色。",
      parameters: Type.Object({}),
      execute: async () => {
        await ensureService();
        const res = await fetch(VOICES_URL, { signal: AbortSignal.timeout(5000) });
        if (!res.ok) throw new Error(`获取音色列表失败：${res.status}`);
        const json = await res.json() as { voices: string[] };
        return { voices: json.voices };
      },
    }),

    // 设置默认音色
    tool({
      name: "qwe3_tts_set_default_voice",
      label: "qwe3 TTS 设置默认音色",
      description: "修改 config/config.json 中的默认音色。修改后立即生效，不需要重启网关。",
      parameters: Type.Object({
        voice_id: Type.String({ description: "要设为默认的音色 ID" }),
      }),
      execute: async ({ voice_id }) => {
        setDefaultVoice(voice_id);
        return { result: `默认音色已切换为: ${voice_id}` };
      },
    }),

    // 查询音量设置
    tool({
      name: "qwe3_tts_get_volume",
      label: "qwe3 TTS 查询音量设置",
      description: "查询当前 TTS 音量增益和防破音峰值设置。",
      parameters: Type.Object({}),
      execute: async () => {
        return getVolumeSettings();
      },
    }),

    // 设置音量
    tool({
      name: "qwe3_tts_set_volume",
      label: "qwe3 TTS 设置音量",
      description: "调节 TTS 合成后的音量增益（gain）和防破音峰值（limit）。gain=1.5 表示音量 1.5 倍（约 +3.5dB），limit=0.95 表示限制输出峰值为 0.95（防止破音）。",
      parameters: Type.Object({
        gain: Type.Optional(Type.Number({ description: "音量增益，如 1.5（1.5 倍）、2.0（2 倍）。默认 1.5" })),
        limit: Type.Optional(Type.Number({ description: "防破音峰值，0.0625~1 之间，如 0.95。默认 0.95" })),
        attack: Type.Optional(Type.Number({ description: "limiter attack 毫秒，默认 5" })),
        release: Type.Optional(Type.Number({ description: "limiter release 毫秒，默认 20" })),
      }),
      execute: async ({ gain, limit, attack, release }) => {
        const cur = getVolumeSettings();
        setVolumeSettings(
          gain ?? cur.gain,
          limit ?? cur.limit,
          attack ?? cur.attack,
          release ?? cur.release,
        );
        const updated = getVolumeSettings();
        return { result: `音量已更新: gain=${updated.gain}, limit=${updated.limit}`, ...updated };
      },
    }),

    // 添加音色
    tool({
      name: "qwe3_tts_add_voice",
      label: "qwe3 TTS 添加音色",
      description:
        "添加新的声音到 qwe3 TTS。音色 ID 不能与现有音色重复。" +
        "reference_text 建议传入，合成效果更好。",
      parameters: Type.Object({
        voice_id: Type.String({ description: "音色唯一标识符，如 my_voice" }),
        reference_audio: Type.String({ description: "参考音频文件路径（支持任意格式，ffmpeg 会自动转码为 float32 WAV）" }),
        reference_text: Type.Optional(
          Type.String({ description: "参考音频对应的文本（不填则 reference_text 为空）" })
        ),
        language: Type.Optional(
          Type.String({ description: "语言 Chinese 或 English（默认 Chinese）" })
        ),
      }),
      execute: async ({ voice_id, reference_audio, reference_text, language }) => {
        if (!existsSync(reference_audio)) throw new Error(`文件不存在：${reference_audio}`);
        await ensureService();
        const args = [voice_id, reference_audio];
        if (reference_text) args.push("--text", reference_text);
        if (language) args.push(language);
        const out = await runPython(ADD_VOICE_SCRIPT, args);
        return { result: out };
      },
    }),

    // 删除音色
    tool({
      name: "qwe3_tts_remove_voice",
      label: "qwe3 TTS 删除音色",
      description: "从 qwe3 TTS 删除指定音色。",
      parameters: Type.Object({
        voice_id: Type.String({ description: "要删除的音色 ID" }),
      }),
      execute: async ({ voice_id }) => {
        const out = await runPython(REMOVE_VOICE_SCRIPT, [voice_id]);
        return { result: out };
      },
    }),

    // 卸载模型
    tool({
      name: "qwe3_tts_unload",
      label: "qwe3 TTS 卸载模型",
      description: "将模型从内存中卸载，释放显存/CPU 占用。服务保持运行。",
      parameters: Type.Object({}),
      execute: async () => {
        await ensureService();
        const out = await runPython(UNLOAD_SCRIPT);
        return { result: out };
      },
    }),
  ],
});
