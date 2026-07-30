# 上市公司年度报告采集与章节定位

输入公司清单和会计年度，批量检索年度报告，选择当前版本并校验 PDF。下载后的文件可继续定位常见章节。处理记录以 JSONL 保存，可导入数据库或文本分析流程。

项目目前内置巨潮资讯网适配器，适用于 A 股年度报告。检索、标题分类、版本选择、文件校验和章节定位分别实现，便于单独使用或替换数据来源。

## 主要功能

- 按证券代码检索指定会计年度的年度报告
- 区分完整报告、摘要、英文版、H 股版和说明公告
- 识别原版、修订版、更正版和更新版
- 将同日无法区分的多份正文标记为 `ambiguous`
- 保存公告编号、发布日期、详情页、文件地址和来源返回信息
- 检查 PDF 文件头、大小和可读页数，并计算 SHA-256
- 使用临时文件和原子替换写入下载结果
- 定位“业务概要”“核心竞争力”“研发投入”等章节标题
- 以 JSONL 保存逐家公司处理记录

## 安装

```bash
git clone https://github.com/ykkai-w/Disclosure-Evidence-Pipeline.git
cd Disclosure-Evidence-Pipeline
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
pytest
```

## 快速开始

示例公司清单位于 `examples/companies.csv`。字段可以使用 `code,name`，也可以使用 `证券代码,证券简称`。

检索公告并保存处理记录：

```bash
disclosure-pipeline collect \
  --source cninfo \
  --input examples/companies.csv \
  --year 2025 \
  --output outputs/2025 \
  --no-download
```

检索并下载通过校验的 PDF：

```bash
disclosure-pipeline collect \
  --source cninfo \
  --input examples/companies.csv \
  --year 2025 \
  --output outputs/2025
```

查看一条公告标题的分类结果：

```bash
disclosure-pipeline classify-title "示例公司2025年年度报告（修订版）" --year 2025
```

检查本地 PDF：

```bash
disclosure-pipeline validate-pdf report.pdf --min-bytes 100000
```

定位章节标题：

```bash
disclosure-pipeline locate-sections report.pdf
```

## 输出文件

```text
outputs/2025/
├── documents/          # 通过检查的 PDF
├── raw_responses/      # 查询参数与来源返回记录
├── records.jsonl       # 公告分类、版本选择和文件校验结果
└── run_summary.json    # 运行范围与状态统计
```

`records.jsonl` 每行对应一家发行人。记录中同时保存最终选择、参与判断的公告以及各公告的处理状态。

## 处理流程

```text
公司清单
   │
   ▼
公告检索
   │
   ▼
标题分类
   │
   ▼
版本选择
   │
   ▼
PDF 校验
   │
   ▼
PDF 与 JSONL 记录

本地 PDF
   │
   ▼
章节标题定位
```

`collect` 完成公告检索、版本选择、下载和校验；`locate-sections` 单独读取本地 PDF，返回匹配标题和候选页码。公告标题、地址和日期按来源返回值保存，分类与版本状态由本地规则生成。详细设计见 [docs/design.md](docs/design.md)。

## 来源适配器

新增数据来源需要实现 `DisclosureSource`：

```python
class AnotherSource(DisclosureSource):
    name = "another_source"

    def list_annual_reports(self, issuer_code, issuer_name, fiscal_year):
        ...

    def download(self, announcement):
        ...
```

标题分类、版本选择、PDF 校验和章节定位可独立复用。接入其他市场时，需要根据当地披露制度调整检索范围和标题规则。

## 当前实现

- 内置来源：巨潮资讯网
- 文档类型：A 股年度报告
- 文件格式：可由 `pypdf` 读取的 PDF
- 章节结果：标题、匹配文本和候选页码
- 检索日期：会计年度次年的 1 月 1 日至 12 月 31 日
- 公告状态：`current`、`superseded`、`ambiguous`、`not_candidate`、`cancelled`
- 处理状态：`selected`、`not_found`、`ambiguous`、`downloaded`、`invalid_document`、`error`

延迟披露或跨年补发需要调整来源适配器的检索日期。巨潮接口或字段调整时，应先用少量证券代码核对查询结果。扫描型 PDF 需要先完成 OCR，再进行章节定位。关键引文应返回原文件核对。

## 开发

```bash
pytest
```

测试覆盖公告标题分类、版本选择、PDF 校验、章节定位、来源适配器和批量流程，测试过程不访问网络。

## 许可证

[MIT](LICENSE)

代码与文档采用 MIT 许可证。运行时取得的公告和 PDF 仍按原来源的使用条款处理。
