# 霜棱库房多量偏离研究簿

固定训练、校准与测试窗口，用MCD稳健中心/协方差描述四量共变，再以独立校准上尾p给人工补测提供线索。

霜棱档案材料研究所有16位分析员，核对库房固定窗口的温度、相对湿度、颗粒浓度和温度波动。上游 `sl-archive-climate-202611.csv` 是窗口汇总；过去逐列画阈值、遇到极端值后手改中心，再用测试分位解释“正常范围”。三个痛点是忽略共变、训练极端值影响估计、把测试数据参与选择后的结果当成保证。本系统替代联合量研究与归档环节，下游由材料负责人批准独立补测，阅读者下载已批准测试窗口CSV。当前全部为独立合成窗口，不连接真实传感器、不做危险诊断或实时告警。

## 启动

```sh
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
docker compose exec -T backend python -m scripts.seed_demo
```

含中文与空格的目录可启动。前端 http://localhost:18230 ，API文档 http://localhost:19230/docs ，PostgreSQL localhost:17730。恰好frontend/backend/worker/db/redis五服务，均有健康检查；backend/worker等待数据库与Redis、frontend等待backend。Redis持久化任务队列，数据库保存来源、快照与结果，backend/worker共享产物卷存完整结果JSON。Nginx `/api/` 去前缀代理后端，无重复API前缀。

| 角色 | 账号 | 密码 | 典型动作 |
|---|---|---|---|
| admin 材料负责人 | admin@shuangleng.demo | Shuangleng2026! | 六页；研究创建、批注、建议、批准/退回 |
| analyst 联合量研究员 | analyst@shuangleng.demo | Shuangleng2026! | 六页；来源核对、冻结配置、提交研究和补测说明 |
| viewer 补测阅读者 | viewer@shuangleng.demo | Shuangleng2026! | 六页只读；下载获批完成研究CSV |

JWT角色真实在后端执行，阅读者写操作403、研究员审批403、未获批导出403、重复审批409。登录/批注/排队/worker完成/建议与审批写审计；登录IP每分钟最多30次。统一错误中间件与请求校验422 handler分开，校验错误仅返回loc/msg文本，不回显含NaN/Inf的input，防止错误响应自身变成500。`.env`与构建/日志/缓存被忽略；部署时修改JWT_SECRET及Compose内数据库口令。

## 一天的研究剧本

1. 09:00 温砚以研究员登录，打开 `SL-01`“主群 · 独立窗口观察”，核对固定四量与train200/cal150/test100。
2. 09:05 查看温度°C、湿度%RH、颗粒μg/m³、温度波动°C的FeatureSpec次序。四量预定义，不开放按测试结果挑选。
3. 09:10 读取 `SL-02` 训练前20条极端值的稳健对照；另查 `SL-03` 线性退化边界，训练秩亏拒绝运行。
4. 09:15 新建“主群四量固定拆分”，预设alpha=.05、seed2026，support_fraction=.8固定。运行创建时冻结来源、角色、四量、alpha。
5. 09:16 worker真实读取队列，只用train定标并拟合FastMCD，保存raw与重加权支持/中心/协方差，之后固定模型给cal/test评分。
6. 09:20 主群真实HTTP运行的raw支持160、重加权支持191；150条cal构成参照，100条test中2条p≤.05。它们来自真实计算，前端没有这些常数。
7. 09:25 查看所选test的D²、cal≥test计数与上尾p，记录独立窗口补测，不把训练支持当新窗口标签。
8. 10:00 沈棠批准研究归档，秦禾以阅读者下载 `deviation-run-N.csv`。批准的是独立核验计划，不确认危险、条件保证或批量FDR。

## 六页与五实体

联合量总览、来源与严格拆分、稳健拟合配置、偏离与校准证据、人工补测审阅、过程留痕。`ArchiveStudy / ClimateWindow / FeatureSpec / DeviationRun / ReviewNote` 均贯穿表、model、schema、service、route、前端API、store及页面/组件；另有User/Audit。来源数值/角色/特征只读核对，窗口批注可写，历史运行使用冻结快照。

seed三研究各450条，共1350窗口、12个特征定义。每研究固定train200/cal150/test100，窗口编号是稳定身份而非连续时间序列。SL-01四量联合Gaussian主群；SL-02只在train前20条加入极端值，cal/test仍来自同一独立主群；SL-03第四量为前两量线性组合，训练秩亏。种子260/261/262、固定生成R与尺度写在seed脚本，不是实测数据。自然键为email、study code、(study,window code)、(study,feature code/position)、基线运行name；重复seed只补缺失，不覆盖用户批注或已批准建议。`SEED_DEMO=true`启动自动执行，失败只记日志，独立seed命令仍可运行。

