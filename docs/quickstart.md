# Quickstart

This page walks through the most common workflow: opening image stacks, tracing a neuron across time, and saving your work.

## 1. Launch

After installation, start pyDynamo from the command line:

```bash
pydynamo_brain
```

Or open an existing project directly:

```bash
pydynamo_brain path/to/my/file.dyn.gz
```

Two windows will appear: a logo/control window (keep this open until you're done) and the project window.

## 2. Start a new project

From the project window, choose **New from Stacks** (`Ctrl-N`) and select one or more `.tif` image files. Each file is a single timepoint volume.

To reopen an existing project, use **Open from File** (`Ctrl-O`) and select a `.dyn.gz` file.

## 3. Trace the first timepoint

In the stack view:

1. **Click** anywhere to place the first point — this should be the soma.
2. **Click** into empty space to extend the current branch.
3. Use the **scroll wheel** (or keys `1`/`2`) to move through Z-slices.
4. **Right-click** (or `Ctrl`+click) on an existing point to start a new branch from it.
5. **Middle-click** (or `Shift`+click) on an existing point to insert a point mid-branch.

Press `Ctrl-S` to save. The file will auto-save after the first manual save.

## 4. Move to the next timepoint

Load the next stack via the stack list. Then either:
- Press `I` to import the previous timepoint's tracing as a starting point.
- Draw from scratch.

Adjust points to match the new image, then press `R` on a point to auto-register it and all downstream points to their positions in the new stack.

## 5. Key shortcuts

| Key | Action |
|-----|--------|
| `1` / `2` | Move Z-slice down / up |
| `W` `A` `S` `D` | Pan the image |
| `X` / `Z` | Zoom in / out |
| `R` | Auto-register selected point and subtree |
| `P` | Toggle puncta mode |
| `F` | Cycle annotations / IDs / none |
| `T` | Tile all visible stacks |
| `F1` | Open full help dialog |
| `Ctrl-S` | Save |
| `Ctrl-Z` | Undo |

See the {doc}`drawing` and {doc}`registration` pages for more detail.
