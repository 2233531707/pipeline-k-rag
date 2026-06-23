# Domain Docs

本文件说明工程类 skills 在探索代码库时应如何读取本仓库的领域文档。

## 布局

本仓库使用 single-context 领域文档布局。

预期位置：

- 仓库根目录的 `CONTEXT.md`
- `docs/adr/` 中的架构决策记录

如果这些文件不存在，静默继续即可。不要预先建议创建它们。生产者 skill（`/grill-with-docs`）会在术语或决策真正明确后按需创建。

## 探索前先阅读

- 如果存在，阅读 `CONTEXT.md`
- 如果存在，阅读 `docs/adr/` 下与当前工作相关的 ADR

## 使用 glossary 中的词汇

当输出中需要命名领域概念时，使用 `CONTEXT.md` 中定义的术语。

如果需要的概念还不在 glossary 中，要么重新考虑措辞，要么把这个缺口记录给 `/grill-with-docs`。

## 标出 ADR 冲突

如果输出与已有 ADR 冲突，明确指出，不要静默覆盖。
