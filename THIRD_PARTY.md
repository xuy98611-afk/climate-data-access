# 第三方数据与软件说明

MIT 许可证适用于本项目代码。仓库不包含 ERA5 数据或第三方软件源码。通过 pip 安装的依赖继续适用其自身许可证与声明，重新分发前应核对所安装版本。

## ERA5 与 Earth Engine

ERA5 由 ECMWF 为哥白尼气候变化服务 C3S 制作。客户端请求 [Earth Engine ERA5 逐小时集合](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_HOURLY)。当前数据条款、引用方式、波段定义及原始参考资料以该官方页面为准；研究成果应引用数据集，并说明制作机构与分发渠道。

Google Earth Engine 提供分发和计算服务；服务条款及账号/项目资格与数据集许可分别适用。参见[认证指南](https://developers.google.com/earth-engine/guides/auth)、[computePixels 文档](https://developers.google.com/earth-engine/apidocs/ee-data-computepixels)及[服务条款](https://earthengine.google.com/terms/)。

来源目录中的链接不授予下载或再分发许可，不表示项目关联，也不代表不同服务之间的账号权限互通。各产品的当前许可、使用限额和署名要求应分别核对。

## Python 依赖

依赖定义见 `pyproject.toml`。下表用于定位上游，不替代依赖本身的许可证声明。

| 依赖 | 用途 | 上游 |
| --- | --- | --- |
| NumPy | 数值数组与离线测试 | [numpy.org](https://numpy.org/) |
| xarray | 标签数组及 NetCDF 读写 | [xarray.dev](https://xarray.dev/) |
| h5netcdf / h5py | 压缩 NetCDF/HDF5 输出 | [h5netcdf](https://github.com/h5netcdf/h5netcdf)、[h5py](https://www.h5py.org/) |
| earthengine-api（可选） | 官方 Earth Engine Python SDK | [earthengine-api](https://github.com/google/earthengine-api) |
| PyArrow（可选） | 独立 Parquet 查询示例 | [arrow.apache.org](https://arrow.apache.org/) |
| DuckDB（可选） | 独立本地 SQL 查询示例 | [duckdb.org](https://duckdb.org/) |

测试数组是合成样本，不代表气象数据；生成测试样本不需要下载上游数据集。
