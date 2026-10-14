# Chimni for VS Code

Syntax highlighting for [Chimni](https://github.com/prat8897/chimni) (`.chimni` files): signatures, sources,
every cell operator, fields, settings, ties and comments. `Cmd/Ctrl + /` toggles `--` comments.

## Install from this folder

```bash
cp -r editors/vscode ~/.vscode/extensions/chimni-0.1.0     # then reload VS Code
```

or package it with `npx @vscode/vsce package` and install the `.vsix` with *Extensions → … → Install from VSIX*.

To keep columns lined up, run `chimni fmt -w file.chimni`.
