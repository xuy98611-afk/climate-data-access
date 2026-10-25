# 统一个人气候工作台的架构

v0.2 用同一套请求规划、获取和核验服务支持命令行与本地中文页面。目录用于发现来源；可执行路线单独声明。用户始终明确选择来源，不因失败自动改用另一产品或分发渠道。

## 数据流与模块

~~~mermaid
flowchart LR
  JSON[请求 JSON / 中文表单] --> PLAN[requests.plan_request 离线规划]
  PLAN --> SERVICE[service.fetch_request 显式获取]
  SERVICE --> GEE[gee + artifacts / ERA5 NetCDF]
  SERVICE --> POINT[providers + transport / 点位 HTTP]
  GEE --> OUTPUT[本地结果与清单]
  POINT --> OUTPUT
  OUTPUT --> VERIFY[service.verify_request 核验]
  CATALOG[随包44项目录] --> SEARCH[catalogue.search_sources]
  SEARCH --> UI[命令行 / 中文页面]
~~~

| 模块 | 责任 |
| --- | --- |
| requests.py | route_capabilities 声明三条路线；plan_request 校验、规范化请求并返回离线计划；timestamps 生成结束不包含的时间轴 |
| providers.py | 生成固定上游 URL，严格解析原始点位 JSON，检查时间/变量/单位并生成 CSV、缺失计数与来源元数据 |
| transport.py | 有上限的 HTTPS 读取；点位请求超时与端点边界 |
| service.py | fetch_request 选择显式路线、写入结果；verify_request 从文件回读核验 |
| config.py / gee.py / artifacts.py | 保留原有 ERA5 网格、官方 SDK、分批 NetCDF、续跑、核验和打包逻辑 |
| catalogue.py / resources | 检索随包发布的公开来源目录，支持关键词及账号条件筛选 |
| cli.py | 同一服务的命令行入口及原有 ERA5 命令 |
| web.py / web/index.html | 本机 HTTP 服务、先计划后获取、单任务执行、历史记录与中文交互 |

这是一套显式注册在代码中的小型架构，目前没有动态插件发现或通用插件注册表。新增适配器需要同步请求、执行、能力声明、界面和测试，见[扩展约定](extending.md)。

## 请求身份与输出

所有区间使用 [start, end)，逐小时为整点 UTC，逐日使用 UTC 日期。来源、频率、位置、变量和输出预算共同确定规范化请求；预算不是进程内存或服务配额保证。

点位输出目录包含：

~~~text
raw.json              原始上游响应字节
data.csv              请求时段内的时间与变量列
manifest.json         状态、请求哈希、文件 SHA-256、单位、来源与缺失计数
workbench-job.json    仅工作台任务附加的运行记录
~~~

点位上游接口按完整日获取；即使只选两小时，原始响应仍保留全天，CSV 只保留选定时段。成功清单最后写入。缺失清单或未完成状态不能作为成功成果，失败任务不会标记完成。统一获取始终要求新的输出目录，避免覆盖；原有 ERA5 fetch 仍可按原规则核验后续跑。

ERA5 走独立的压缩 NetCDF 批次和 schema 1 清单；点位使用 schema 2。统一核验分派到对应实现，不把点位 CSV 强行解释为区域网格，也不把 NetCDF 声称为原始 HTTP 响应存档。ERA5 详细变量、单位及累计口径见[方法说明](methods.md)。

## 来源语义

| 路线 | 保留与检查的约定 |
| --- | --- |
| ERA5 / GEE | ECMWF/ERA5/HOURLY；原生 0.25° 格点中心，9 变量子集；严格有限值，缺失拒绝，不补值 |
| NASA POWER | 单点日/小时，UTC；原始头部和变量定义随 raw.json 保存；清单记上游来源、单位、返回位置与缺失数；真实变量格点中心未知 |
| Open-Meteo | 固定 models=era5、cell_selection=nearest、elevation=nan、timezone=UTC、wind_speed_unit=ms；保存返回格点坐标 |

来源数值和单位保持原样，不自动转摄氏度、毫米或辐射率。null 与 POWER -999 在点位 CSV 中为空，按变量计数。不同来源之间的对应关系不能据变量中文名称推定，任何下游转换都应另行记录。

## 本地服务与权限边界

服务只绑定 127.0.0.1；检查 Host/Origin，修改请求要求当前页面的会话令牌。令牌是进程内的本地防护，不是数据服务账号凭据。一次只执行一个获取任务；页面计划绑定具体参数，有效期 30 分钟，改参后须重新规划。重启时未完成任务记录显示中断。

项目只使用本机已有 GEE SDK 认证和用户指定的合资格项目，不收集账号密码或令牌，不把项目 ID 写入结果。目录查询和规划不触发认证或外部数据请求。导入 JSON 只是本机读取请求参数，不上传私人文件。

点位传输只访问固定提供者 HTTPS 端点，60 秒超时，单响应最多 64 MiB，并检查原始响应、CSV 和清单的总体预算。没有自动重试或换源；ERA5 保留原有有限重试机制。浏览器单文件下载上限为 32 MiB，较大结果从本地目录使用。

本项目不连接私人研究数据库，不写正式数据库，不自启定时下载，也不托管公网服务。

## 核验的含义

点位核验回读 SHA-256，重新解析 raw.json，并逐字节对照应生成的 CSV，同时检查时间轴、变量、单位、缺失数和来源元数据。ERA5 核验保持其原有批次与网格检查。它们用于检查一致性与可追溯性，不构成独立科学精度检验、发布者签名或不同渠道逐值相同的证明。
