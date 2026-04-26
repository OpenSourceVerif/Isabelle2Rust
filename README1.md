# Isabelle2Rust



## Quick start

```bash
make build TEST_THEORY=get TEST_DIR=Test/get_test 
# isabelle build -v -e -d . Get_Test
make run TEST_THEORY=Max_Test RUST_OUT=tests_targeted/Rust_Out

make test TEST_DIR=tests_targeted TEST_THEORY=Max_Test


```

| 选项             | 含义                                                         |
| ---------------- | ------------------------------------------------------------ |
| `isabelle build` | 构建指定的 Isabelle session                                  |
| `-v`             | verbose（详细）模式，打印更多构建过程中的信息                |
| `-e`             | execute，即执行理论文件中的 ML 代码（如 `ML ‹...›` 块）      |
| `-d .`           | 使用当前目录作为 session 目录，查找 `ROOT`, `ROOTS`, `.thy`, `.ML` 文件 |
| `Get_Test`       | 指定构建的 session 名称，在 `ROOT` 文件中定义                |

## Code Submission with `git cz` (replace `git commit`)

see [commitizen.md](commitizen.md)

### Configuration

This project is already configured for Commitizen in `package.json`:

```json
"scripts": {
  "cz": "git-cz"
},
"devDependencies": {
  "commitizen": "^4.3.1",
  "cz-conventional-changelog": "^3.3.0"
},
"config": {
  "commitizen": {
    "path": "./node_modules/cz-conventional-changelog"
  }
}
```

- `scripts.cz`: run `npm run cz` as a shortcut
- `cz-conventional-changelog`: adapter for Conventional Commits
- `config.commitizen.path`: tells Commitizen which adapter to use

