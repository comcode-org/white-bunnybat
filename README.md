# white-bunnybat

This repo contains the [Hackmud](https://hackmud.com/) game font, white-bunnybat.

See [./NOTICE.txt](./NOTICE.txt) for licensing usage info.

## How to contribute

See the [CONTRIBUTING.md](https://github.com/comcode-org/white-bunnybat?tab=contributing-ov-file) doc for details about how to contribute. Some important notes:

- Our [Values](https://github.com/comcode-org/white-bunnybat?tab=contributing-ov-file#values)
- You should [Create an issue](https://github.com/comcode-org/white-bunnybat?tab=contributing-ov-file#creating-issues) first!
- Changes to white-bunnybat are ultimately at the sole discretion of ComCODE.
- To submit changes towards solving an issue, [create a Pull Request](https://github.com/comcode-org/white-bunnybat?tab=contributing-ov-file#creating-pull-requests-prs). You will need to [fork the repo](https://docs.github.com/articles/fork-a-repo) and push your changes to your fork for this.

We use [fontforge](https://fontforge.org/). The font project file is at [white-bunnybat.sfd](./white-bunnybat.sfd). To contribute changes, you simply need to update this file.

You can do this directly using the fontforge GUI (just open the .sfd file, make changes, and save it), or e.g. using [fontforge's python scripting](https://fontforge.org/docs/scripting/python.html).

When using the fontforge GUI, we recommend going to File -> Preferences and setting "SaveEditorState" to "Off". This will reduce noise in the .sfd changes.

To build the release font files, run [./build.sh](./build.sh).

## How to test your changes

We don't know yet! :D

One way to test your changes is by building a .ttf (with [./build.sh](./build.sh)) and then including it in a web page. Be warned, though, that in-game rendering is significantly different from default web rendering. In particular, your characters may look fine on the web, but may overlap in-game.

For now, you will need a ComCODE volunteer to test your changes in-game. This manual testing is expensive, so smaller, simpler diffs are much more likely to be accepted than large or complex ones.

## Prettier linting

We use [prettier](https://prettier.io/) for linting. If you get an error about this, you can:

1. start a codespace on your branch, and then in the terminal in the codespace:
2. run `npx prettier --write .` to fix the lint errors
3. commit and push the changes in the terminal
   ```bash
   git add -u
   git commit -m "Run npx prettier --write ."
   git push
   ```
