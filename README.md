# 气候数据收集接口 · climate-data-access

这是一个用于规划及按需获取区域 ERA5 逐小时数据的 Python 接口。当前实现使用 Google Earth Engine 官方 SDK，输出压缩 NetCDF 批次及来源、请求和文件校验清单。

当前为 0.1.0 初期版本。新封装客户端仅使用合成数组做离线测试，本轮没有重新执行云端下载。项目不包含气象原始数据、账号凭据或私人研究数据库。[验证状态](docs/status.md)明确区分历史方法测试与新客户端验证。

[English](README.en.md) · [方法与变量](docs/methods.md) · [验证状态](docs/status.md) · [42 项气候数据目录](catalog/sources.json)

## 安装与离线规划

需要 Python 3.11 或更高版本。建议创建并按所在 shell 的方法激活虚拟环境：

```sh
python -m venv .venv
python -m pip install -e .
climate-access plan examples/two_hours.json
```

`plan` 检查配置并计算格点、小时数、批次数及未压缩数值输出大小估算。规划和导入包均不会自动认证或请求云端。

## 按需下载、核验与打包

先自行按官方[认证说明](https://developers.google.com/earth-engine/guides/auth)配置自己的账号和有权限使用的 Cloud 项目。需要登录时，由你自行运行 `earthengine authenticate`。本工具通过 `ee.Initialize(project=...)` 使用现有 SDK 凭据，不自动弹出认证流程。

```sh
python -m pip install -e ".[gee]"
climate-access fetch examples/two_hours.json --project YOUR_PROJECT_ID --output data/two-hours
climate-access verify data/two-hours
climate-access bundle data/two-hours --output exports/two-hours.zip
```

只有 `fetch` 会请求外部服务，并使用所指定项目的权限与配额。使用前核对当前服务资格及数据条款；离线规划通过不表示账号、数据可用性或下载已验证。

使用相同配置和输出目录可以继续未完成任务；已有批次先核验再复用。配置变化或已有输出损坏会被拒绝。不同请求使用新目录。ZIP 打包前会核验，且不会覆盖已有归档。

异常终止可能留下 `.run.lock`。确认没有其他进程正在写入后，再检查和处理该锁文件。若 NetCDF 已发布但清单尚未提交，续跑会拒绝覆盖这个未登记文件；保留该目录供检查，改用新目录，不要通过删除已核验结果强行重试。容量限额也属于请求身份，修改限额需要新目录。

## 配置与口径

示例配置见 `examples/two_hours.json`，完整约定见[方法说明](docs/methods.md)。

| 字段 | 含义 |
| --- | --- |
| `start`、`end` | 整点 UTC，必须以 `Z` 结尾；开始包含、结束不包含；单次最多 744 个连续小时 |
| `area` | 数组 `[north, west, south, east]`，表示包含的 0.25° 格点中心；不支持跨日期变更线 |
| `variables` | `u10 v10 d2m t2m sp tp ssrdc ssrd tcc` 中的变量子集 |
| `batch_hours` | 每批小时数；示例为 6，上限 24；每批按 float64 估算的未压缩数值量不超过 32 MiB |
| `max_output_mib` | 实际输出文件及清单的运行时容量上限；示例为 128 MiB，不是进程内存、全局缓存或服务配额上限 |

保留来源单位与时间含义，不自动转摄氏度、毫米或 W/m²，不做物理裁剪、插值补缺或当地日聚合。降水及辐射的累计区间必须结合上游文档解释。不同渠道不保证逐值一致，也不会自动替换渠道。

所有请求时刻必须能用 NetCDF 纳秒时间编码表示，最晚为 `2262-04-11T23:00:00Z`；这只是编码边界，不表示 ERA5 已有未来数据。

## 42 项目录与历史验证

[公开目录](catalog/sources.json)仅保留产品名称、指标、覆盖、频率、性质和公开入口等产品字段；状态单独列在 `status_by_id`。目录包含来源、分发渠道及工具，并不表示实现了 42 个连接器。

- Earth Engine：当前仅实现 `ECMWF/ERA5/HOURLY`，新客户端为离线测试状态。
- ARCO：只有历史小样本实验，未实现生产适配器。
- CDS：历史网页下载样本通过，不代表 CDS API 已实现或验证。
- 其余项：目录登记，不声称账号权限或下载已打通。

前身方法曾完成 2003—2010 年的区域获取：96 个月、70,128 个 UTC 小时、9 个变量、37 × 61 格点。对应原始文件后来已删除，本项目不包含这些文件；历史结果不能当作新客户端已复现的证据。

## 开发与授权

```sh
python -m pip install -e ".[gee,query]"
python -m unittest discover -s tests
```

测试使用临时目录中的合成数组，不是气象观测或再分析数据。可选 Parquet/DuckDB 示例只查询独立本地文件，不连接私人数据库。

```sh
python examples/query_point.py data/two-hours --output exports/north-west-point.parquet
```

该示例选择西北角的一个格点，不计算区域平均值。

项目代码采用 [MIT 许可证](LICENSE)；数据继续适用各自上游条款及署名要求。参见[第三方说明](THIRD_PARTY.md)与[安全说明](SECURITY.md)。
