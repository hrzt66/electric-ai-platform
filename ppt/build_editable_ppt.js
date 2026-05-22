const path = require("path");
const PptxGenJS = require("/Users/hrzt/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pptxgenjs");

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "OpenAI Codex";
pptx.company = "OpenAI";
pptx.subject = "基于AI生成电力图像及多维度质量评价 毕业答辩";
pptx.title = "基于AI生成电力图像及多维度质量评价 - 可编辑版";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN",
};

const base = "/Users/hrzt/code/vibe coding/codex/毕业设计/electric-ai-platform/ppt";
const img = (name) => path.join(base, name);
const bg = "/Users/hrzt/Downloads/ChatGPT Image 2026年5月15日 18_11_37.png";
const theme = {
  blue: "002FA7",
  ink: "0A0A0A",
  paper: "FAFAF8",
  light: "F2F2EE",
  border: "D8D8D2",
  text2: "505050",
  white: "FFFFFF",
};

function addHeader(slide, left, right, opts = {}) {
  slide.addText(left, {
    x: 0.5,
    y: 0.2,
    w: 5.4,
    h: 0.2,
    fontFace: "Aptos",
    fontSize: 9,
    color: opts.light ? "EAEAEA" : "666666",
    bold: false,
    charSpace: 1.2,
    margin: 0,
  });
  slide.addText(right, {
    x: 10.8,
    y: 0.2,
    w: 2.0,
    h: 0.2,
    fontFace: "Aptos",
    fontSize: 9,
    color: opts.light ? "EAEAEA" : "666666",
    align: "right",
    margin: 0,
  });
}

function addTitle(slide, kicker, title, subtitle) {
  slide.addText(kicker, {
    x: 0.7,
    y: 0.7,
    w: 4.8,
    h: 0.25,
    fontFace: "Aptos",
    fontSize: 10,
    color: "666666",
    bold: false,
    charSpace: 1.5,
    margin: 0,
  });
  slide.addText(title, {
    x: 0.7,
    y: 1.0,
    w: 6.6,
    h: 0.7,
    fontFace: "Microsoft YaHei",
    fontSize: 24,
    color: theme.ink,
    bold: false,
    margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.7,
      y: 1.8,
      w: 7.2,
      h: 0.6,
      fontFace: "Microsoft YaHei",
      fontSize: 11,
      color: theme.text2,
      margin: 0,
    });
  }
}

function addBulletList(slide, items, box, opts = {}) {
  const runs = [];
  for (const item of items) {
    runs.push({
      text: item,
      options: {
        bullet: { indent: 14 },
        hanging: 2,
      },
    });
  }
  slide.addText(runs, {
    x: box.x,
    y: box.y,
    w: box.w,
    h: box.h,
    fontFace: "Microsoft YaHei",
    fontSize: opts.fontSize || 12,
    color: opts.color || theme.ink,
    breakLine: true,
    paraSpaceAfterPt: opts.paraSpaceAfterPt || 10,
    valign: "top",
    margin: 2,
    fit: "shrink",
  });
}

function addCard(slide, title, body, box, accent = false) {
  slide.addShape(pptx.ShapeType.rect, {
    x: box.x,
    y: box.y,
    w: box.w,
    h: box.h,
    line: { color: accent ? theme.blue : theme.border, pt: accent ? 1.5 : 1 },
    fill: { color: accent ? theme.blue : theme.light },
    radius: 0,
  });
  slide.addText(title, {
    x: box.x + 0.15,
    y: box.y + 0.12,
    w: box.w - 0.3,
    h: 0.25,
    fontFace: "Aptos",
    fontSize: 10,
    color: accent ? theme.white : "444444",
    bold: true,
    margin: 0,
  });
  slide.addText(body, {
    x: box.x + 0.15,
    y: box.y + 0.42,
    w: box.w - 0.3,
    h: box.h - 0.52,
    fontFace: "Microsoft YaHei",
    fontSize: 11,
    color: accent ? theme.white : theme.text2,
    margin: 0,
    fit: "shrink",
    valign: "top",
  });
}

