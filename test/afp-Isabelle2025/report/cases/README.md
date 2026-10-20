# 本轮案例证据

完整分析见 [实验报告](../README.md)。本目录中的原始理论和生成 Rust 均保留实际字节；文件来源与原理论 SHA256 见各条目的 source.json。

| 条目 | 案例用途 | 原始理论 | 实际 Rust 产物 |
| --- | --- | --- | --- |
| [List-Index](List-Index/) | 候选、导出、编译正例 | [original/](List-Index/original/) | [优化前](List-Index/rust-before/export1/)、[优化后](List-Index/rust-after/export1/) |
| [Example-Submission](Example-Submission/) | 完整扫描后无候选 | [original/](Example-Submission/original/) | 未请求导出，无 Rust |
| [AVL-Trees](AVL-Trees/) | 候选通过，导出失败 | [original/](AVL-Trees/original/) | 导出未完成，无 Rust |
| [Approximation_Algorithms](Approximation_Algorithms/) | 导出成功，编译失败 | [original/](Approximation_Algorithms/original/) | [优化前](Approximation_Algorithms/rust-before/export1/)，未执行优化 |
| [Posix-Lexing](Posix-Lexing/) | 内存限制导致扫描不完整 | [original/](Posix-Lexing/original/) | 后续被阻塞，无 Rust |

每个条目另附 scope.json（主 exports.json 中的范围）、result.json（主 results.json 中的阶段记录）、export/（生成的显式导出理论）、logs/（本轮完整命令日志的 .txt 副本），以及成功扫描时的 scan/ 原始 XML。Rust 目录保存 Cargo.toml、Cargo.lock 及完整源码，不含 target 或可执行文件。

原 AFP 文件使用上游许可证 [AFP-LICENSE](AFP-LICENSE)，作者与维护者注释保留。运行这些原理论仍需实验报告指定的完整 AFP 和项目版本；编译保留的 Rust crate 的命令见报告末尾。
