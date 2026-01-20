# white-bunnybat

This repo contains the [Hackmud](https://hackmud.com/) game font, white-bunnybat.

## How to contribute (WIP WIP WIP)

We use [fontforge](https://fontforge.org/). The font project file is at [white-bunnybat.sfd](./white-bunnybat.sfd). To contribute changes, you simply need to update this file.

You can do this directly using the fontforge GUI (just open the .sfd file, make changes, and save it), or you can use fontforge's python scripting.

In particular: if you have a .ttf containing some glyphs you want (and have the right...) to merge into white-bunnybat, you can use the [merge_gylphs.py](./merge_glyphs.py) script, for example:

```bash
./merge_glyphs.py braille.ttf U+2800..U+28FF
```

The repo has a devcontainer configuration with fontforge installed (no GUI), so these Python scripts can be run in a GitHub codespace.

## Testing

TODO add scripts to generate test .html files and in-game scripts from defined glyph ranges?

game testing will have to be done by volunteer who can load font into dev client?

TODO figure out TextMeshPro steps (document here or in hackmudclient?)
