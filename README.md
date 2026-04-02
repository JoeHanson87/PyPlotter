# PyPlotter – TDMS Viewer

A dark-mode desktop application for opening, viewing, and visually comparing multiple TDMS data files side-by-side on a single overlay plot.

---

## Features

- **Open multiple TDMS files** via *File → Open TDMS File(s)* or `Ctrl+O`
- **Per-channel checkboxes** – select exactly which channels to display
- **Overlay plot** – all selected channels rendered on the same axes for direct visual comparison
- **Automatic colour assignment** – each channel gets a distinct colour; a colour swatch is shown next to each checkbox
- **Time-track support** – uses the TDMS time track when available, otherwise falls back to a sample index
- **Interactive navigation** – pan, zoom, and save via the standard Matplotlib toolbar
- **Dark-mode theme** throughout the UI and the plot canvas
- **Per-file close button** – remove individual files without clearing the entire session

---

## Requirements

| Package | Version |
|---------|---------|
| Python  | ≥ 3.10  |
| nptdms  | ≥ 1.10  |
| matplotlib | ≥ 3.7 |
| numpy   | ≥ 1.24  |
| tkinter | bundled with Python |

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Running the application

```bash
python tdms_viewer.py
```

---

## Usage

1. Click **Open File** in the sidebar (or *File → Open TDMS File(s)*) and select one or more `.tdms` files.
2. Each file's groups and channels appear in the sidebar as labelled checkboxes.
3. Tick any combination of checkboxes; the overlay plot updates instantly.
4. Use the Matplotlib toolbar at the bottom of the plot to zoom, pan, or save the figure.
5. Click **✕** next to a filename to unload that file and remove its channels.
6. Use *View → Select All / Deselect All* to quickly toggle visibility.

---

## Project structure

```
PyPlotter/
├── tdms_viewer.py   # Main application
├── requirements.txt # Python dependencies
└── README.md        # This file
```