function addImageCaption(slide, imagePath, caption, subcaption, box, contain = true) {
  slide.addImage({
    path: imagePath,
    x: box.x,
    y: box.y,
    w: box.w,
    h: box.h,
    sizing: contain ? { type: "contain", x: box.x, y: box.y, w: box.w, h: box.h } : { type: "cover", x: box.x, y: box.y, w: box.w, h: box.h },
  });
  slide.addText(caption, {
    x: box.x,
    y: box.y + box.h + 0.06,
    w: box.w,
    h: 0.2,
    fontFace: "Microsoft YaHei",
    fontSize: 10,
    color: theme.ink,
    bold: true,
    margin: 0,
  });
  if (subcaption) {
    slide.addText(subcaption, {
      x: box.x,
      y: box.y + box.h + 0.24,
      w: box.w,
      h: 0.22,
      fontFace: "Microsoft YaHei",
      fontSize: 8.5,
      color: "666666",
      margin: 0,
    });
  }
}

function footer(slide, text) {
  slide.addText(text, {
    x: 0.7,
    y: 7.08,
    w: 12.0,
    h: 0.18,
    fontFace: "Aptos",
    fontSize: 8,
    color: "7A7A7A",
    margin: 0,
    align: "right",
  });
}

function addBg(slide) {
  slide.addImage({ path: bg, x: 0, y: 0, w: 13.333, h: 7.5 });
}

// Slide 1
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: theme.blue };
  addHeader(s, "毕业答辩 · 上海电力大学", "01 / 11", { light: true });
  s.addText("AI POWER IMAGE GENERATION · QUALITY EVALUATION", {
    x: 0.7, y: 0.75, w: 6.5, h: 0.22, fontFace: "Aptos", fontSize: 10, color: "EDEDED", charSpace: 1.4, margin: 0,
  });
  s.addText("基于AI生成电力图像\n及多维度质量评价", {
    x: 0.7, y: 1.2, w: 7.1, h: 1.45, fontFace: "Microsoft YaHei", fontSize: 24, color: theme.white, bold: false, margin: 0,
  });
  s.addText("围绕电力场景图像生成、质量评分与平台闭环验证，构建“可生成、可评价、可追踪”的工程化系统。", {
    x: 0.7, y: 2.85, w: 6.8, h: 0.6, fontFace: "Microsoft YaHei", fontSize: 11, color: "F2F2F2", margin: 0,
  });
  s.addImage({ path: img("images/01-school-logo.png"), x: 9.2, y: 1.45, w: 2.7, h: 2.2, sizing: { type: "contain", x: 9.2, y: 1.45, w: 2.7, h: 2.2 } });
  s.addText("学生：茹文栚    学号：20221533\n学院：人工智能学部    专业：计算机科学与技术\n指导教师：卢芳芳", {
    x: 0.7, y: 5.9, w: 5.3, h: 0.8, fontFace: "Microsoft YaHei", fontSize: 11, color: theme.white, margin: 0,
  });
}

