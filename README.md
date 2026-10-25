# Weichen Lyu's personal website

Jekyll website with an academic homepage, photography albums, and a blog.

## 本地预览

在终端进入这个目录，运行：

```sh
./preview.command
```

第一次运行会把 Jekyll 依赖安装到本项目的 `vendor/`（已从 Git 和网站输出中排除），并检查 Python/Pillow 图片处理依赖，缺少时自动在 `vendor/tools/image-python` 准备。需要网络、Ruby、Python 3 和 macOS Command Line Tools。后续运行会复用依赖。

默认打开 <http://127.0.0.1:4000/>；如果 4000 已被占用，脚本会自动尝试 4001、4002 等端口，并打印实际预览地址。以终端显示的地址为准，其后加 `/photography/` 或 `/blog/` 可打开摄影集和博客。修改内容后保存，刷新浏览器即可；修改 `_config.yml` 后需要重启。停止服务按 `Ctrl+C`。也可用 `PORT=5000 ./preview.command` 指定优先使用的端口。

也可使用自己安装的兼容 Ruby/Bundler：

```sh
bundle install
bundle exec jekyll serve --host 127.0.0.1 --port 4000
```

不能直接双击源文件 `index.md` 或用普通静态文件服务器预览源代码，必须先经过 Jekyll 构建。

## 发布到 GitHub Pages

仓库已经包含 `.github/workflows/pages.yml`，推送到 `main` 后会构建网站、自动生成封面和相册内的轻量预览图，再发布构建产物。首次启用时，在仓库 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**。以后照常提交、推送即可，不需要提交 `_site/`、生成的图片或本地缓存。Actions 页面中的同名工作流也支持手动运行。

工作流沿用 GitHub 官方 Jekyll 构建，再执行图片优化。仓库按分支直接发布的内置构建不会执行自定义图片处理，因此需要上述一次性设置。当前代码修改不会自动提交或推送。

## 导航

在 `_data/navigation.yml` 修改导航名称和顺序。CV 始终读取 `_config.yml` 中的 `cv_link`，替换该 PDF 文件即可更新简历。主页保留原来的学术内容；Photography 和 Blog 使用独立的宽版布局。

## 添加摄影相册

1. 在 `assets/photos/` 新建相册文件夹，例如 `beijing-autumn`，把照片放进去。建议用长边约 2000–2400 px 的压缩 JPEG/WebP。
2. 复制 `_templates/album.md` 到 `_albums/beijing-autumn.md`，删除 `published: false`，填写以下内容即可：

```yaml
---
title: 北京 · 秋日
cover_description: 秋日街头的片刻。
description: |
  这里写点开相册后展示的详细介绍。

  可以分段记录拍摄背景、地点和故事。
date: 2026-10-24
location: 北京
cover: /assets/photos/beijing-autumn/01.jpg
photos: /assets/photos/beijing-autumn/
---
```

`photos` 直接填写网站内的文件夹路径，无需逐张列出文件，也无需填写 `alt`。支持 JPG/JPEG、PNG、WebP、AVIF 和 GIF，扩展名不区分大小写。只读取该文件夹的直接图片，不递归读取子文件夹。图片按文件名排序（不区分大小写的字典序）；想控制顺序，可命名为 `01.jpg`、`02.jpg`、`03.jpg` 等，数字位数保持一致。

以后向该文件夹添加、移除或重命名图片，Jekyll 重新构建后会自动更新相册、照片数量和顺序，本地预览保存后刷新即可。无需运行生成照片列表的脚本。路径中的空格、中文会自动处理。

`date` 是创建时间，决定普通相册排序；`location` 是拍摄地点。相册自动出现在 `/photography/`，对应详情页为 `/photography/beijing-autumn/`。标题、地点和介绍都支持中文；注意 YAML 字段的英文冒号后必须留一个空格，例如 `title: 日本`。

日期支持只写年月，例如 `date: 2026-08`；页面显示“2026-08”，排序时按该月 1 日计算。完整日期 `date: 2026-08-15` 也可使用，页面按原精度显示。同样支持 `last_modified_at: 2026-10`。没有日期的普通相册排在最后。相册仍编辑 `_albums/*.md`，访问地址保持不变；通过普通 Jekyll 页面读取，无需额外插件，兼容 GitHub Pages。

