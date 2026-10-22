# Deepwick for bat

A deep navy syntax theme with Visual Studio 2022's colors, for
[bat](https://github.com/sharkdp/bat). For delta, see
[Deepwick for delta](https://github.com/deepwick/delta).

> Deepwick is an unofficial theme derived from
> [Polywick Blue](https://vscode.polywickstudio.net) by Polywick Studio (MIT).
> Not affiliated with Polywick Studio.

![Deepwick in bat](screenshot.png)

## bat

```sh
mkdir -p "$(bat --config-dir)/themes"
cp Deepwick.tmTheme "$(bat --config-dir)/themes/"
bat cache --build
bat --theme=Deepwick some-file.py
```

To make it the default, add `--theme="Deepwick"` to `$(bat --config-file)`
or set `BAT_THEME=Deepwick`. bat draws italics only when asked, so add
`--italic-text=always` to the same file to get italic comments.

## delta

Deepwick for delta now lives in
[deepwick/delta](https://github.com/deepwick/delta), which is the maintained
copy. This repo keeps `deepwick.gitconfig` so existing includes keep working:

```ini
[include]
    path = /path/to/deepwick.gitconfig
[delta]
    features = deepwick
```

## Notes

- `variable.language` (Python `self`, JavaScript `this`) is Blue, matching
  Visual Studio's keyword color.
- Diff file headers and hunk ranges are Blue.
- Python decorators (`@dataclass`) are Yellow, like functions.

Tested with bat 0.26.1.

## License

MIT. See [LICENSE](LICENSE).