// Slide 2
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: "F7FBFF" };
  addHeader(s, "CONTENTS", "02 / 11");
  s.addShape(pptx.ShapeType.rect, {
    x: 7.0, y: 0, w: 6.33, h: 7.5,
    line: { color: "D7E8F7", pt: 0 },
    fill: { color: "DDEEFF", transparency: 22 },
  });
  s.addShape(pptx.ShapeType.rect, {
    x: 7.0, y: 5.35, w: 6.33, h: 2.15,
    line: { color: "B7D4EE", pt: 0 },
    fill: { color: "BBD8F2", transparency: 30 },
  });
  s.addText("目 录", {
    x: 0.9,
    y: 0.9,
    w: 2.0,
    h: 0.68,
    fontFace: "Microsoft YaHei",
    fontSize: 30,
    color: theme.blue,
    bold: true,
    margin: 0,
  });
  s.addText("CONTENTS", {
    x: 0.92,
    y: 1.7,
    w: 2.6,
    h: 0.24,
    fontFace: "Aptos",
    fontSize: 13,
    color: "4EA1D9",
    charSpace: 6,
    margin: 0,
  });
  s.addShape(pptx.ShapeType.line, {
    x: 0.92, y: 2.05, w: 2.55, h: 0,
    line: { color: "4EA1D9", pt: 2.2, beginArrowType: "none", endArrowType: "triangle" },
  });

  const outline = [
    ["01", "项目背景与研究意义"],
    ["02", "系统总体设计"],
    ["03", "关键技术研究"],
    ["04", "系统实现与功能展示"],
    ["05", "总结与展望"],
  ];
  const ys = [2.65, 3.5, 4.35, 5.2, 6.05];
  outline.forEach((item, i) => {
    s.addShape(pptx.ShapeType.roundRect, {
      x: 0.88, y: ys[i] - 0.02, w: 0.62, h: 0.38,
      rectRadius: 0.05,
      line: { color: theme.blue, pt: 0 },
      fill: { color: theme.blue },
    });
    s.addText(item[0], {
      x: 0.88, y: ys[i] + 0.03, w: 0.62, h: 0.16,
      fontFace: "Aptos",
      fontSize: 11,
      color: theme.white,
      bold: true,
      align: "center",
      margin: 0,
    });
    s.addText(item[1], {
      x: 1.8, y: ys[i] - 0.02, w: 4.2, h: 0.3,
      fontFace: "Microsoft YaHei",
      fontSize: 19,
      color: theme.blue,
      bold: true,
      margin: 0,
    });
    s.addShape(pptx.ShapeType.line, {
      x: 1.82, y: ys[i] + 0.28, w: 4.7, h: 0,
      line: { color: "B8D7EF", pt: 1.1, dash: "dash" },
    });
  });
  s.addText("右侧保留作视觉背景，你可以只改左边目录文字，不会影响其它页面。", {
    x: 7.35, y: 0.92, w: 5.45, h: 0.4,
    fontFace: "Microsoft YaHei",
    fontSize: 11,
    color: "5C6C7A",
    margin: 0,
  });
  s.addText("POWER\nGRID", {
    x: 7.35, y: 1.75, w: 2.5, h: 0.85,
    fontFace: "Aptos",
    fontSize: 20,
    color: theme.blue,
    bold: true,
    margin: 0,
  });
}

// Slide 3
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: theme.paper };
  addHeader(s, "SECTION", "03 / 12");
  s.addText("项目背景与研究意义", {
    x: 0.82, y: 1.05, w: 7.6, h: 1.0, fontFace: "Microsoft YaHei", fontSize: 30, color: theme.blue, bold: true, margin: 0,
  });
  s.addText("Section 01", {
    x: 0.85, y: 2.0, w: 2.0, h: 0.25, fontFace: "Aptos", fontSize: 13, color: "4EA1D9", charSpace: 5, margin: 0,
  });
  s.addShape(pptx.ShapeType.line, {
    x: 0.85, y: 2.35, w: 2.5, h: 0,
    line: { color: "4EA1D9", pt: 2.2, beginArrowType: "none", endArrowType: "triangle" },
  });
  s.addText("这一页作为过渡页，后面进入具体的研究背景、系统设计与实现内容。", {
    x: 0.85, y: 2.8, w: 5.4, h: 0.6, fontFace: "Microsoft YaHei", fontSize: 11, color: theme.text2, margin: 0,
  });
  s.addShape(pptx.ShapeType.rect, {
    x: 7.0, y: 0, w: 6.33, h: 7.5, line: { color: "D7E8F7", pt: 0 }, fill: { color: "DDEEFF", transparency: 22 },
  });
  s.addShape(pptx.ShapeType.rect, {
    x: 7.0, y: 5.35, w: 6.33, h: 2.15, line: { color: "B7D4EE", pt: 0 }, fill: { color: "BBD8F2", transparency: 30 },
  });
  s.addText("电力场景 · AI 生成 · 多维评价", {
    x: 7.35, y: 1.0, w: 4.9, h: 0.5, fontFace: "Microsoft YaHei", fontSize: 18, color: theme.blue, bold: true, margin: 0,
  });
  s.addText("Transition", {
    x: 7.35, y: 1.7, w: 2.0, h: 0.22, fontFace: "Aptos", fontSize: 12, color: "4EA1D9", charSpace: 6, margin: 0,
  });
}

