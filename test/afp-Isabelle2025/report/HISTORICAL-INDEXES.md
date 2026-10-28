# 历史索引与保留边界

保留的是 2026-10-28 的报告快照。数字、CSV 和原机器统计没有重算或改写。`report-audit.json`、`mechanism-evidence.json` 等原审计与摘要只描述当时核验，不能证明清理后的全量证据仍存在。

| 文件 | 现在的用途 |
| --- | --- |
| candidates.csv、declarations-published.csv、failed-candidates.csv | 历史候选结论；原 witness 路径为历史引用 |
| candidate-witnesses.jsonl、evidence-files.jsonl、successful-artifacts.csv | 历史证据及产物索引；未列入精选清单的导出/编译文件已清理 |
| failures.jsonl、entries.csv、summary.json、分类 CSV | 保留的原报告正文、条目与统计；正文里的原路径仍是历史引用 |
| report-audit.json、residual-category-review.json、unclassified-examples.json、mechanism-evidence.json | 当时的审计与分类过程记录，未经本次重新认证 |
| selected-evidence.jsonl | 本次逐文件核验的精选证据：原路径、新路径、SHA256、字节数与用途 |

全量导出证据已清理，无法逐项重新核验。正文四页的本地链接均已迁到保留文件；历史 CSV/JSON 内原路径保留原字节，不制作指向已删除文件的超链接。精选范围以四页正文详析案例为限，没有保留全部成功产物。完整冻结扫描另位于 `../scan/`，其内容未改写。

[精选证据清单](selected-evidence.jsonl) 与 [迁移前报告文件摘要](../setup/report-original-files.json) 用于核对保留范围。可从 AFP 主目录执行 `python3 tools/afp.py verify-report` 检查精选证据、正文链接与原表格摘要；该命令不会宣称完成全量导出审计。查询旧路径用 `python3 tools/afp.py path '历史路径'`。
