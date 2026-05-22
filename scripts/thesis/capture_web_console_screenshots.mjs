import fs from "node:fs";
import path from "node:path";
import process from "node:process";

import { chromium } from "/Users/hrzt/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs";

const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:4173";
const OUTPUT_DIR = path.resolve(process.cwd(), "docs/image/ui");
const IMAGE_MAP_PATH = path.resolve(process.cwd(), "docs/image/ui-image-map.json");
const AUTH_STORAGE_KEY = "electric-ai-auth";

const IMAGE_FILE = path.resolve(process.cwd(), "docs/image/paper-ready/generated/prompt_01_sd15-electric.png");
const CHECKED_IMAGE_FILE = path.resolve(process.cwd(), "docs/image/paper-ready/generated/prompt_02_sd15-electric.png");

const NOW = "2026-04-20 14:20:00";
const TASK_ID = 101;
const ASSET_ID = 501;

const apiEnvelope = (data, message = "ok") => ({
  code: 0,
  message,
  data,
  trace_id: "thesis-demo-trace",
});

const models = [
  {
    id: 1,
    model_name: "sd15-electric",
    display_name: "Stable Diffusion 1.5 Electric",
    model_type: "generation",
    service_name: "python-ai-service",
    status: "available",
    description: "SD1.5 baseline generation runtime for electric scenes",
    default_positive_prompt: "500kV substation, industrial realism, detailed power equipment",
    default_negative_prompt: "blurry, low quality, disconnected wires, deformed insulators",
    local_path: "model/generation/sd15-electric",
  },
  {
    id: 2,
    model_name: "sd15-electric-specialized",
    display_name: "Stable Diffusion 1.5 Electric Specialized",
    model_type: "generation",
    service_name: "python-ai-service",
    status: "available",
    description: "Domain-specialized generation runtime for electric scenes",
    default_positive_prompt: "500kV substation yard, detailed equipment, tidy cables, realistic optics",
    default_negative_prompt: "artifact, low quality, broken structure",
    local_path: "model/generation/sd15-electric-specialized",
  },
  {
    id: 3,
    model_name: "ssd1b-electric",
    display_name: "SSD-1B Electric",
    model_type: "generation",
    service_name: "python-ai-service",
    status: "available",
    description: "SSD-1B distilled generation runtime for lower-memory local generation",
    default_positive_prompt: "wind turbines on grassland, clear sky, cinematic lighting",
    default_negative_prompt: "blurry, noisy, distorted geometry",
    local_path: "model/generation/ssd1b-electric",
  },
  {
    id: 11,
    model_name: "electric-score-v1",
    display_name: "Electric Score V1 (Legacy)",
    model_type: "scoring",
    service_name: "python-ai-service",
    status: "available",
    description: "Legacy scorer based on ImageReward, CLIP-IQA and aesthetic predictor",
    default_positive_prompt: "",
    default_negative_prompt: "",
    local_path: "model/scoring/electric-score-v1",
  },
  {
    id: 12,
    model_name: "electric-score-v2",
    display_name: "Electric Score V2 (Electric Domain)",
    model_type: "scoring",
    service_name: "python-ai-service",
    status: "available",
    description: "Retrained four-dimension scorer with electric-domain optimization",
    default_positive_prompt: "",
    default_negative_prompt: "",
    local_path: "model/scoring/electric-score-v2",
  },
];

const task = {
  id: TASK_ID,
  job_type: "generate",
  status: "completed",
  stage: "completed",
  error_message: "",
  model_name: "sd15-electric",
  scoring_model_name: "electric-score-v2",
  prompt: "modern electrical substation yard, high-voltage breakers and transformers, realistic optics",
  negative_prompt: "blurry, low quality, distorted wires",
  payload_json: JSON.stringify({
    prompt: "modern electrical substation yard, high-voltage breakers and transformers, realistic optics",
    negative_prompt: "blurry, low quality, distorted wires",
    model_name: "sd15-electric",
    scoring_model_name: "electric-score-v2",
    seed: 42,
    steps: 20,
    guidance_scale: 7.5,
    width: 512,
    height: 512,
    num_images: 1,
  }),
  created_at: NOW,
  updated_at: NOW,
};

