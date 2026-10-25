> **本地统一工作台（v0.2）：** 安装后运行 `climate-access serve --open`，在中文页面检索本目录、保存请求并获取 ERA5 / NASA POWER / Open-Meteo 数据。详见 [启动说明](../README.md)。本页仍保留 44 项入口的原有获取步骤；目前实际可执行 3 条路线。

# 普通用户获取气候数据：44项入口与操作步骤

**核对日期：2026-10-24。** 从无需账号的小样本开始；需要注册时，用自己的个人账号按官方流程操作。

这份目录同时列出可公开获取、需注册、需用途资格、需申请和未确认下载的条目。它不是44项全部已下载成功的承诺。目录、数据集和计算工具按既有条目计数，不是44套相互独立的数据。

## 不会写代码，先从这里开始

1. **NASA POWER**：打开[地图取数页面](https://power.larc.nasa.gov/data-access-viewer/)，选点、日期、要素与格式。也可先查看[单点两天T2M示例JSON](https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M&community=RE&latitude=0&longitude=0&start=20040101&end=20040102&format=JSON&time-standard=UTC)。
2. **NOAA GSOD**：打开[年度目录](https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/)，选年份和站号下载CSV，用Excel导入。先从[示例2024年站点CSV](https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/2024/01001099999.csv)了解字段。
3. **SPEI干旱指数**：打开[2.11版地图](https://spei.csic.es/spei_database_2_11/)，选时间尺度和地点，使用Download point。Download NC为格点文件，通常更大。

需要查看NetCDF或GeoTIFF而不做编程时，可以使用兼容的可视化软件；例如NASA的[Panoply](https://www.giss.nasa.gov/tools/panoply/)支持多种地学数组文件。Parquet、GRIB和云原生存储仍需要相应工具。“无需账号”不等于“无需数据处理知识”。

## 获取条件统计

| 条件 | 条目数 | 含义 |
| --- | ---: | --- |
| 无需账号的公开路线 | 22 | 提供公开文件/API/存储路线；实测范围分别标注，仍有配额、格式和许可要求。 |
| 免费注册后按产品获取 | 14 | 有免费个人注册及产品获取流程；本轮未注册测试每个下载服务。 |
| 按产品分公开、注册或受限 | 4 | 同一平台不同产品的权限不同，必须看具体产品。 |
| 需注册并满足用途资格 | 1 | 需要注册并核对非商业等使用资格；不承诺任意用户免费计算。 |
| 需实名、申请或站方确认 | 3 | 可能需要实名或站方审核，未取得目标时序的下载验收。 |
| 下载流程尚未确认 | 0 | 可见公开选择器/说明，但未提交表单或完成下载。 |
| 合计 | 44 | 包含有条件及待核验项目。 |

NASA相关共10项，其中NEX-GDDP-CMIP6归入未来情景类；GLDAS/NLDAS/FLDAS等并列产品沿用一条目录记录，不另拆数量。

## 本轮确认和修正

- NASA POWER逐日2条、逐小时24条T2M及Open-Meteo单点一天24小时响应通过结构和非缺测检查。
- Meteostat Parquet、GHCN固定宽度文本、GSOD/IBTrACS CSV、WorldClim ZIP和SPEI/IMD NetCDF只读取文件前缀；不称全文件核验。
- ARCO读取Zarr组元数据，Planette、NCAR及NEX-GDDP读取匿名对象列表；不称多年数据下载验收。
- NOAA ISD旧文件地址此次返回HTML，已改列官方Access Data Service的CSV路线；失败记录仍保留。
- SPEI浏览工具读取超时，但匿名HTTP和真实NetCDF前缀可读，已补入当前地图与下载链接。
- DWD/GPCC的Python客户端出现本地证书链问题，使用系统证书客户端和独立浏览核对目录；没有关闭TLS验证。
- JRA-3Q更新到JMA当前地址，按其指引列NCAR/GDEX；JMA明确DIAS处于长期维护，不推荐读者走该失效入口。
- CERES官方页面公告2026-10-23至10-26维护，标为暂时维护；公开页面可见不代表此时能完成订单。

## 各入口操作卡

每项均提供起始链接、三步操作、账号条件和核验边界。官方规则或服务状态可能改变，失败时回到产品页重新定位，不将返回的HTML当成数据文件。

### 1. ERA5 逐小时

<a id="era5_hourly"></a>

**类别**：再分析与综合气象；**获取条件**：免费注册后按产品获取。

入口：[ERA5 逐小时](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=download)。用途：气温、露点、气压、风、降水、辐射。

1. 在CDS免费注册或登录自己的账号。
2. 选择变量、年月日、小时和小范围区域，接受本数据集条款。
3. 提交小批请求，等待任务完成后下载；批量编程再按官方API指南配置自己的令牌。

**核验与限制**：注册和许可步骤已由官方说明确认；本轮未代新用户注册或重新提交CDS任务，不能保证排队时长。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=download)；[说明2](https://cds.climate.copernicus.eu/how-to-api)。

### 2. ERA5 逐日统计

<a id="era5_daily"></a>

**类别**：再分析与综合气象；**获取条件**：免费注册后按产品获取。

入口：[ERA5 逐日统计](https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics?tab=download)。用途：最高气温、最低气温、日平均、露点、气压。

1. 注册或登录CDS。
2. 选择变量、日统计量、小时采样与时区，并接受产品条款。
3. 先请求少量日期和小区域，完成后下载。

**核验与限制**：日统计是小时数据的聚合；采样和日界要记录。本轮只核对官方目录与获取流程。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics?tab=download)；[说明2](https://cds.climate.copernicus.eu/how-to-api)。

### 3. ERA5-Land

<a id="era5_land"></a>

**类别**：再分析与综合气象；**获取条件**：免费注册后按产品获取。

入口：[ERA5-Land](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=download)。用途：气温、土壤温度、土壤水分、蒸发、径流。

1. 注册或登录CDS。
2. 选择ERA5-Land所需变量、时间和区域，接受产品条款。
3. 提交小批任务并从任务结果下载。

**核验与限制**：ERA5-Land与ERA5分开使用；本轮未进行登录后下载验收。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=download)；[说明2](https://cds.climate.copernicus.eu/how-to-api)。

### 4. Open-Meteo

<a id="open_meteo"></a>

**类别**：再分析与综合气象；**获取条件**：无需账号的公开路线。

入口：[Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api)。用途：气温、降水、湿度、风、日照、湿球温度。

1. 在历史天气页面填写经纬度和起止日期。
2. 勾选气温、降水等要素；长期研究明确选择ERA5或ERA5-Land，选择时区。
3. 使用页面生成的请求，按提供的格式导出或保存响应。

**核验与限制**：免费公开接口有用途和请求量限制，商业及大规模使用核对订阅条件；已实测单点一天24小时JSON。历史预报是另一个子接口，不能当作ERA5。

**证据层级**：anonymous_sample（无账号小请求通过结构/数量检查，只证明所测样本）。

官方说明：[说明1](https://open-meteo.com/en/docs/historical-weather-api)；[说明2](https://open-meteo.com/en/terms)；[说明3](https://open-meteo.com/en/docs/historical-forecast-api)。

### 5. Meteostat

<a id="meteostat"></a>

**类别**：站点观测；**获取条件**：无需账号的公开路线。

入口：[Meteostat](https://dev.meteostat.net/data/bulk.html)。用途：站点气温、站点降水、气压、风、历史天气。

1. 进入Bulk Data，选择日、小时或月数据说明。
2. 按照官方模板下载相应年份Parquet，并按需取得站点坐标目录。
3. 用支持Parquet的工具读取，按站号和日期筛选，检查每列来源标记。

**核验与限制**：Bulk无需账号或key；JSON API是另一路线。Parquet需要兼容工具，年文件可能较大；含模型补充值，不能全称纯站点观测。已核验2024年文件PAR1前缀。

**证据层级**：file_prefix（读取到预期文件格式或CSV前缀，未验证全文件）。

官方说明：[说明1](https://dev.meteostat.net/data/bulk.html)；[说明2](https://dev.meteostat.net/data/bulk/daily)。

### 6. NOAA GHCN-Daily

<a id="noaa_ghcnd"></a>

**类别**：站点观测；**获取条件**：无需账号的公开路线。

入口：[NOAA GHCN-Daily](https://www.ncei.noaa.gov/pub/data/ghcn/daily/)。用途：站点最高气温、站点最低气温、站点降水、雪。

1. 先读取readme和站点目录，确定站号。
2. 进入all或by_station目录，下载对应测站文件。
3. 按官方字段定义读取气温和降水，并保留缺测与质量旗标。

**核验与限制**：公开文件路线无需CDO令牌；固定宽度.dly不等于现成Excel。已读取一个站文件前缀，未下载全站年序列。

**证据层级**：file_prefix（读取到预期文件格式或CSV前缀，未验证全文件）。

官方说明：[说明1](https://www.ncei.noaa.gov/pub/data/ghcn/daily/)；[说明2](https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt)。

### 7. NOAA ISD / Global Hourly

<a id="noaa_isd"></a>

**类别**：站点观测；**获取条件**：无需账号的公开路线。

入口：[NOAA ISD / Global Hourly](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)。用途：能见度、小时气温、露点、气压、风、云。

1. 从产品说明确定站号和年份。
2. 优先使用官方Access Data Service的global-hourly短日期CSV请求，或从现行产品页进入文件分发。
3. 先取一天检查字段及质量码，再扩大时段；ISD-Lite是另一个简化子通道。

**核验与限制**：旧global-hourly和ISD-Lite文件URL在此次测试返回HTML，未误判为CSV成功；官方数据服务短日期CSV可读。NOAA正在迁移云服务，按当前产品页定位。

**证据层级**：file_prefix（读取到预期文件格式或CSV前缀，未验证全文件）。

官方说明：[说明1](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)；[说明2](https://www.ncei.noaa.gov/support/access-data-service-api)。

### 8. NOAA GSOD

<a id="noaa_gsod"></a>

**类别**：站点观测；**获取条件**：无需账号的公开路线。

入口：[NOAA GSOD](https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/)。用途：日均能见度、日均气温、降水、风。

1. 在公开目录点击年份。
2. 按USAF+WBAN站号找到对应CSV文件并下载。
3. 用Excel导入CSV，按变量说明识别单位、缺测码及观测次数。

**核验与限制**：已核验示例年度CSV前缀；日均统计不是小时原值，不能据此得到日最低能见度或低能见度时长。

**证据层级**：file_prefix（读取到预期文件格式或CSV前缀，未验证全文件）。

官方说明：[说明1](https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/)；[说明2](https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc:C00516/html)。

### 9. 德国 DWD Climate Data Center

<a id="dwd_cdc"></a>

**类别**：站点观测；**获取条件**：无需账号的公开路线。

入口：[德国 DWD Climate Data Center](https://opendata.dwd.de/climate_environment/CDC/)。用途：站点气温、降水、日照、风、欧洲格点。

1. 选择observations_germany、observations_global或需要的格点目录。
2. 逐层选择变量、频率，以及historical或recent。
3. 下载站点说明和数据压缩包，按随附字段说明读取。

**核验与限制**：公开目录无账号；Python本次出现本地证书链问题，Windows系统证书客户端及独立浏览工具可读，未关闭TLS验证。

**证据层级**：listing_or_metadata（匿名目录或元数据可读，未验证气象值）。

官方说明：[说明1](https://opendata.dwd.de/climate_environment/CDC/)；[说明2](https://opendata.dwd.de/climate_environment/CDC/Liesmich_intro_CDC-FTP.txt)。

### 10. 英国 Met Office / CEDA

<a id="metoffice_ceda"></a>

**类别**：站点观测；**获取条件**：按产品分公开、注册或受限。

入口：[英国 Met Office / CEDA](https://www.metoffice.gov.uk/research/climate/maps-and-data/data)。用途：英国站点、HadUK-Grid、MIDAS Open、气候统计。

1. 在Met Office数据页选择需要的具体产品。
2. 公开文本可直接下载；进入CEDA时检查Public、Registered或Restricted标记。
3. Registered产品用个人账号注册，Restricted产品按该数据集要求申请。

**核验与限制**：CEDA允许个人注册，但部分产品有地区或机构限制；不能把整个CEDA都称作普通人免费直下。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://www.metoffice.gov.uk/research/climate/maps-and-data/data)；[说明2](https://help.ceda.ac.uk/article/39-ceda-account)。

### 11. 中国气象数据网 CMA

<a id="cma"></a>

**类别**：中国与区域资料；**获取条件**：需实名、申请或站方确认。

入口：[中国气象数据网 CMA](https://data.cma.cn/)。用途：中国站点、地面气候日值、日照、能见度。

1. 打开中国气象数据网并查看目标数据集的访问对象。
2. 按网站要求实名注册和提交所需用途材料。
3. 账号无权访问或需要当地站资料时，按中国气象局公开指引咨询相应部门。

**核验与限制**：主页读取结果不稳定，本轮未完成普通个人账号下载验收；实名注册不保证所有站点和年份获准。需要中国站点时也可另查NOAA公开站点，但不能承诺覆盖相同。

**证据层级**：not_download_verified（只找到门户/申请步骤/年份选择器，下载尚未确认）。

官方说明：[说明1](https://data.cma.cn/)；[说明2](https://www.cma.gov.cn/wmhd/gzly/cjwt/202204/t20220415_4759049.html)；[说明3](https://data.nsmc.org.cn/dataportal/cn/support/user.html)。

### 12. 国家青藏高原科学数据中心 TPDC

<a id="tpdc"></a>

**类别**：中国与区域资料；**获取条件**：需实名、申请或站方确认。

入口：[国家青藏高原科学数据中心 TPDC](https://data.tpdc.ac.cn/)。用途：高原气象、CMFD、陆面、水文、生态、实测站。

1. 在支持JavaScript的浏览器里搜索数据集或DOI。
2. 阅读具体产品的共享方式、用途及申请条件，使用自己的账号登录。
3. 开放下载按页面操作；受控产品提交申请后等待审核。

**核验与限制**：本轮读取到JS门户和公开服务说明，未执行登录后下载；各产品分别授权，不承诺所有资料对任意个人自动开放。

**证据层级**：not_download_verified（只找到门户/申请步骤/年份选择器，下载尚未确认）。

官方说明：[说明1](https://data.tpdc.ac.cn/)；[说明2](https://www.tpdc.ac.cn/about)。

### 13. 印度 IMD 格点降水

<a id="imd_india"></a>

**类别**：中国与区域资料；**获取条件**：无需账号的公开路线。

入口：[印度 IMD 格点降水](https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html)。用途：印度日降水、季风。

1. 进入0.25°逐日格点降水的官方页面。
2. 从年份选择框选一年的NetCDF。
3. 按页面下载提示操作；如出现登记或条款，先核对身份要求再继续。

**核验与限制**：已按公开年份选择器匿名提交2024年请求，读取1KiB并确认NetCDF/HDF5签名；未下载或核验整年文件。仅覆盖印度产品范围。

**证据层级**：file_prefix（读取到预期文件格式或CSV前缀，未验证全文件）。

官方说明：[说明1](https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html)。

### 14. NASA Earthdata Search

<a id="earthdata"></a>

**类别**：NASA 与卫星陆面；**获取条件**：免费注册后按产品获取。

入口：[NASA Earthdata Search](https://search.earthdata.nasa.gov/)。用途：NASA、卫星、MERRA-2、GLDAS、GPM、MODIS。

1. 免费注册自己的Earthdata Login账号并验证邮箱。
2. 在Earthdata Search选数据集、时间和区域。
3. 登录后按产品下载或定制；如提示授权，只授权所需的官方数据应用。

**核验与限制**：这是数据检索平台，不是一套单独气候数据；本轮核对免费自助注册说明，未验证新账号的每个下载服务。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://search.earthdata.nasa.gov/)；[说明2](https://urs.earthdata.nasa.gov/documentation/for_users)；[说明3](https://nsidc.org/data/user-resources/help-center/downloading-nsidc-daac-earthdata-cloud-data-using-web-browser)。

### 15. NASA POWER

<a id="nasa_power"></a>

**类别**：NASA 与卫星陆面；**获取条件**：无需账号的公开路线。

入口：[NASA POWER](https://power.larc.nasa.gov/data-access-viewer/)。用途：太阳辐射、气温、湿度、风、降水、农业气象。

1. 在Data Access Viewer选地图点和所需应用类别。
2. 选择小时、日或月、时间范围及气温/辐射/风等变量。
3. 导出所需格式；不会操作地图时，可先打开本指南给出的单点JSON示例。

**核验与限制**：已匿名验证逐日2条及逐小时24条T2M响应；不是站点实测，不对所有变量组合或区域配额作保证。

**证据层级**：anonymous_sample（无账号小请求通过结构/数量检查，只证明所测样本）。

官方说明：[说明1](https://power.larc.nasa.gov/data-access-viewer/)；[说明2](https://power.larc.nasa.gov/docs/services/api/)。

### 16. NASA MERRA-2

<a id="merra2"></a>

**类别**：NASA 与卫星陆面；**获取条件**：免费注册后按产品获取。

入口：[NASA MERRA-2](https://gmao.gsfc.nasa.gov/gmao-products/merra-2/data-access_merra-2/)。用途：气温、风、辐射、气溶胶、气压、湿度。

1. 注册Earthdata Login。
2. 从官方Data Access进入GES DISC，选对应MERRA-2集合。
3. 设置时间和区域，按产品页面下载或子集服务操作，并完成所需应用授权。

**核验与限制**：已核对官方分发和免费账号流程，未做登录后取数；瞬时、时均与累计量分开解释。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://gmao.gsfc.nasa.gov/gmao-products/merra-2/data-access_merra-2/)；[说明2](https://urs.earthdata.nasa.gov/documentation/for_users)。

### 17. NASA GLDAS / NLDAS / FLDAS

<a id="gldas"></a>

**类别**：NASA 与卫星陆面；**获取条件**：免费注册后按产品获取。

入口：[NASA GLDAS / NLDAS / FLDAS](https://ldas.gsfc.nasa.gov/gldas)。用途：土壤湿度、蒸散、径流、雪、陆面通量。

1. 注册Earthdata Login。
2. 在Get the Data分别选择GLDAS、NLDAS或FLDAS，进入GES DISC。
3. 选模型、版本、变量和时间，按下载或子集服务提示获取。

**核验与限制**：三个系统的范围和模型不同；本轮核对产品页与流程，未完成登录后的下载验收。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://ldas.gsfc.nasa.gov/gldas)；[说明2](https://urs.earthdata.nasa.gov/documentation/for_users)。

### 18. NASA GPM IMERG / TRMM

<a id="gpm_imerg"></a>

**类别**：NASA 与卫星陆面；**获取条件**：免费注册后按产品获取。

入口：[NASA GPM IMERG / TRMM](https://gpm.nasa.gov/data/imerg)。用途：卫星降水、极端降水、降水强度。

1. 注册Earthdata Login。
2. 从GPM数据目录选择所需IMERG版本，进入Earthdata或GES DISC路线。
3. 确定Early/Late/Final、时间频率及区域后下载；PPS路线如使用须另核对注册。

**核验与限制**：选择的免费账号路线与PPS权限分开；本轮未进行登录后下载，不混用降水率与累计量。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://gpm.nasa.gov/data/imerg)；[说明2](https://urs.earthdata.nasa.gov/documentation/for_users)。

### 19. NASA SMAP / NSIDC

<a id="smap"></a>

**类别**：NASA 与卫星陆面；**获取条件**：免费注册后按产品获取。

入口：[NASA SMAP / NSIDC](https://smap.jpl.nasa.gov/data/)。用途：土壤水分、冻融、根区水分。

1. 注册Earthdata Login。
2. 从SMAP产品表选择等级并进入NSIDC数据页。
3. 使用Earthdata Search或页面的HTTPS File System，按日期找到文件并登录下载。

**核验与限制**：官方有无需编程的浏览器下载教程；本轮未登录取数，L4是模型同化产品。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://smap.jpl.nasa.gov/data/)；[说明2](https://nsidc.org/data/user-resources/help-center/downloading-nsidc-daac-earthdata-cloud-data-using-web-browser)；[说明3](https://urs.earthdata.nasa.gov/documentation/for_users)。

### 20. NASA MODIS / VIIRS（AppEEARS路线）

<a id="modis_viirs"></a>

**类别**：NASA 与卫星陆面；**获取条件**：免费注册后按产品获取。

入口：[NASA MODIS / VIIRS（AppEEARS路线）](https://appeears.earthdatacloud.nasa.gov/)。用途：地表温度、NDVI、EVI、蒸散、积雪、植被。

1. 注册并登录Earthdata账号。
2. 在AppEEARS创建点或区域提取任务，选择产品、变量、日期和位置。
3. 先提交小任务，完成后下载结果并保留质量层及比例因子。

**核验与限制**：AppEEARS是JS应用，不包含全部MODIS/VIIRS产品；本轮核对门户及官方说明，未提交登录后提取任务。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://appeears.earthdatacloud.nasa.gov/)；[说明2](https://appeears.earthdatacloud.nasa.gov/api/)；[说明3](https://urs.earthdata.nasa.gov/documentation/for_users)。

### 21. NASA Giovanni

<a id="giovanni"></a>

**类别**：NASA 与卫星陆面；**获取条件**：免费注册后按产品获取。

入口：[NASA Giovanni](https://giovanni.gsfc.nasa.gov/giovanni/)。用途：区域平均、时间序列、降水、气溶胶、陆面。

1. 使用Earthdata Login登录Giovanni。
2. 选择数据集、变量、时间及区域，再选择时间序列或区域统计。
3. 先运行一个小分析，完成后导出结果，记录数据来源和统计方法。

**核验与限制**：在线分析工具，不是独立数据源；本轮核对门户及LDAS官方说明，未运行登录后分析。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://giovanni.gsfc.nasa.gov/giovanni/)；[说明2](https://ldas.gsfc.nasa.gov/gldas)；[说明3](https://urs.earthdata.nasa.gov/documentation/for_users)。

### 22. NASA CERES

<a id="ceres"></a>

**类别**：NASA 与卫星陆面；**获取条件**：免费注册后按产品获取。

入口：[NASA CERES](https://ceres.larc.nasa.gov/Data/)。用途：短波辐射、长波辐射、地球辐射收支、云。

1. 先检查CERES产品页顶部维护公告。
2. 选产品后进入Order Data或CERES Search and Subsetting。
3. 使用Earthdata账号登录并选择时空范围下载；维护期间稍后重试。

**核验与限制**：官方公告列出2026-10-23至10-26维护窗口，本次按暂时维护标记，不能保证现在完成下载。Earthdata登录要求有官方说明。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。
当前状态：**暂时维护**；请在官方公告窗口结束后确认服务。

官方说明：[说明1](https://ceres.larc.nasa.gov/Data/)；[说明2](https://subset.larc.nasa.gov/ceres/login.php)；[说明3](https://urs.earthdata.nasa.gov/documentation/for_users)。

### 23. CHIRPS v3 / CHIRPS v2

<a id="chirps"></a>

**类别**：降水、干旱与高分辨率格点；**获取条件**：无需账号的公开路线。

入口：[CHIRPS v3 / CHIRPS v2](https://www.chc.ucsb.edu/data/chirps3)。用途：降水、旱涝、降水极端。

1. 进入CHIRPS v3说明并点击对应数据下载目录。
2. 选日、月或候等频率，区分preliminary和final，再选年份。
3. 下载NetCDF或GeoTIFF文件，并记录v3版本及日产品路线。

**核验与限制**：目录可匿名读取；不把v2、v3或不同日下分配产品混用。本轮检查目录，不做完整栅格下载。

**证据层级**：listing_or_metadata（匿名目录或元数据可读，未验证气象值）。

官方说明：[说明1](https://www.chc.ucsb.edu/data/chirps3)；[说明2](https://data.chc.ucsb.edu/products/CHIRPS/v3.0/)。

### 24. DWD GPCC

<a id="gpcc"></a>

**类别**：降水、干旱与高分辨率格点；**获取条件**：无需账号的公开路线。

入口：[DWD GPCC](https://opendata.dwd.de/climate_environment/GPCC/)。用途：全球陆地降水、站点降水插值。

1. 在目录选择Daily、Monthly或Climatology产品。
2. 继续选版本与网格，先下载README和说明。
3. 再下载所需年份文件，用支持NetCDF的工具读取。

**核验与限制**：系统证书客户端确认目录公开可读；未关闭TLS校验。目录可读不证明所有年份文件完整。

**证据层级**：listing_or_metadata（匿名目录或元数据可读，未验证气象值）。

官方说明：[说明1](https://opendata.dwd.de/climate_environment/GPCC/)。

### 25. TerraClimate

<a id="terraclimate"></a>

**类别**：降水、干旱与高分辨率格点；**获取条件**：无需账号的公开路线。

入口：[TerraClimate](https://www.climatologylab.org/terraclimate.html)。用途：温度、降水、蒸散、水分亏缺、VPD、PDSI。

1. 打开Download部分，选择官方年度NetCDF目录或THREDDS子集入口。
2. 按版本、变量和年份选择所需文件。
3. 下载或裁剪子集后读取，保留单位和来源说明。

**核验与限制**：官方页面明确提供逐变量/逐年文件和子集路线；本轮未下载整年文件。v1.0与v1.1不能随意拼接。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://www.climatologylab.org/terraclimate.html)。

### 26. CRU TS / CRU CY

<a id="cru_ts"></a>

**类别**：降水、干旱与高分辨率格点；**获取条件**：按产品分公开、注册或受限。

入口：[CRU TS / CRU CY](https://crudata.uea.ac.uk/cru/data/hrg/)。用途：温度、降水、PET、水汽压、国家气候序列。

1. 在CRU页面选择当前版本或明确需要的历史版本。
2. 按该版本链接进入CRU目录或CEDA，先查看访问等级。
3. 公开目录直接下载；CEDA需账号的产品按个人注册和产品条款操作。

**核验与限制**：CRU公开目录本轮可读；不同版次可能走CEDA或按需申请。不要把所有CRU产品都写成无需注册。

**证据层级**：listing_or_metadata（匿名目录或元数据可读，未验证气象值）。

官方说明：[说明1](https://crudata.uea.ac.uk/cru/data/hrg/)；[说明2](https://help.ceda.ac.uk/article/39-ceda-account)。

### 27. WorldClim

<a id="worldclim"></a>

**类别**：降水、干旱与高分辨率格点；**获取条件**：无需账号的公开路线。

入口：[WorldClim](https://www.worldclim.org/data/worldclim21.html)。用途：气候平均、BIO生物气候、温度、降水。

1. 在历史气候页面选择变量与网格分辨率。
2. 点击表格中的ZIP链接下载。
3. 解压后用QGIS等兼容工具读取GeoTIFF；先从较小的10分钟网格开始。

**核验与限制**：已核验示例ZIP前缀；这些长期气候平均不能代替每年的真实天气序列。

**证据层级**：file_prefix（读取到预期文件格式或CSV前缀，未验证全文件）。

官方说明：[说明1](https://www.worldclim.org/data/worldclim21.html)。

### 28. CHELSA

<a id="chelsa"></a>

**类别**：降水、干旱与高分辨率格点；**获取条件**：无需账号的公开路线。

入口：[CHELSA](https://www.chelsa-climate.org/)。用途：高分辨率温度、降水、BIO、SPI、SPEI。

1. 在Datasets选择需要的日、月、气候平均或情景产品。
2. 检查产品页状态和覆盖，再进入Download链接的公开存储浏览器。
3. 按变量和时段下载；先检查一小块文件与质量说明。

**核验与限制**：部分产品标有缺口或incomplete，不能承诺所需日期齐全；本轮核对产品与下载入口，未整文件下载。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://www.chelsa-climate.org/)；[说明2](https://envicloud.wsl.ch/)。

### 29. SPEIbase / Global Drought Monitor

<a id="spei"></a>

**类别**：降水、干旱与高分辨率格点；**获取条件**：无需账号的公开路线。

入口：[SPEIbase / Global Drought Monitor](https://spei.csic.es/database.html)。用途：SPEI、干旱、标准化水分亏缺。

1. 进入SPEIbase当前版本的交互地图。
2. 选择时间尺度，地图选点后使用Download point导出序列。
3. 需要格点数据时使用Download NC；先确认文件较大和所需时间尺度。

**核验与限制**：已找到2.11版实际NetCDF，并匿名核验1KiB文件签名；浏览工具超时不等于服务不可用。未核验全文件和逐值准确性。

**证据层级**：file_prefix（读取到预期文件格式或CSV前缀，未验证全文件）。

官方说明：[说明1](https://spei.csic.es/database.html)；[说明2](https://spei.csic.es/spei_database_2_11/)；[说明3](https://spei.csic.es/spei_database_2_11/nc/spei01.nc)。

### 30. Copernicus CMIP6

<a id="cmip6_cds"></a>

**类别**：未来气候情景；**获取条件**：免费注册后按产品获取。

入口：[Copernicus CMIP6](https://cds.climate.copernicus.eu/datasets/projections-cmip6?tab=download)。用途：未来温度、降水、气候情景、SSP。

1. 注册或登录CDS。
2. 选择模式、成员、情景、变量、频率和年份，接受具体许可。
3. 先提交小范围任务，完成后下载并记录日历和成员信息。

**核验与限制**：当前目录与账号/API流程已核对，本轮未进行登录后下载。未来情景不是历史观测。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://cds.climate.copernicus.eu/datasets/projections-cmip6?tab=download)；[说明2](https://cds.climate.copernicus.eu/how-to-api)。

### 31. NASA NEX-GDDP-CMIP6

<a id="nex_gddp"></a>

**类别**：未来气候情景；**获取条件**：无需账号的公开路线。

入口：[NASA NEX-GDDP-CMIP6](https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/)。用途：降尺度未来气温、降水、湿度、风、辐射。

1. 从官方Data Access进入AWS公开存储或THREDDS。
2. 选择模式、情景、成员、变量和年份。
3. 按提供的文件链接下载，或使用THREDDS页面的子集服务。

**核验与限制**：匿名S3对象列表已实测；本轮未下载完整情景文件，也不需要申请NCCS计算账号来使用这条公开存储路线。

**证据层级**：listing_or_metadata（匿名目录或元数据可读，未验证气象值）。

官方说明：[说明1](https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/)；[说明2](https://registry.opendata.aws/nex-gddp-cmip6/)。

### 32. ESGF / Metagrid

<a id="esgf"></a>

**类别**：未来气候情景；**获取条件**：按产品分公开、注册或受限。

入口：[ESGF / Metagrid](https://esgf.github.io/)。用途：CMIP6、CORDEX、全球模式、区域模式。

1. 从ESGF官网进入其推荐的Metagrid检索。
2. 按项目、模式、情景、变量和频率筛选文件。
3. 选择节点的HTTP下载；若该节点要求注册或接受条款，按节点提示操作。

**核验与限制**：平台在迁移，节点规则不同；官网可读不等于所有搜索结果的文件都通过下载测试。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://esgf.github.io/)。

### 33. Google Research ARCO ERA5

<a id="arco"></a>

**类别**：公开镜像与云端计算；**获取条件**：无需账号的公开路线。

入口：[Google Research ARCO ERA5](https://github.com/google-research/arco-era5)。用途：ERA5小时气象、气压层。

1. 阅读项目说明，选择所需变量所在的Zarr存储及版本。
2. 先检查元数据、时间起点、坐标和分块形状。
3. 用支持Zarr的工具只读取所需时空子集，先测试一个小时。

**核验与限制**：匿名Zarr组元数据读取通过；全球块可能很大，需要编程工具。不是给每个用户预先裁好的下载包。

**证据层级**：listing_or_metadata（匿名目录或元数据可读，未验证气象值）。

官方说明：[说明1](https://github.com/google-research/arco-era5)。

### 34. Planette ERA5 Archive

<a id="planette"></a>

**类别**：公开镜像与云端计算；**获取条件**：无需账号的公开路线。

入口：[Planette ERA5 Archive](https://registry.opendata.aws/planette_era5_reanalysis/)。用途：ERA5日/月聚合、气温、降水率。

1. 从AWS公开数据登记页进入Browse Dataset。
2. 按发布方说明选择ERA5聚合产品、变量和快照。
3. 使用支持Zarr/icechunk的工具读取小子集，保留实际快照和聚合口径。

**核验与限制**：官方明确无需AWS账号，匿名对象列表通过；云原生格式需要工具，不是直接Excel下载。

**证据层级**：listing_or_metadata（匿名目录或元数据可读，未验证气象值）。

官方说明：[说明1](https://registry.opendata.aws/planette_era5_reanalysis/)；[说明2](https://github.com/PlanetteAI/planette_era5_archive)。

### 35. Google Earth Engine

<a id="earth_engine"></a>

**类别**：公开镜像与云端计算；**获取条件**：需注册并满足用途资格。

入口：[Google Earth Engine](https://developers.google.com/earth-engine/guides/access)。用途：ERA5、CHIRPS、MODIS、TerraClimate、批量区域统计。

1. 用自己的Google账号创建Cloud项目并启用Earth Engine API。
2. 注册项目用途，符合非商业资格时完成验证；商业用途按官方计费方案处理。
3. 在Code Editor或SDK里选数据集，先运行一个小区域任务。

**核验与限制**：免费计算需要用途资格和周期性验证；不能承诺任意用户免费使用。只取ERA5时可改走CDS或公开镜像。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://developers.google.com/earth-engine/guides/access)。

### 36. NOAA PSL

<a id="noaa_psl"></a>

**类别**：海洋、气候指数与灾害；**获取条件**：无需账号的公开路线。

入口：[NOAA PSL](https://psl.noaa.gov/data/climateindices/list/)。用途：ENSO、Niño3.4、PDO、NAO、季风、气候指数。

1. 在列表选择Niño3.4、PDO、NAO等所需指数。
2. 打开对应原始时间序列文件。
3. 保存为文本并用Excel或其他工具导入，按说明处理缺测码。

**核验与限制**：Niño3.4公开文本已读取；各指数基准期和版本分别记录。

**证据层级**：anonymous_sample（无账号小请求通过结构/数量检查，只证明所测样本）。

官方说明：[说明1](https://psl.noaa.gov/data/climateindices/list/)；[说明2](https://psl.noaa.gov/data/correlation/nina34.data)。

### 37. NOAA IBTrACS

<a id="ibtracs"></a>

**类别**：海洋、气候指数与灾害；**获取条件**：无需账号的公开路线。

入口：[NOAA IBTrACS](https://www.ncei.noaa.gov/products/international-best-track-archive)。用途：台风、热带气旋、路径、风速、中心气压。

1. 在产品页选择CSV Data、NetCDF或Shapefile。
2. 从公开目录选择版本与海盆子集，先下载较小文件。
3. 保留机构字段、风速口径和缺测标记。

**核验与限制**：示例海盆CSV前缀已核验；轨迹融合不是每家机构原始记录的完全等价替代。

**证据层级**：file_prefix（读取到预期文件格式或CSV前缀，未验证全文件）。

官方说明：[说明1](https://www.ncei.noaa.gov/products/international-best-track-archive)；[说明2](https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/)。

### 38. Copernicus Marine

<a id="copernicus_marine"></a>

**类别**：海洋、气候指数与灾害；**获取条件**：免费注册后按产品获取。

入口：[Copernicus Marine](https://data.marine.copernicus.eu/products)。用途：海温、海洋热浪、盐度、流速、海平面、海冰。

1. 免费注册Marine账号，或使用受支持的CDSE联合登录。
2. 在产品目录选择海温、流速等数据，检查覆盖和变量。
3. 设置所需子集并下载；按产品页面选择浏览器或Toolbox路线。

**核验与限制**：官方允许无机构个人注册，下载需要登录；本轮核对流程，未代注册或执行登录后下载。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://data.marine.copernicus.eu/products)；[说明2](https://help.marine.copernicus.eu/en/articles/4220332-how-to-register-for-copernicus-marine-service)。

### 39. Copernicus CAMS / ADS

<a id="cams_ads"></a>

**类别**：海洋、气候指数与灾害；**获取条件**：免费注册后按产品获取。

入口：[Copernicus CAMS / ADS](https://ads.atmosphere.copernicus.eu/)。用途：气溶胶、空气质量、臭氧、温室气体、火排放。

1. 在ADS注册或登录自己的ECMWF可用账号。
2. 选CAMS产品、变量、区域和时间，接受对应产品条款。
3. 先通过下载表单请求小批数据；需要编程时按官方CDSAPI指南配置。

**核验与限制**：账号品牌相同不表示所有数据集已接受许可或有权限；本轮未登录下载。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://ads.atmosphere.copernicus.eu/)；[说明2](https://cds.climate.copernicus.eu/how-to-api)。

### 40. 日本 JRA-3Q / JRA-55

<a id="jra3q"></a>

**类别**：再分析与综合气象；**获取条件**：按产品分公开、注册或受限。

入口：[日本 JRA-3Q / JRA-55](https://www.data.jma.go.jp/jra/html/JRA-3Q/index_en.html)。用途：再分析气温、风、湿度、辐射。

1. 从当前JMA页面选择NCAR/GDEX协作分发，不使用旧失效主机。
2. 进入GDEX的d640000产品页，按需要注册个人账号和接受非商业许可。
3. 选择数据产品和时段，按GDEX下载方式取小样本。

**核验与限制**：旧JMA地址失败已更新；JMA现提示DIAS长期维护。GDEX允许无机构个人注册，但本轮只核对产品/账号政策，未完成登录后下载。

**证据层级**：official_documentation（核对官方产品及获取说明；不表示完成登录后下载）。

官方说明：[说明1](https://www.data.jma.go.jp/jra/html/JRA-3Q/index_en.html)；[说明2](https://gdex.ucar.edu/datasets/d640000/)；[说明3](https://gdex.ucar.edu/news/open-access-data/)。

### 41. ECMWF Open Data：IFS / AIFS

<a id="ecmwf_forecast"></a>

**类别**：数值天气预报；**获取条件**：无需账号的公开路线。

入口：[ECMWF Open Data：IFS / AIFS](https://www.ecmwf.int/en/forecasts/datasets/open-data)。用途：ECMWF、IFS、AIFS、天气预报、气温、降水、风、气压。

1. 点击Browse the data files进入公开预报目录。
2. 选择起报日期、时次、IFS/AIFS模式及预报时效。
3. 下载所需GRIB文件，用兼容工具读取并记录累计区间。

**核验与限制**：匿名目录可读；这是开放参数子集，历史保存和额外配送服务分别核对。

**证据层级**：listing_or_metadata（匿名目录或元数据可读，未验证气象值）。

官方说明：[说明1](https://www.ecmwf.int/en/forecasts/datasets/open-data)；[说明2](https://data.ecmwf.int/forecasts/)。

### 42. NOAA / NCEP GFS

<a id="noaa_gfs"></a>

**类别**：数值天气预报；**获取条件**：无需账号的公开路线。

入口：[NOAA / NCEP GFS](https://nomads.ncep.noaa.gov/)。用途：GFS、NOAA、NCEP、天气预报、气温、降水、风、湿度、气压。

1. 在NOMADS选择GFS 0.25 Degree的HTTPS或grib filter。
2. 选择起报日期、时次和预报时效，过滤变量/层次/区域。
3. 下载所需GRIB；不要把滚动预报目录当多年历史库。

**核验与限制**：当前产品目录可匿名读取，未核验每个预报文件；频繁请求须遵守服务限制。

**证据层级**：listing_or_metadata（匿名目录或元数据可读，未验证气象值）。

官方说明：[说明1](https://nomads.ncep.noaa.gov/)；[说明2](https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/)。

### 43. NSF NCAR / GDEX ERA5 分发

<a id="ncar_gdex_era5"></a>

**类别**：公开镜像与云端计算；**获取条件**：无需账号的公开路线。

入口：[NSF NCAR / GDEX ERA5 分发](https://registry.opendata.aws/nsf-ncar-era5/)。用途：ERA5、小时场、区域裁剪、时间边界核对。

1. 从AWS登记页进入公开ERA5存储。
2. 按产品目录选择单层或其他集合，再选变量和月份。
3. 使用文件下载或适合的子集工具；先小样本核对时间与变量语义。

**核验与限制**：公开S3无需AWS账号，匿名对象列表已通过；GDEX/OPeNDAP是另一获取方式，其历史九变量裁剪未通过，不把它写成批量已打通。

**证据层级**：listing_or_metadata（匿名目录或元数据可读，未验证气象值）。

官方说明：[说明1](https://registry.opendata.aws/nsf-ncar-era5/)；[说明2](https://nsf-ncar-era5.s3.us-west-2.amazonaws.com/?list-type=2&max-keys=1)。

### 44. 生态观测网络资源目录与台站资料线索

<a id="cner_station_lead"></a>

**类别**：中国与区域资料；**获取条件**：需实名、申请或站方确认。

入口：[生态观测网络资源目录与台站资料线索](https://www.cnern.org.cn/share_dict.jsp?data=1&type=2)。用途：生态站、林芝、日照气候背景、台站资料申请。

1. 在公开资源目录定位生态站及数据资源。
2. 核对站点、变量、年份及共享方式；目录里的气候背景不等于可下载序列。
3. 开放条目按页面注册获取；具体长期序列需按站方要求申请确认。

**核验与限制**：目录可读，但目标逐日时序下载未确认；保留为资料线索，不作为“普通人已能直接下载”的成果。

**证据层级**：not_download_verified（只找到门户/申请步骤/年份选择器，下载尚未确认）。

官方说明：[说明1](https://www.cnern.org.cn/share_dict.jsp?data=1&type=2)。

## 获取数据后的最小检查

先核对变量、单位、时区与日界、坐标/站号、版本和缺测码，再做分析。再分析、遥感、站点观测、模型同化和未来情景分开标注。下载权、平台计算资格、再分发权和商业用途分别看上游条款。

本项目的MIT许可适用于代码，不会把上游数据改成MIT许可。每位使用者自行完成账号注册和所需授权，不共享维护者账号、Cloud项目、Cookie或令牌。

## 程序和核验记录

- [机器目录](../catalog/sources.json)：44项、获取分组、步骤、官方证据与实现状态。
- [匿名访问核验记录](../catalog/access-checks.json)：有界GET及IMD年份表单POST、结果格式、字节数和前缀哈希；包含失败记录。
- [软件验证状态](status.md)：当前仅提供ERA5 GEE客户端，其他目录条目不等于实现连接器。
- [方法与变量](methods.md)：ERA5客户端的时间、网格、单位和输出约定。

本轮没有使用个人气象账号做认证下载，也没有把私人数据库、研究原始数据、采集原脚本的私人路径或凭据发布到仓库。