`cover` 直接填写相册图片路径，例如 `cover: /assets/photos/beijing-autumn/01.jpg`，不需要另做封面图片；不填时自动使用文件名排序后的第一张。`cover_position: "50% 30%"` 可以调整方形封面的裁切位置，默认居中。

`cover_description` 只用于封面悬停时展示的短句，最多显示两行；`description` 只用于点开相册后的详细介绍，不截断，使用 `|` 可保留换行和分段。两个字段各自独立，都可以省略，不会互相替代。最后一个 `---` 后还可写支持 Markdown 的正文，用于更长的拍摄记录。

### 图片展示和 EXIF

`cover` 始终填写相册原图路径。每次预览或发布，系统自动为封面生成 480 / 960 像素宽的 WebP，浏览器按屏幕大小选取；图片尺寸较小时不放大。原图替换后自动更新生成地址，未改变时复用缓存。封面的 `cover_position` 设置继续有效。

相册内的照片也会自动生成 480 / 960 / 1600 / 2400 像素宽的 WebP（小图不放大）。瀑布流、等高分行和宽幅大图会根据照片实际展示宽度选择尺寸，原始构图、比例和水印保持。点开后才加载原图，并从原图读取 EXIF。

封面预览写入 `_site/assets/generated/covers/`，相册预览写入 `_site/assets/generated/photos/`，本地复用缓存位于 `.cover-cache/`，全部不提交到 Git。不匹配旧 `thumbs/` 或读取 `thumb` 字段，你不需要额外运行图片生成命令。首次构建会生成所有预览图，后续构建复用缓存；GitHub Actions 也会保存缓存，缓存可用时只补充新增或变化的图片。旧的子文件夹不会被计入相册。

相册介绍右下角有两个布局按钮：左侧为“宽幅大图 + 等高分行”，右侧为原来的三列瀑布流。默认保持瀑布流，浏览器会记住后续选择，并应用到其他相册。新模式中，宽高比达到 1.9 的照片独占一行，16:9 左右的照片最多两张并排，其他照片自动分为等高的行。为保持前部紧凑，普通横图、竖图会从后面借用合适的照片拼满当前行，普通横图优先与 4:3 / 3:2 横图配对；只有最后剩余的单张允许不铺满。照片不裁切，点开大图后按屏幕展示顺序翻页。切回瀑布流或在手机单列中展示时恢复文件名顺序，无需修改相册配置。

如果第一张是竖构图，并且相册后面有至少两张普通横图，新模式会以“左侧竖图 + 右侧上下两张横图”开场，保留竖图的高度感，三张照片原比例组成完整矩形。手机上继续使用单列。

放大照片后自动读取图片自带的 EXIF，不显示描述文字。新上传或重命名照片无需另外生成参数表，只要图片保留 EXIF 即可。已有参数表作为快速缓存继续使用，单张照片手动填写的 `exif` 优先。不同照片的参数异步读取时不会串到另一张照片上。

如果希望预先提取参数，仍可使用以下可选命令（需要 Python 和 Pillow）：

```sh
python3 scripts/extract-photo-exif.py /path/to/originals --prefix /assets/photos/beijing-autumn/
```

原片和网页图片应同名；脚本优先匹配实际文件名及大小写，也兼容原片 `DSC_0900.JPG` 对应网页图片 `DSC_0900.jpg`。它只将显示用的六项参数写入 `_data/photo_exif.json`，不会复制或压缩图片，也不会修改原片。如果图片本身已清除 EXIF，而且没有缓存或手填参数，参数面板会隐藏；需从原片恢复参数。

### 独立精选集

`_albums/selected.md` 已使用 `photos: /assets/photos/selected/`。直接向这个目录放入照片即可，顺序同样按文件名排列。封面继续由 `cover` 指定相册图片。

精选集通过 `pinned: true` 置顶，显示 `last_modified_at` 作为最后更新时间。更新照片时同步修改这个日期；普通相册的 `date` 保留创建时间。

### 摄影水印与版权

添加照片后，在项目目录运行以下命令，将 `@mattlyu` 小水印写入照片左下角。水印使用白色实心字、深色细描边和轻微阴影，在明暗交错、纹理复杂的背景上也能保持可读：

