# 源码发布与维护

本项目使用独立 Git 仓库管理接口源码、中文说明、公开来源目录、示例和离线测试。研究数据库、气象原始数据、下载输出、账号凭据及本地运行环境不属于发布内容。

维护时从本项目目录执行 Git 操作，不要在上层研究目录初始化或整体上传资料。提交前检查：

```sh
git status --short
git diff --cached --stat
python -m unittest discover -s tests
```

使用具体文件路径暂存改动，并检查暂存内容。新适配器须区分目录登记、离线测试与真实下载验收。当前 GEE 客户端只标注离线测试通过；CDS API 和 ARCO 适配器尚未实现。

GitHub Actions 在推送或拉取请求时运行离线合成测试，无需云端密钥。准备阶段的本地验证快照见 [validation.json](validation.json)，最新 CI 结果以仓库 Actions 页面为准。

MIT 许可证适用于项目代码，源数据和依赖继续适用其各自条款。
