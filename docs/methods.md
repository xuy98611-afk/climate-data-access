# 请求口径与输出方法

## 来源与传输

适配器从 [`ECMWF/ERA5/HOURLY`](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_HOURLY) 选取影像，通过官方 Earth Engine SDK 的 [`ee.data.computePixels`](https://developers.google.com/earth-engine/apidocs/ee-data-computepixels) 发起限定范围的数值请求，不自动替换分发渠道。

各使用者按[官方 SDK 流程](https://developers.google.com/earth-engine/guides/auth)独立配置认证。只有显式执行 `fetch` 才通过所指定 Cloud 项目及已有凭据初始化 Earth Engine；规划及导入模块保持离线。

## 时间与网格

请求使用以 `Z` 结尾的整点 UTC，单次最多 744 个连续小时。区间为 `[start, end)`：午夜开始的两小时请求包含 00:00 和 01:00。输出保持 UTC，不做当地日聚合或夏令时转换。

区域接口采用该集合的 0.25° 经纬度网格。`area` 为 `[north, west, south, east]`，边界表示包含的格点中心，必须准确落在网格上。纬度由北向南递减，经度由西向东递增。服务端请求使用格点边缘偏移，使像元中心与输出坐标对齐。不支持跨日期变更线、插值或网格降采样。

这一约定描述分发数据的规则经纬度网格，不表示大气模式底层网格或有效分辨率就是 0.25° 正方形。

## 支持变量

| 简称 | Earth Engine 波段 | 来源单位 |
| --- | --- | --- |
| `u10` | `u_component_of_wind_10m` | m/s |
| `v10` | `v_component_of_wind_10m` | m/s |
| `d2m` | `dewpoint_temperature_2m` | K |
| `t2m` | `temperature_2m` | K |
| `sp` | `surface_pressure` | Pa |
| `tp` | `total_precipitation` | m |
| `ssrdc` | `surface_solar_radiation_downward_clear_sky` | J/m² |
| `ssrd` | `surface_solar_radiation_downwards` | J/m² |
| `tcc` | `total_cloud_cover` | 比例 |

客户端保留所选波段的来源值，并在元数据中记录单位，不自动换算摄氏度、毫米或 W/m²。组合小时或计算速率前，须核对上游波段定义及累计区间；单独一个时间戳不能定义累计窗口。本工具不做去累计、取整、格点平均或其他逐小时增量波段派生，也不静默混用来源。

要求响应值有限。超出预期物理范围的值不会自动裁剪或纠正；有限值检查属于完整性检查，不证明气象准确性。掩膜或格式异常的响应会被拒绝，不自动补值。

## 分批、完整性与续跑

每批最多 24 小时，按 float64 估算的未压缩波段数值量最多 32 MiB。`max_output_mib` 另行限制运行时实际输出文件及清单的总体积。这些上限不保证进程内存、全局缓存、服务配额或完成时长；上游仍可能拒绝请求。

完成的批次保存为压缩 NetCDF。清单记录来源、规范化请求和每个文件的校验值，使输出绑定于特定请求和分发渠道。续跑前核对已有输出，配置变化或文件异常会被拒绝。需检查被拒绝的目录，不同请求使用新目录。

`verify` 检查清单及登记批次的内容。`bundle` 先核验再创建 ZIP，且拒绝覆盖已有目标。ZIP CRC 和 SHA-256 用于检查相对于清单的意外损坏，不证明发布者身份、科学准确性或与 CDS/ARCO 逐值一致。

异常终止可能留下 `.run.lock`。只有确认没有写入进程后才可处理锁；若已有 NetCDF 尚未登记清单，程序会拒绝覆盖。保留该目录供检查，使用新目录继续，不要删除已核验结果强行重试。容量限额是请求身份的一部分，修改限额也需新目录。

## 独立查询

可选示例将本地输出中的西北角单格点转换为 Parquet，并通过 DuckDB 查询，不计算区域均值，不查找或写入私人研究数据库。下游单位转换、时间聚合、质量过滤与派生指标均应明确记录方法及来源。
