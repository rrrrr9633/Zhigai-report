# 智改数转诊断报告生成 Skill

## 定位

通过授权远程服务生成完整 `.docx` 智改数转诊断报告。

公开分发版 skill 只作为客户端入口；核心 Python 生成脚本和官方 docx 模板应只保存在服务端。

## 唯一生成链路

```text
企业素材
  ↓
AI 提取事实并生成 JSON 数据
  ↓
scripts/run_report.sh
  ↓
scripts/remote_generate.py 上传 JSON 与图片附件
  ↓
server/app.py 校验授权、额度和到期时间
  ↓
服务端 generate_report.py 打开官方模板
  ↓
服务端填充模板并返回 .docx
  ↓
本地保存完整 .docx 文件
```

## 资产边界

### 可分发给用户

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 主 skill 指令 |
| `agents/openai.yaml` | 展示信息 |
| `scripts/run_report.sh` | 统一客户端入口 |
| `scripts/remote_generate.py` | 远程生成客户端 |
| `references/CONSTRAINTS.md` | 内容约束 |
| `references/使用说明.md` | 使用说明 |
| `references/安装教程.md` | 安装教程 |

### 只放服务端

| 文件 | 说明 |
|------|------|
| `server/app.py` | 授权校验与远程生成 API |
| `server/licenses.json` | 真实授权码、到期时间和额度，禁止分发 |
| `scripts/generate_report.py` | 核心模板填充脚本，禁止分发 |
| `assets/智改数转调研表-20260507v1.0.docx` | 官方 docx 模板，禁止分发 |
| `requirements.txt` | 服务端生成依赖 |

## 服务端启动

复制授权样例：

```bash
cp server/licenses.example.json server/licenses.json
```

编辑 `server/licenses.json`，替换授权码、到期时间和额度。

启动服务：

```bash
python3 server/app.py
```

默认监听：

```text
http://127.0.0.1:8787
```

可通过环境变量调整：

```bash
ZHIGAI_SERVER_HOST=0.0.0.0 \
ZHIGAI_SERVER_PORT=8787 \
ZHIGAI_LICENSES_PATH=/secure/path/licenses.json \
ZHIGAI_GENERATOR_PATH=/secure/path/generate_report.py \
ZHIGAI_TEMPLATE_PATH=/secure/path/template.docx \
python3 server/app.py
```

## 客户端运行方式

首次运行可保存远程服务地址和授权码：

```bash
bash ~/.codex/skills/zhigai-report/scripts/run_report.sh \
  --api-base-url https://your-api.example.com \
  --license-key ZHIGAI-TRIAL-CHANGE-ME \
  --data 生成的数据.json \
  --output 企业名称_智改数转报告_日期.docx \
  --save-config
```

后续运行：

```bash
bash ~/.codex/skills/zhigai-report/scripts/run_report.sh \
  --data 生成的数据.json \
  --output 企业名称_智改数转报告_日期.docx
```

## 禁止事项

- 禁止输出 Markdown 正文作为最终报告。
- 禁止用 Markdown 表格替代官方模板内表格。
- 禁止新建空白 Word 再写入正文。
- 禁止要求用户复制粘贴到官方模板。
- 禁止远程授权失败后改用本地生成路线。

## 发布提醒

对外分发时，不要把以下内容打包进去：

```text
assets/
scripts/generate_report.py
server/licenses.json
```

否则用户拿到核心脚本或模板后，就可以绕过远程授权长期使用。