const auditEvents = [
  {
    id: 1,
    job_id: TASK_ID,
    event_type: "task.preparing",
    message: "任务进入准备阶段",
    payload_json: JSON.stringify({ job_id: TASK_ID }),
    created_at: "2026-04-20 14:20:01",
  },
  {
    id: 2,
    job_id: TASK_ID,
    event_type: "model.prepare",
    message: "模型加载完成",
    payload_json: JSON.stringify({ model_name: "sd15-electric" }),
    created_at: "2026-04-20 14:20:03",
  },
  {
    id: 3,
    job_id: TASK_ID,
    event_type: "generation.completed",
    message: "生成完成",
    payload_json: JSON.stringify({ count: 1 }),
    created_at: "2026-04-20 14:20:10",
  },
  {
    id: 4,
    job_id: TASK_ID,
    event_type: "scoring.completed",
    message: "评分完成",
    payload_json: JSON.stringify({ scoring_model_name: "electric-score-v2" }),
    created_at: "2026-04-20 14:20:12",
  },
  {
    id: 5,
    job_id: TASK_ID,
    event_type: "task.completed",
    message: "任务已完成",
    payload_json: JSON.stringify({ asset_count: 1 }),
    created_at: "2026-04-20 14:20:13",
  },
];

const historyItem = {
  id: ASSET_ID,
  job_id: TASK_ID,
  image_name: "prompt_01_sd15-electric.png",
  file_path: "docs/image/paper-ready/generated/prompt_01_sd15-electric.png",
  model_name: "sd15-electric",
  status: "generated",
  positive_prompt: task.prompt,
  negative_prompt: task.negative_prompt,
  sampling_steps: 20,
  seed: 42,
  guidance_scale: 7.5,
  created_at: NOW,
  visual_fidelity: 53.52,
  text_consistency: 43.24,
  physical_plausibility: 37.64,
  composition_aesthetics: 65.81,
  total_score: 48.12,
};

const assetDetail = {
  asset: {
    id: ASSET_ID,
    job_id: TASK_ID,
    image_name: historyItem.image_name,
    file_path: historyItem.file_path,
    model_name: historyItem.model_name,
    status: historyItem.status,
    created_at: NOW,
    updated_at: NOW,
  },
  prompt: {
    positive_prompt: historyItem.positive_prompt,
    negative_prompt: historyItem.negative_prompt,
    sampling_steps: historyItem.sampling_steps,
    seed: historyItem.seed,
    guidance_scale: historyItem.guidance_scale,
  },
  score: {
    visual_fidelity: historyItem.visual_fidelity,
    text_consistency: historyItem.text_consistency,
    physical_plausibility: historyItem.physical_plausibility,
    composition_aesthetics: historyItem.composition_aesthetics,
    total_score: historyItem.total_score,
  },
  checked_image_path: "docs/image/paper-ready/generated/prompt_02_sd15-electric.png",
  score_explanation: {
    checked_image_path: "docs/image/paper-ready/generated/prompt_02_sd15-electric.png",
    dimensions: {
      visual_fidelity: {
        uses_yolo: true,
        summary: "设备边缘较清晰，主要结构完整。",
        formula: "视觉分 = 图像特征评分 + 校准映射",
        details: ["主设备轮廓清楚", "局部纹理保持较稳定"],
        expected_classes: ["bus", "switch", "insulator"],
        matched_classes: ["bus", "switch"],
        missing_classes: ["insulator"],
        detections: [{ class_name: "bus", confidence: 0.91 }, { class_name: "switch", confidence: 0.88 }],
      },
      text_consistency: {
        uses_yolo: false,
        summary: "提示词中的变电站主体表达基本到位，但细粒度部件覆盖有限。",
        formula: "文本分 = ImageReward / 学生模型文本分",
        details: ["变电站场景语义正确", "设备数量与提示词约束存在轻微偏差"],
      },
      physical_plausibility: {
        uses_yolo: true,
        summary: "主要设备关系较为合理，但部分局部连接仍可优化。",
        formula: "物理分 = CLIP-IQA / 学生模型物理分 + 检测增强",
        details: ["主设备布局自然", "局部绝缘结构表达略弱"],
      },
      composition_aesthetics: {
        uses_yolo: false,
        summary: "画面主体清晰，层次分明，适合作为平台展示样例。",
        formula: "构图分 = 美学预测分 + 校准",
        details: ["主体居中明显", "画面光照统一"],
      },
    },
  },
};

const historyPage = {
  items: [historyItem],
  page: 1,
  page_size: 10,
  total: 1,
  total_pages: 1,
};

function ensureOutputDir() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

