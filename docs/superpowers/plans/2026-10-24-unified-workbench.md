# 统一气候工作台 Implementation Plan

> **For agentic workers:** Use subagent-driven-development for bounded implementation and independent reviews. Execute within the existing dedicated public repository on the feature branch; no additional worktree is necessary. Follow test-driven-development and verification-before-completion.

**Goal:** 将 44 项目录与三个明确获取路线组织成个人可用的中文本地工作台。

**Architecture:** 目录/请求/来源/传输/持久化各自独立；界面调用与命令行相同的服务函数。现有区域 ERA5 工具保持兼容。无需数据库写入或云端服务。

**Tech Stack:** Python 3.11+、标准库 HTTP/CSV/JSON、既有 numpy/xarray/h5netcdf、原 GEE 可选 SDK。

## Task 1：统一服务层

Files: create `src/climate_access/catalogue.py`, `requests.py`, `providers.py`, `transport.py`, `service.py`, `tests/test_service.py`, `src/climate_access/resources/sources.json`.

- [ ] 先写并运行失败测试：请求边界/日界、目录44项、原生变量名、禁止未知字段、源固定、缺测计数、时间完整、错误响应及篡改核验。
- [ ] 实现离线 `plan_request(obj)`；输出源、频率、空间、变量、预计行数、认证要求和限制。严格拒绝隐式跨来源回退。
- [ ] 实现 `fetch_request(obj, directory, *, project=None, transport=None)`；前两个点位路线保存有界原始响应、CSV和可回读清单；ERA5委托现有获取工具。HTTP transport 可注入用于合成响应测试。
- [ ] 实现 `verify_request(directory)`；核验请求、源身份、原始字节 SHA、CSV时间/变量/单位及缺测；ERA5调用既有核验。已有路径拒绝覆盖。
- [ ] Run: `python -m unittest discover -s tests -v`；确认原18项和新增测试均通过。实现人自查后进行独立规格审查和质量审查。

## Task 2：中文本地工作台与命令行

Files: modify `src/climate_access/cli.py`; create `src/climate_access/web.py`, `src/climate_access/web/index.html`, `tests/test_web.py`, `examples/power_daily.json`, `examples/open_meteo_hourly.json`, `examples/era5_unified.json`.

- [ ] 先写失败测试：离线计划不发网、目录检索、Host/Origin与会话校验、未知路径/来源、任务历史以及预算/日期错误返回。
- [ ] 新 CLI 命令 catalog/request-plan/request-fetch/request-verify/serve，旧命令保持不变。所有普通错误输出结构化结果并非零退出。
- [ ] 仅在 `127.0.0.1` 启动本地 HTTP 服务。固定输出根，随机会话标识，有限请求体，不接受任意 URL/文件路径。页面不展示实现内部配置细节，只提供用户所需的账号/来源条件。
- [ ] 页面用中文显示目录、获取表单、计划确认、结果及历史。ERA5默认优先；先计划再执行；可复制或下载请求JSON供以后复用。
- [ ] Run offline tests；浏览器实测检索NASA、切换来源、生成计划、错误提示与移动窄屏。

## Task 3：文档、打包和发布

Files: modify `pyproject.toml`, `src/climate_access/__init__.py`, `README.md`, `README.zh-CN.md`, `README.en.md`, `docs/status.md`, `THIRD_PARTY.md`; create `docs/architecture.md`, `docs/extending.md`, `docs/ecosystem.md`, `docs/workbench-validation.json`, root Windows launcher in public repo.

- [ ] 版本0.2.0；setuptools package-data包含目录JSON与HTML；README提供安装、启动、三份请求及输出解释。
- [ ] 记录五个开源工具的官方资料、适用边界和分阶段接入；明确真正实现数量和目录数量。
- [ ] NASA POWER和Open-Meteo各执行一个有界真实历史请求，保存原始响应与核验在忽略的本地数据目录；公开摘要仅写通用点位、日期、行数、源和校验状态。
- [ ] 从wheel隔离安装后离开仓库运行CLI与目录加载；证明数据资源随包发布。
- [ ] 独立最终审查；运行全部离线测试、git diff --check、敏感信息和意外数据检查。
- [ ] 在既有用户授权的GitHub项目发布并验证远端提交与CI。公共代码不含研究数据库、用户查询历史或凭据。

Run commands use the workspace Python build environment and set TEMP/TMP inside the workspace on this Windows host. User has already approved building this workflow; continue through all three tasks and report the concrete working result.
