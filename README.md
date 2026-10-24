# Weichen Lyu's personal website

Jekyll website with an academic homepage, photography albums, and a blog.

## 本地预览

在终端进入这个目录，运行：

```sh
./preview.command
```

第一次运行会把 Jekyll 依赖安装到本项目的 `vendor/`（已从 Git 和网站输出中排除），不会修改网站线上内容。需要网络、Ruby 和 macOS Command Line Tools。后续运行会复用依赖。

默认打开 <http://127.0.0.1:4000/>；如果 4000 已被占用，脚本会自动尝试 4001、4002 等端口，并打印实际预览地址。以终端显示的地址为准，其后加 `/photography/` 或 `/blog/` 可打开摄影集和博客。修改内容后保存，刷新浏览器即可；修改 `_config.yml` 后需要重启。停止服务按 `Ctrl+C`。也可用 `PORT=5000 ./preview.command` 指定优先使用的端口。

也可使用自己安装的兼容 Ruby/Bundler：

```sh
bundle install
bundle exec jekyll serve --host 127.0.0.1 --port 4000
```

不能直接双击源文件 `index.md` 或用普通静态文件服务器预览源代码，必须先经过 Jekyll 构建。

## 导航

在 `_data/navigation.yml` 修改导航名称和顺序。CV 始终读取 `_config.yml` 中的 `cv_link`，替换该 PDF 文件即可更新简历。主页保留原来的学术内容；Photography 和 Blog 使用独立的宽版布局。

## 添加摄影相册

1. 在 `assets/photos/` 新建相册文件夹，例如 `beijing-autumn`，把照片放进去。建议用长边约 2000–2400 px 的压缩 JPEG/WebP。
2. 复制 `_templates/album.md` 到 `_albums/beijing-autumn.md`，删除 `published: false`，填写以下内容即可：

```yaml
---
title: 北京 · 秋日
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

`cover` 可指定任意一张封面；不填时自动使用文件名排序后的第一张。`cover_position: "50% 30%"` 可以调整方形封面的裁切位置，默认居中。`description` 和最后一个 `---` 后的正文都是可选介绍。

### 缩略图和 EXIF

如需单独的缩略图，在相册目录下新建 `thumbs/`，放入与展示图**同名**的缩略图，例如 `assets/photos/beijing-autumn/thumbs/01.jpg`。页面会自动匹配，缩略图不会重复计入照片数量；没有缩略图时直接使用展示图。桌面保持三列瀑布流，小屏幕自动减少列数。

也可以在项目目录运行以下命令，一次为整本相册生成缩略图（需要 Python 和 Pillow，当前电脑已安装）：

```sh
python3 scripts/make-thumbnails.py assets/photos/beijing-autumn
```

它会自动创建 `thumbs/`，保持文件名和照片比例，将长边缩到最多 960px（小图不放大），校正相机方向，并保留颜色配置文件。原图不改动；已有缩略图默认跳过，以后加照片再运行同一命令即可。加 `--size 1200` 可调整尺寸，加 `--overwrite` 可重新生成已有缩略图。动画图片会跳过，页面继续使用原图。缩略图的精简文件不用于保存 EXIF，参数从相册目录中的大图读取。

放大照片后自动读取相册大图自带的 EXIF，不显示描述文字。新上传或重命名照片无需另外生成参数表，只要大图保留 EXIF 即可；`thumbs/` 的小图没有 EXIF 不影响显示。已有参数表作为快速缓存继续使用，单张照片手动填写的 `exif` 优先。不同照片的参数异步读取时不会串到另一张照片上。

如果希望预先提取参数，仍可使用以下可选命令（需要 Python 和 Pillow）：

```sh
python3 scripts/extract-photo-exif.py /path/to/originals --prefix /assets/photos/beijing-autumn/
```

原片和网页图片应同名；脚本优先匹配实际文件名及大小写，也兼容原片 `DSC_0900.JPG` 对应网页图片 `DSC_0900.jpg`。它只将显示用的六项参数写入 `_data/photo_exif.json`，不会复制或压缩图片，也不会修改原片。如果图片本身已清除 EXIF，而且没有缓存或手填参数，参数面板会隐藏；需从原片恢复参数。

### 独立精选集

`_albums/selected.md` 已使用 `photos: /assets/photos/selected/`。直接向这个目录放入照片，`thumbs/` 内放可选同名缩略图即可，顺序同样按文件名排列。封面继续由 `cover` 单独指定。

精选集通过 `pinned: true` 置顶，显示 `last_modified_at` 作为最后更新时间。更新照片时同步修改这个日期；普通相册的 `date` 保留创建时间。

### 可选：手动指定顺序或说明

旧的照片列表格式仍然可用。只有需要自定义顺序、为某张照片设置说明或手填 EXIF 时，才需使用：

```yaml
photos:
  - src: /assets/photos/beijing-autumn/02.jpg
  - src: /assets/photos/beijing-autumn/01.jpg
    caption: 可选说明
```

`alt`、`thumb`、`width`、`height` 和 `exif` 都可选。`width`、`height` 同时填写时应为缩略图实际尺寸；未填写时由浏览器读取图片比例。放大查看支持左右方向键、手机横向轻扫和 Esc 关闭。

## 添加博客

复制 `_templates/post.md` 到 `_posts/YYYY-MM-DD-article-slug.md`，删除 `published: false`，填写标题、时间、摘要和 Markdown 正文。首次使用时可创建：

```text
_posts/2026-10-24-my-first-post.md
```

`description` 显示在列表中；不填时使用文章首段。`categories` 和 `tags` 可不填。文章在 `/blog/` 按发布时间倒序显示，独立地址如 `/blog/2026/10/24/my-first-post/`。

列表采用标题下方左侧封面、右侧摘要与“阅读全文”的样式，不显示作者行；手机端改为上下排列。用 `cover` 指定本地封面图片（建议 760×420 px），`cover_alt` 填图片说明；不填封面时只显示文字。摘要最多显示三行。

需要数学公式时，在文章头部加 `math: true`。行内公式写作 `$$e^{At}$$`，独立公式把 `$$` 分别放在公式前后单独一行；可用 `\tag{1}` 编号。公式使用本地 KaTeX 0.16.22 渲染，不依赖外部 CDN；长公式可横向滚动。`source_url` 可选，用于在文章末尾保留原文链接。

使用 `last_modified_at` 标记更新时间不会改变列表排序。保留 `published: false` 可以保存未发布文章；未来日期的文章默认不会提前显示。

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
