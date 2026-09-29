# photo-to-ppt

将实拍讲座幻灯片保真还原为图片式 PowerPoint 的 Codex skill。

支持逐页四点透视校正、保守清晰度增强、基于同页真实照片的遮挡修补，以及按页码反馈调整裁剪。不会将幻灯片重建为可编辑文字，也不会猜测被遮挡的内容。

## 安装

下载本仓库，将包含 `SKILL.md` 的整个目录命名为 `photo-to-ppt`，放到个人 Codex 技能目录 `~/.codex/skills/` 中。下一轮对话即可调用。

## 使用

在 Codex 中指定技能和照片目录，例如：

> 请使用 $photo-to-ppt，将指定文件夹中的讲座照片还原为 PPT，保留全部照片，每张对应一页。

生成 PPTX 时需要当前环境提供 Presentations 技能；生成 PDF 时需要 PDF 技能。图片处理辅助脚本依赖 Pillow 和 NumPy，优先使用环境已有依赖。

```bash
python scripts/rectify.py inventory /path/to/photos --output /path/to/work/inventory.json
python scripts/rectify.py rectify /path/to/photo.jpg --config /path/to/page.json --output /path/to/work/page-01.png
```

四角必须逐张查看照片后确定。脚本不自动识别屏幕边界，不自动移除人影。配置说明见 [geometry.md](references/geometry.md)，遮挡处理边界见 [occlusion.md](references/occlusion.md)。

## 文件

- `SKILL.md`：工作流程与质量要求
- `agents/openai.yaml`：技能展示信息
- `references/`：几何校正、遮挡修补和复核说明
- `scripts/rectify.py`：照片清单与四点透视转换工具

本仓库仅包含技能及辅助脚本，不包含讲座照片、演示文稿或个人工作目录。
