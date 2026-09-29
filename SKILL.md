---
name: photo-to-ppt
description: Restore photographed lecture slides to faithful image-based PPTX, with perspective correction, conservative clarity enhancement, evidence-based occlusion repair, and page-by-page crop revisions. Use for 讲座照片转PPT、拍屏幻灯片还原、去人头遮挡、根据页号点评修正裁剪. Not for generating new slide content or reconstructing editable text from papers.
---

# 讲座照片还原 PPT

把实拍照片中有证据的原始幻灯片内容还原到端正、清晰的图片式 PPT。优先保住标题、结论、图注和页码；去人影不能以猜字、重画照片或伪造图表为代价。

## 接手任务

- 读取指定照片、基准 PPT 和本轮点评。页号默认指基准 PPT 页序，不能用原幻灯片印刷页码替代。固定 `PPT页 → 来源照片 → 处理参数 → 问题` 映射。
- 用户认可的页锁定图片和布局；未要求修改的页沿用基准。新版本另存，保留可回退中间图。
- 新建时默认保留全部照片，每张对应一页；用户要求合并时才按内容合并。文件名含 `(1)` 不是重复证据。不能混拼互相替换的展示状态。
- 按用户要求选择样张、仅中间图片、全套处理或逐页修订。要求暂停在图片阶段就不组装 PPT；已授权全套时不额外设置审批关卡。

## 处理流程

1. **先核对原图，再定边界。** 总览用于找同页照片和异常页；逐张查看原始分辨率。每张照片独立确定四角，不套用统一裁剪框。标题下划线、正文矩形和结论条不是屏幕边缘。
2. **校正和裁剪分开。** “扩左侧”要回原图找回真实像素，不能放大旧裁剪图。宽高比依据基准/实拍证据，不能统一硬拉成16:9。边界不确定时保留少量余量。“先不裁剪”用包含原照片全部四角的扩展画布校正，画外留白，等比例插入。见 [geometry.md](references/geometry.md)。
3. **适度增强。** 从最高分辨率原图处理曝光、色偏、噪声和锐度，避免反复有损编码。检查细字、浅色线、数字和公式，不能因提亮丢失。生成的锐利笔画不是真实文字证据。脚本默认不改颜色，增强参数按当前照片决定。
4. **逐区域判断遮挡。** 同页实拍才可配准补回正文/图表/照片；确认只有连续背景才局部修补。共同遮挡、倒计时下方标识不明或画外内容，保留问题。操作前读 [occlusion.md](references/occlusion.md)。不能用整页生成式重绘来去人影。
5. **先审图，再封装。** 每页一张高质量图完整放置，保持比例，禁止 `cover` 二次裁剪。不增加正文说明或改写内容。备注记录来源和实际完成/未完成事项。PPTX 实现读取当前可用 Presentations skill；PDF 输出读取当前 PDF skill，运行时路径从环境发现，不硬编码机器路径。
6. **逐页复核导出结果。** 总览不能替代每页完整渲染和修补处放大图。核对标题、结论、图注、页码与原图；检查倾斜、误补、头发弧线和接缝。锁定页校验嵌入图片哈希和布局。核对页数、来源覆盖及空页。交付 PPTX、用户要求的预览/中间图和简短问题清单。

## 工具与经验

当前环境允许非生成性脚本处理时，可用 `scripts/rectify.py`：

```bash
python scripts/rectify.py inventory /path/to/photos --output /path/to/work/inventory.json
python scripts/rectify.py rectify /path/to/photo.jpg --config /path/to/page.json --output /path/to/work/page-01.png
```

依赖 Pillow、NumPy，优先使用环境提供的运行时。脚本只执行已由视觉确认的四点透视转换、可选轻微增强及来源记录；不自动决定页序/边界，不猜遮挡。配置见 [geometry.md](references/geometry.md)。不要照搬过去项目坐标、增益或尺寸。

按 [review-and-lessons.md](references/review-and-lessons.md) 复核并记录经验。区分真实实拍补回、背景估计、尚无证据恢复。实际有人影或接缝不能标“无问题”。用户认可某版代表它满足当次用途，不代表算法可自动无损还原任何照片。