共享RunSummary用于首页/结果/审阅；DistancePlot用于首页/结果；另有StudySelector、ScoreECDF、CovarianceMatrix及通用Notice/DataTable/StatusBadge。所有评分、计数、p与校准ECDF在Python计算，SVG只映射后端结果。

## 算法与严格拆分

固定四量按FeatureSpec.position排列，校验窗口身份与编号唯一、split仅train/cal/test且不重叠；每行四量完整、有限、绝对值≤1e9，布尔/复数训练值拒绝。运行不接受自定义features或support_fraction字段。仅train计算均值与总体尺度，先按每列最大差缩放求标准差避免平方溢出。训练至少20条；中心化定标矩阵SVD数值秩不足p、常量特征拒绝。

生产拟合是scikit-learn1.6.1 `MinCovDet(support_fraction=.8, random_state=seed, assume_centered=False)`，使用FastMCD近似搜索、一致性修正与重加权，不声称全枚举全局最优。保存原始raw及最终重加权支持掩码/代码/数量、中心、协方差（训练定标单位及原单位），并保留定标参数与全部训练D²。support_fraction控制raw支持；最终支持数量可以不同；支持仅描述训练拟合，不是新窗口的标签。MCD适用于单峰近对称/椭圆主群，多峰不适用，这与[官方MinCovDet文档](https://scikit-learn.org/stable/modules/generated/sklearn.covariance.MinCovDet.html)的适用范围及raw支持定义一致。

对raw与最终协方差都校验正定及数值条件数，λmin≤p*eps*λmax或条件数>1e10明确失败；本系统评分不用伪逆或补脊静默绕过奇异性。最终拟合中心μ、协方差Σ下：`D²=(x−μ)ᵀΣ⁻¹(x−μ)`，实现Cholesky求解后平方和，无χ²理论阈值。结果矩阵页可切raw/重加权及原单位/训练定标单位；条件数指标指最终重加权模型。

fit函数只接收train，拟合冻结后分别给cal与test评分。校准m条固定，测试上尾：

```text
p(test) = (1 + # {cal D² >= test D²}) / (m + 1)
探索筛选 = p <= 运行前预设alpha
```

含等号，同值保守，最小分辨率1/(m+1)。m150时为1/151；若预设alpha=.05，可达到的边际错误网格界为floor(.05*151)/151=7/151。**固定训练且校准/测试独立可交换**时，这是单个新窗口的边际误报控制，不是每批最多5%、条件保证、FDR、故障概率或危险诊断。训练污染只影响固定评分函数的质量，不授权把测试放回拟合；MCD的主群假设与conformal交换性是不同前提。若反复看test调整特征/alpha，不能仍声称预先约定保证。

结果保存全部150校准分数、100测试D²/p/计数/筛选及200训练分数/支持。单研究最多2000窗口，固定4量；来源为预置三研究。fit_hash覆盖算法/特征定义/训练数值/seed/.8，全输入hash还覆盖全部拆分、cal/test、批注与alpha。自然键排序使输入行序不改结果；改test不改fit或cal但改全输入指纹；改alpha不改评分或p。所有计算在Python worker真实执行。

## 开发与结构

React18.3、ReactRouter7.18.5、TypeScript5.7、Vite6.4.6；Python3.11、FastAPI0.115、SQLAlchemy2、NumPy2.2、SciPy1.15、scikit-learn1.6.1；PostgreSQL16/Redis7/Nginx1.27。

```sh
# backend：先准备PostgreSQL/Redis，设置DATABASE_URL和REDIS_URL
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
# 另开终端在backend启动worker；需可写/artifacts，推荐Compose
python -m src.worker
# 前端从项目根进入frontend，Vite代理/api到localhost:8000
cd ../frontend
npm ci
npm run dev
```

`backend/src/{routes,controllers,services,models,schemas,middlewares,utils,constants,config}` 按来源、MCD、conformal、运行与审阅职责拆分；`backend/scripts/seed_demo.py`；migration为可选索引升级，首次schema由SQLAlchemy metadata建立，非独立全量DDL。`frontend/src/{api,stores,types,components/common,hooks,pages,router,utils,constants}` 为React应用。

.env参数：COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、JWT_SECRET、SEED_DEMO；DATABASE_URL/REDIS_URL由Compose定义。角色枚举在backend/constants/roles与frontend/constants/enums，参与路由鉴权和页面角色显示；运行枚举backend/constants/status与同一前端enums参与worker/StatusBadge；审阅Literal位于backend/schemas/note并在model/service与前端ReviewStatus使用；split Literal位于backend/schemas/window，分析校验与前端SplitRoles保持train/cal/test。

测试脚本、关键JSON/CSV、截图及已知差异在同批 `test-artifacts/gb-0026/TESTING.md`。本项目为单worker研究工具，无来源上传、任务崩溃恢复、多worker去重、真实设备或自动告警。清理仅本题：`docker compose down -v --remove-orphans`。MIT License。