// Slide 3
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: "F7FBFF" };
  addHeader(s, "BACKGROUND", "04 / 12");
  addCard(s, "问题一", "真实电力图像采集成本高，危险工况和极端场景样本难获取，数据长期稀缺且分布不均。", { x: 0.8, y: 1.9, w: 3.9, h: 1.35 });
  addCard(s, "问题二", "通用文生图模型在电力设备结构、标识和导线细节上容易出现语义偏差与物理不合理。", { x: 0.8, y: 3.45, w: 3.9, h: 1.35 });
  addCard(s, "本文工作", "设计生成与评分一体化平台，引入 LoRA 微调、多维评分模型与 YOLO 辅助检测训练，形成可验证闭环。", { x: 0.8, y: 5.0, w: 3.9, h: 1.45 }, true);
  addBulletList(s, [
    "研究目标 1：提升电力场景图像生成的专业适配能力",
    "研究目标 2：建立视觉保真、文本一致、物理合理、构图美学四维评价体系",
    "研究目标 3：在平台侧完成任务提交、结果反馈、历史回溯与审计追踪",
  ], { x: 5.2, y: 2.0, w: 7.2, h: 4.7 }, { fontSize: 12, paraSpaceAfterPt: 14 });
}

// Slide 3
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: theme.paper };
  addHeader(s, "RESEARCH OBJECTIVES", "05 / 12");
  addTitle(s, "MAIN WORK · FOUR PARTS", "论文核心工作与答辩主线");
  addCard(s, "01 数据治理", "围绕输电塔、风机、导线等关键对象持续清洗与重构训练集。", { x: 0.8, y: 2.0, w: 2.9, h: 1.9 });
  addCard(s, "02 生成模型", "基于提示词控制与 LoRA 微调提升电力设备细节和专业构图稳定性。", { x: 3.95, y: 2.0, w: 2.9, h: 1.9 });
  addCard(s, "03 质量评价", "构建四维评分体系，并使用 YOLOv11 辅助检测结果验证行业对象可识别性。", { x: 7.1, y: 2.0, w: 2.9, h: 1.9 }, true);
  addCard(s, "04 平台验证", "基于 Vue3、Go、Python、MySQL、Redis 构建工程化业务闭环。", { x: 10.25, y: 2.0, w: 2.25, h: 1.9 });
  addBulletList(s, [
    "第 3 章：系统需求分析与总体设计",
    "第 4 章：模型训练、优化实现与辅助检测实验",
    "第 5 章：平台实现、应用验证与结果分析",
  ], { x: 0.9, y: 4.45, w: 11.8, h: 1.8 }, { fontSize: 13, paraSpaceAfterPt: 16 });
}

// Slide 4
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: theme.paper };
  addHeader(s, "SYSTEM DESIGN", "06 / 12");
  addTitle(s, "SYSTEM ARCHITECTURE · DATA STORAGE", "系统总体架构与数据存储设计", "前端、Go 微服务、Python AI 运行时、数据库与文件存储共同形成业务闭环。");
  addImageCaption(s, img("images/04-system-architecture.png"), "平台协同架构", "任务管理 / 模型调度 / 结果回写", { x: 0.8, y: 2.25, w: 5.8, h: 3.3 });
  addImageCaption(s, img("images/05-database-er.png"), "数据库与存储结构", "MySQL + Redis + 文件存储联合设计", { x: 6.95, y: 2.25, w: 5.55, h: 3.3 });
}