function setAuthStorage(page) {
  return page.addInitScript(([key, payload]) => {
    window.localStorage.setItem(key, JSON.stringify(payload));
  }, [
    AUTH_STORAGE_KEY,
    {
      accessToken: "demo-token",
      userName: "admin",
      displayName: "System Admin",
    },
  ]);
}

async function fulfillJson(route, payload, message = "ok") {
  await route.fulfill({
    status: 200,
    contentType: "application/json; charset=utf-8",
    body: JSON.stringify(apiEnvelope(payload, message)),
  });
}

async function fulfillImage(route, filePath) {
  await route.fulfill({
    status: 200,
    contentType: "image/png",
    body: fs.readFileSync(filePath),
  });
}

async function installMocks(context) {
  await context.route("**/api/v1/auth/login", async (route) => {
    await fulfillJson(route, {
      access_token: "demo-token",
      user_name: "admin",
      display_name: "System Admin",
    });
  });

  await context.route("**/api/v1/models**", async (route) => {
    await fulfillJson(route, models);
  });

  await context.route("**/api/v1/tasks/generate", async (route) => {
    await fulfillJson(route, task, "task-create");
  });

  await context.route("**/api/v1/tasks/" + TASK_ID, async (route) => {
    await fulfillJson(route, task, "task-detail");
  });

  await context.route("**/api/v1/tasks", async (route) => {
    await fulfillJson(route, [task], "task-list");
  });

  await context.route("**/api/v1/assets/history/page**", async (route) => {
    await fulfillJson(route, historyPage, "asset-history-page");
  });

  await context.route("**/api/v1/assets/history/" + ASSET_ID, async (route) => {
    await fulfillJson(route, assetDetail, "asset-detail");
  });

  await context.route("**/api/v1/assets/history**", async (route) => {
    await fulfillJson(route, [historyItem], "asset-history");
  });

  await context.route("**/api/v1/audit/tasks/" + TASK_ID + "/events", async (route) => {
    await fulfillJson(route, auditEvents, "audit-events");
  });

  await context.route("**/files/image-checks/**", async (route) => {
    await fulfillImage(route, CHECKED_IMAGE_FILE);
  });

  await context.route("**/files/images/**", async (route) => {
    await fulfillImage(route, IMAGE_FILE);
  });
}

async function capture(page, name, options = {}) {
  const outputPath = path.join(OUTPUT_DIR, name);
  if (options.selector) {
    await page.locator(options.selector).first().screenshot({ path: outputPath, type: "png" });
  } else {
    await page.screenshot({ path: outputPath, type: "png", fullPage: options.fullPage ?? true });
  }
  return outputPath;
}

async function main() {
  ensureOutputDir();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  await installMocks(context);
  const page = await context.newPage();

  const imageMap = {};

  try {
    await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle" });
    await page.getByText("工业电力图像生成与评分平台").waitFor();
    imageMap["登录与统一入口"] = await capture(page, "login-view.png");

    await setAuthStorage(page);

    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: "networkidle" });
    await page.locator(".hero-eyebrow").filter({ hasText: "平台概览" }).first().waitFor();
    imageMap["概览页"] = await capture(page, "dashboard-view.png");

    await page.goto(`${BASE_URL}/models`, { waitUntil: "networkidle" });
    await page.locator(".hero-title").filter({ hasText: "模型中心" }).first().waitFor();
    imageMap["模型中心"] = await capture(page, "model-center-view.png");

    await page.goto(`${BASE_URL}/generate`, { waitUntil: "networkidle" });
    await page.locator(".status-title").filter({ hasText: "实时状态" }).first().waitFor();
    await page.getByRole("button", { name: /提交真实生成任务/i }).first().click().catch(() => {});
    await page.waitForTimeout(2500);
    imageMap["生成工作台"] = await capture(page, "generate-view.png");

    await page.goto(`${BASE_URL}/history`, { waitUntil: "networkidle" });
    await page.locator(".table-title").filter({ hasText: "历史中心" }).first().waitFor();
    imageMap["历史中心与详情"] = await capture(page, "history-view.png");

    await page.goto(`${BASE_URL}/tasks/audit/101`, { waitUntil: "networkidle" });
    await page.locator(".summary-title").filter({ hasText: "任务 #101" }).first().waitFor();
    imageMap["任务审计"] = await capture(page, "task-audit-view.png");
  } finally {
    fs.writeFileSync(IMAGE_MAP_PATH, JSON.stringify(imageMap, null, 2), "utf8");
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
