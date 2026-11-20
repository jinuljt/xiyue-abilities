# 喜悦 · 能力库

四个声明式样例、结构规范及 Python 标准库离线校验/文字预览。

```sh
python3 check.py
python3 -m unittest -v
python3 check.py capabilities/tea-guide.json --preview
```

完整使用方式、版本/启用/权限边界见 [README.html](README.html)（下载后可在浏览器打开）。

当前支持 `say`、`confirm`、`timer` 声明；实际运行依赖兼容的喜悦 Agent。离线预览不会联网、播放声音或写任务状态。网络工具、任意代码和真机播报不在本仓库的已验证能力内。