// Slide 5
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: theme.paper };
  addHeader(s, "MODEL WORKFLOW", "07 / 12");
  addTitle(s, "GENERATION PIPELINE · EVALUATION PIPELINE", "生成模型与评分模型双链路协同");
  addCard(s, "生成链路", "1. 提示词控制\n2. LoRA 微调\n3. 样本治理\n4. 结果持久化", { x: 0.8, y: 2.0, w: 5.8, h: 3.9 });
  addCard(s, "评分链路", "1. 视觉保真\n2. 文本一致\n3. 物理合理\n4. 构图美学", { x: 6.9, y: 2.0, w: 5.6, h: 3.9 }, true);
  footer(s, "两条链路在平台内通过异步任务和审计记录形成闭环");
}

// Slide 6
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: theme.paper };
  addHeader(s, "TRAINING EVOLUTION", "08 / 12");
  addTitle(s, "DATA CLEANING · TRAINING PATH", "清洗版本与训练路径演进");
  const timeline = [
    ["R1 基线", "highquality-v2-pure-yolo-clean-r1", "mAP50 0.69417"],
    ["Wind Boost", "boosted-wind-good1x", "mAP50 0.70363"],
    ["Tower Clean8", "windgood1x-towerclean8", "mAP50 0.71885"],
    ["Hardclean R1-R2", "hardclean-r1 / hardclean-r2", "mAP50 0.70776 / 0.70285"],
    ["Hardclean R3", "hardclean-r3", "mAP50 0.68457"],
  ];
  let x = 0.75;
  timeline.forEach((item, idx) => {
    addCard(s, item[0], `${item[1]}\n${item[2]}`, { x, y: 2.35, w: 2.35, h: 2.2 }, idx === 2);
    if (idx < timeline.length - 1) {
      s.addShape(pptx.ShapeType.line, { x: x + 2.38, y: 3.45, w: 0.35, h: 0, line: { color: theme.border, pt: 1.2, beginArrowType: "none", endArrowType: "triangle" } });
    }
    x += 2.45;
  });
  footer(s, "全局最高训练目录：hqv2_windgood1x_towerclean8_yolo11s_640_ft1");
}

// Slide 7
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: theme.paper };
  addHeader(s, "YOLO ASSISTED DETECTION", "09 / 12");
  addTitle(s, "YOLOv11 TRAINING LOSS CURVE", "辅助检测训练损失曲线");
  addImageCaption(s, img("1.YOLOv11辅助检测训练损失曲线.png"), "YOLOv11 辅助检测训练损失曲线", "基于更新后的 result 全量 epoch 路径重绘", { x: 0.8, y: 2.0, w: 8.2, h: 3.8 });
  addCard(s, "最佳 mAP50", "0.71885\n来自 windgood1x-towerclean8 版本，是当前全局最高成绩。", { x: 9.35, y: 2.05, w: 3.0, h: 1.5 }, true);
  addCard(s, "最佳 mAP50-95", "0.36486\n说明高 IoU 区间仍有提升空间。", { x: 9.35, y: 3.75, w: 3.0, h: 1.2 });
  addCard(s, "实验意义", "检测训练结果辅助验证生成图像中的行业对象可识别性与结构约束能力。", { x: 9.35, y: 5.12, w: 3.0, h: 1.3 });
}

