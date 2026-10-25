# 成熟工具与后续复用方向

本项目的定位是个人研究的统一工作流：查来源、保存请求、离线规划、明确获取、保留来源并核验结果。尽量复用成熟的数据访问工具，把本项目需要的请求约束和成果核验放在适配层。

**当前真正执行的依赖与路线**只有 GEE 官方 Python SDK 的 ERA5 区域访问，以及 NASA POWER、Open-Meteo 的标准库 HTTP 点位访问。下列前四个库没有安装、没有调用，也没有接成连接器；这里记录可借鉴的结构与未来集成方向。

| 工具 | 官方提供的能力 | 本项目可借鉴或后续集成的方向 |
| --- | --- | --- |
| EODAG | 按提供者/集合搜索和下载，包含搜索与认证插件 | 借鉴“产品目录、搜索、认证、下载分离”；未来按确切集合包装一条路线，保留显式提供者 |
| earthaccess | 通过 Earthdata 认证、检索并访问 NASA 数据 | 将来用于需要 Earthdata 的 NASA 集合；不能把 POWER 无账号路线推定为 Earthdata 权限 |
| earthkit-data | 以数据源入口读取和获取多种气象格式，支持 GRIB/NetCDF 等处理 | 将来用于明确的 ECMWF/CDS/文件读取路线；校验数据源版本、网格、时间与格式行为 |
| intake-esm | 检索地球系统模型资产目录并载入分析用数组 | 将来用于 CMIP 等多资产目录；在载入前固定模式、试验、成员、版本与变量 |
| Open-Meteo | 通过历史天气 API 暴露 ERA5 等产品 | 已实现其固定 ERA5 点位 HTTP 路线；保留最近格点、UTC、禁用高程订正等明确参数 |

官方源码与文档：

- EODAG：[源码](https://github.com/CS-SI/eodag) · [官方文档](https://eodag.readthedocs.io/en/stable/)
- earthaccess：[源码](https://github.com/earthaccess-dev/earthaccess) · [官方快速开始](https://earthaccess.readthedocs.io/en/latest/user/quick-start/)
- earthkit-data：[源码](https://github.com/ecmwf/earthkit-data) · [官方文档](https://earthkit-data.readthedocs.io/en/latest/)
- intake-esm：[源码](https://github.com/intake/intake-esm) · [官方文档](https://intake-esm.readthedocs.io/en/stable/)
- Open-Meteo：[源码](https://github.com/open-meteo/open-meteo) · [历史天气 API](https://open-meteo.com/en/docs/historical-weather-api)

这些链接是架构参考和集成候选，不表示上述项目与本项目有合作或背书。当前项目未复制这些库的源码；安装或重新分发时分别核对其版本与许可证。

## 如何逐步接入

新增路线先声明准确能力与限制，再用适配器调用选定库：本项目负责离线计划、来源身份、请求预算、可回读输出和核验；成熟库负责已支持的搜索、认证、传输或格式读取。所有外部默认值都要核对，尤其是模型选择、时区、空间插值、缓存和重试。

每次只实现有实际研究需求的产品与范围，锁定经过测试的依赖版本，并补充离线错误样本及获授权的最小在线验收。认证留在用户本机官方机制，来源目录不能代替账号资格。具体改动位置与契约见[扩展约定](extending.md)。