```sh
python3 scripts/watermark-photos.py
```

只处理一本相册时，例如精选集，可使用 `python3 scripts/watermark-photos.py assets/photos/selected`。水印脚本保留分辨率、EXIF、XMP 和颜色配置，不创建原图副本。`_data/photo_watermarks.json` 记录文件校验值、字体校验值和水印版本，重复运行会跳过已处理的照片，避免水印叠加。支持用 `--font /path/to/font.ttf` 指定字体，用 `--dry-run` 只检查、不写图片。

从旧版灰色或自适应黑灰水印升级时运行 `python3 scripts/watermark-photos.py --upgrade-existing`。脚本先核对全部文件和旧字体，再按原有字形、颜色与透明度替换合成结果；新水印必须至少与旧水印同样不透明，避免放大旧 JPEG 的压缩误差。不会直接在旧字上重复叠盖，也不生成无水印副本。照片以 JPEG 95 质量保存，已有压缩误差无法完全逆转。修改文字、位置或使用其他不兼容样式时应从自己的无水印原片重新处理；已处理文件若被其他软件改动，脚本会停止，防止误盖第二层水印。

摄影首页及各相册底部显示摄影作品版权声明。`assets/photos/` 中的照片、封面和缩略图不适用模板代码的 CC0 许可，其使用说明见 [摄影作品版权声明](assets/photos/LICENSE.txt)。第三方程序库保留各自的许可。

### 可选：手动指定顺序或说明

旧的照片列表格式仍然可用。只有需要自定义顺序、为某张照片设置说明或手填 EXIF 时，才需使用：

```yaml
photos:
  - src: /assets/photos/beijing-autumn/02.jpg
  - src: /assets/photos/beijing-autumn/01.jpg
    caption: 可选说明
```

`alt`、`width`、`height` 和 `exif` 都可选。`width`、`height` 同时填写时应为相册图片实际尺寸；未填写时使用已有水印记录中的尺寸，或由浏览器读取图片比例。放大查看支持左右方向键、手机横向轻扫和 Esc 关闭。

## 添加博客

复制 `_templates/post.md` 到 `_posts/YYYY-MM-DD-article-slug.md`，删除 `published: false`，填写标题、时间、摘要和 Markdown 正文。首次使用时可创建：

```text
_posts/2026-10-24-my-first-post.md
```

`description` 显示在列表中；不填时使用文章首段。`categories` 和 `tags` 可不填。文章在 `/blog/` 按发布时间倒序显示，独立地址如 `/blog/2026/10/24/my-first-post/`。

列表采用标题下方左侧封面、右侧摘要与“阅读全文”的样式，不显示作者行；手机端改为上下排列。用 `cover` 指定本地封面图片（建议 760×420 px），`cover_alt` 填图片说明；不填封面时只显示文字。摘要最多显示三行。

需要数学公式时，在文章头部加 `math: true`。行内公式写作 `$$e^{At}$$`，独立公式把 `$$` 分别放在公式前后单独一行；可用 `\tag{1}` 编号。公式使用本地 KaTeX 0.16.22 渲染，不依赖外部 CDN；长公式可横向滚动。`source_url` 可选，用于在文章末尾保留原文链接。

使用 `last_modified_at` 标记更新时间不会改变列表排序。保留 `published: false` 可以保存未发布文章；未来日期的文章默认不会提前显示。

标题包含公式时，保留纯文字 `title` 用于浏览器标签页，另加 `math_title` 用于文章页和 Blog 列表中的数学排版，例如：

```yaml
math: true
title: 矩阵指数 e^At
math_title: '矩阵指数 \(e^{At}\)'
```

`math_title` 中使用 `\(...\)` 表示行内公式，并用 YAML 单引号保留反斜杠；不填写时继续显示普通标题。

标题和正文都可以用中文，建议 URL 文件名使用简短英文或拼音。正文中的本地图片建议用 `relative_url`：

```liquid
![图片说明]({{ '/assets/photos/album/01.jpg' | relative_url }})
```

## 构建检查

```sh
bundle exec jekyll build
git diff --check
```

`_site/` 是生成结果，不提交。模板、预览脚本和本地依赖均不输出为网站页面。
