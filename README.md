# 解析几何小题笔记仓库（analytic-geometry-problems）

本仓库按知识架构将手写《解析几何小题》原稿拆分为 **Markdown + 高清裁剪图**，支持在 GitHub 上直接按模块翻阅，也支持随时一键按 `outline.yaml` 顺序自动化合并排版为完整 PDF。

## 当前已收录模块
- `01_直线与方程/`（16 个知识点，含 P2、P3、P5、P40–P46 原稿裁剪图）
- `02_圆与方程/`（11 个知识点，含 P4、P6–P8、P46、P51 原稿裁剪图）

## 一键合并排版为大 PDF

### 方法一：本地运行（一条命令）
```bash
pip install -r requirements.txt
python3 build_pdf.py
```
默认输出到 `output/解析几何小题合集.pdf`。

如需只合并指定模块（例如只导出模块一）：
```bash
python3 build_pdf.py --modules 01 -o output/01_直线与方程.pdf
```

### 方法二：GitHub Actions 云端自动合成
本仓库已内置 `.github/workflows/build-pdf.yml`。上传到 GitHub 后，每次修改任意 `.md` 或调整 `outline.yaml` 顺序并推送（或在仓库 **Actions** 页面点击 **Run workflow**），GitHub 会自动运行脚本并生成最新 PDF 供下载。

## 如何调整大纲顺序或补充内容
- **调整合并顺序**：直接编辑 `outline.yaml` 中的模块或条目顺序即可，无需改动图片文件。
- **添加纠错或心得**：直接打开对应知识点的 `.md` 文件，在图片上方新增一行文字即可，合并脚本会自动把它渲染成高亮备注框。
