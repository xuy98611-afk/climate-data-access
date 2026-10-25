# 第三方数据、服务与软件说明

[MIT 许可证](LICENSE)适用于本项目代码，不替代任何上游数据、API 服务或依赖软件的条款。仓库不包含气象原始数据包、第三方库源码或账号凭据。通过 pip 安装的依赖继续适用其版本对应的许可证与声明。

## ERA5 与 Earth Engine

ERA5 由 ECMWF 为哥白尼气候变化服务 C3S 制作。本项目通过 [Earth Engine ERA5 逐小时集合](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_HOURLY)及官方 SDK 获取限定范围的变量。引用、波段、原始参考资料与数据使用条件以该页面及其所链接的官方条款为准；成果须明确数据制作机构和实际分发路径。

Earth Engine 的账号、项目资格、服务条款与数据许可分别适用。使用自己的有资格项目和本机认证；不能将个人研究资格自动推广到收费项目。参见[认证指南](https://developers.google.com/earth-engine/guides/auth)、[computePixels 文档](https://developers.google.com/earth-engine/apidocs/ee-data-computepixels)和[服务条款](https://earthengine.google.com/terms/)。

## NASA POWER

点位日/小时路线直接调用 NASA POWER 官方公开 API。产品由多种来源加工形成，不能当作气象站观测。代码保留原始响应、源单位、来源信息、UTC 与缺失约定；研究者应核对所选参数的定义、来源时期和适用性。

获取方式、参数与服务限制见 [POWER API 官方文档](https://power.larc.nasa.gov/docs/services/api/)，科学方法、引用与确认方式从 [POWER 官方文档入口](https://power.larc.nasa.gov/docs/)查阅。公开接口无需账号不等于无限配额，也不表示本项目赋予数据再分发或商业使用的独立许可。请遵循当前官方条款与来源致谢要求。

## Open-Meteo

本项目使用历史天气 API，明确固定 ERA5 模型、最近格点、UTC，并禁用高程订正。Open-Meteo 是此路线的分发和处理服务；不得将其点位处理结果描述为未经处理的 GEE/CDS 区域成果。变量与处理参数见[历史天气 API 官方文档](https://open-meteo.com/en/docs/historical-weather-api)。

Open-Meteo 的免费 API 适用非商业使用与请求限制；数据许可及署名条件与服务访问条件需分别遵守。商业用途或超出免费服务限额应按其当前方案处理。参见[官方条款与许可条件](https://open-meteo.com/en/terms)；不要把“无需账号”理解为任意用途免费。Open-Meteo [公开源码](https://github.com/open-meteo/open-meteo)本身的许可证也不等于免费 API 的服务条件。

## Python 依赖

实际依赖见 pyproject.toml，下表只帮助定位上游，不代替许可证文件。

| 依赖 | 用途 | 上游 |
| --- | --- | --- |
| NumPy | 数值数组与离线测试 | [numpy.org](https://numpy.org/) |
| xarray | 标签数组及 NetCDF 读写 | [xarray.dev](https://xarray.dev/) |
| h5netcdf / h5py | 压缩 NetCDF/HDF5 输出 | [h5netcdf](https://github.com/h5netcdf/h5netcdf) · [h5py](https://www.h5py.org/) |
| earthengine-api（可选） | 官方 Earth Engine Python SDK | [earthengine-api](https://github.com/google/earthengine-api) |
| PyArrow（可选） | 独立 Parquet 查询示例 | [arrow.apache.org](https://arrow.apache.org/) |
| DuckDB（可选） | 独立本地 SQL 查询示例 | [duckdb.org](https://duckdb.org/) |

点位 HTTP 与本地网页服务使用 Python 标准库，未引入 POWER 或 Open-Meteo 第三方客户端。测试样本由合成数组/JSON 构成，不代表气象观测或真实再分析数据。

## 目录与架构参考

目录链接不授予下载或再分发许可，不表示合作或背书，也不能推定不同服务账号权限互通。每个来源都须分别核对资格、许可、使用限额与引用方式。

[生态文档](docs/ecosystem.md)列出的 EODAG、earthaccess、earthkit-data、intake-esm 是架构参考与未来集成候选；当前没有安装、调用或复制其源码。未来引入时应按具体版本补充依赖、许可证声明、能力与验证证据。