// Slide 8
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: theme.paper };
  addHeader(s, "YOLO RESULT OVERVIEW", "10 / 12");
  addTitle(s, "ALL_RESULTS_SUMMARY.CSV", "按 CSV 汇总的指标与版本对比");
  addImageCaption(s, img("2.YOLOv11辅助检测指标图.png"), "指标图", "Precision / Recall / mAP 收敛表现", { x: 0.75, y: 2.0, w: 3.0, h: 1.75 });
  addImageCaption(s, img("3.YOLOv11辅助检测数据清洗与结果总览图.png"), "清洗与结果总览", "版本演进与训练结果关联", { x: 3.95, y: 2.0, w: 3.0, h: 1.75 });
  addImageCaption(s, img("4.基于all_results_summary的全局训练排名图.png"), "全局训练排名", "按 mAP50 排序", { x: 7.15, y: 2.0, w: 2.55, h: 1.75 });
  addImageCaption(s, img("5.基于all_results_summary的核心清洗版本对比图.png"), "核心清洗版本对比", "重点关注反复迭代的核心版本", { x: 9.95, y: 2.0, w: 2.35, h: 1.75 });
  addCard(s, "关键结论", "windgood1x-towerclean8 达到当前最佳成绩；继续 hardclean 后数据更纯，但整体指标未继续突破。", { x: 0.8, y: 4.35, w: 5.7, h: 1.25 });
  addCard(s, "实验价值", "YOLO 结果把“生成图像像不像电力场景”进一步量化为“关键对象能否被稳定识别”。", { x: 6.75, y: 4.35, w: 5.55, h: 1.25 }, true);
}

// Slide 9
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: theme.paper };
  addHeader(s, "PLATFORM IMPLEMENTATION", "11 / 12");
  addTitle(s, "PLATFORM UI · BUSINESS LOOP", "平台核心页面实现与业务闭环");
  const cards = [
    [img("images/07-dashboard-view.png"), "概览页"],
    [img("images/07-model-center-view.png"), "模型中心"],
    [img("images/07-generate-view.png"), "生成工作台"],
    [img("images/07-history-view.png"), "历史中心"],
    [img("images/07-audit-view.png"), "任务审计"],
  ];
  const positions = [
    { x: 0.75, y: 2.0 }, { x: 3.25, y: 2.0 }, { x: 5.75, y: 2.0 }, { x: 8.25, y: 2.0 }, { x: 10.75, y: 2.0 },
  ];
  cards.forEach((c, i) => addImageCaption(s, c[0], c[1], "", { x: positions[i].x, y: positions[i].y, w: 2.1, h: 1.45 }));
  addCard(s, "工程价值", "前端负责参数交互与结果展示，Go 服务完成治理与鉴权，Python 运行时专注 AI 推理，形成可部署、可追踪、可解释的平台体系。", { x: 0.8, y: 4.45, w: 11.5, h: 1.35 });
}

// Slide 10
{
  const s = pptx.addSlide();
  addBg(s);
  s.background = { color: theme.paper };
  addHeader(s, "CONCLUSION", "12 / 12");
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 4.7, h: 7.5, line: { color: theme.blue, pt: 0 }, fill: { color: theme.blue } });
  s.addText("让电力图像生成\n从可用走向可验证", {
    x: 0.55, y: 1.4, w: 3.6, h: 1.25, fontFace: "Microsoft YaHei", fontSize: 24, color: theme.white, margin: 0,
  });
  s.addText("本文以生成模型、评分模型和平台工程三部分协同，完成了面向电力场景的 AIGC 应用探索。", {
    x: 0.55, y: 3.0, w: 3.45, h: 0.9, fontFace: "Microsoft YaHei", fontSize: 11, color: theme.white, margin: 0,
  });
  addCard(s, "01 生成能力更贴近行业场景", "通过提示词控制与 LoRA 微调，电力设备细节和专业构图得到更稳定呈现。", { x: 5.25, y: 1.35, w: 6.8, h: 1.25 });
  addCard(s, "02 多维评分让结果更可解释", "不再只看“像不像”，而是把视觉、语义、物理与美学一起纳入评价框架。", { x: 5.25, y: 2.95, w: 6.8, h: 1.25 });
  addCard(s, "03 平台闭环支撑持续优化", "后续可继续扩展更多场景数据、评分器与检测辅助任务，推动电力行业 AIGC 走向更可靠应用。", { x: 5.25, y: 4.55, w: 6.8, h: 1.35 }, true);
  footer(s, "感谢各位老师批评指正");
}

const out = path.join(base, "基于AI生成电力图像及多维度质量评价-可编辑版.pptx");
pptx.writeFile({ fileName: out }).then(() => {
  console.log(out);
}).catch((err) => {
  console.error(err);
  process.exit(1);
});
