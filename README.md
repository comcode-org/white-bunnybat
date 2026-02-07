# white-bunnybat

This repo contains the [Hackmud](https://hackmud.com/) game font, white-bunnybat.

## How to contribute (WIP)

See the [CONTRIBUTING.md](https://github.com/comcode-org/white-bunnybat?tab=contributing-ov-file) doc for details about how to contribute. Some important notes:

- Our [Values](https://github.com/comcode-org/white-bunnybat?tab=contributing-ov-file#values)
- You should [Create an issue](https://github.com/comcode-org/white-bunnybat?tab=contributing-ov-file#creating-issues) first!
- Changes to white-bunnybat are ultimately at the sole discretion of ComCODE.
- To submit changes towards solving an issue, [create a Pull Request](https://github.com/comcode-org/white-bunnybat?tab=contributing-ov-file#creating-pull-requests-prs). You will need to [fork the repo](https://docs.github.com/articles/fork-a-repo) and push your changes to your fork for this.

We use [fontforge](https://fontforge.org/). The font project file is at [white-bunnybat.sfd](./white-bunnybat.sfd). To contribute changes, you simply need to update this file.

You can do this directly using the fontforge GUI (just open the .sfd file, make changes, and save it), or e.g. using [fontforge's python scripting](https://fontforge.org/docs/scripting/python.html).

To build the release font files, run [./build.sh](./build.sh).

See [./NOTICE.txt](./NOTICE.txt) for licensing usage info.

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
