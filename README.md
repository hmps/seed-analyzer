# Seed Analyzer

A tool that measures seeds from photographs. Place seeds on millimeter grid paper, take a photo, and get measurements for each seed including length, width, and shape classification.

## What It Does

- **Detects seeds** automatically from your photo
- **Measures dimensions** in millimeters (using the grid paper for calibration)
- **Classifies shapes** as circular, oval, or elongated
- **Calculates statistics** including min, max, average, and standard deviation
- **Identifies size distribution** (ratio of large to small seeds)

## Requirements

- A computer running **Windows 10 or 11** (also works on Mac/Linux)
- An internet connection (for initial setup only)
- Photos of seeds on **millimeter grid paper**

---

## Setup Instructions (Windows)

### Step 1: Install Python

1. Open your web browser and go to: https://www.python.org/downloads/
2. Click the big yellow **"Download Python 3.x.x"** button
3. Run the downloaded installer
4. **IMPORTANT**: Check the box that says **"Add Python to PATH"** at the bottom of the installer window
5. Click **"Install Now"**
6. Wait for installation to complete, then click "Close"

To verify Python installed correctly:
1. Press `Windows Key + R`
2. Type `cmd` and press Enter
3. In the black window that opens, type: `python --version`
4. You should see something like `Python 3.12.0`

### Step 2: Install UV (Package Manager)

UV is a tool that manages Python packages. To install it:

1. Open Command Prompt (press `Windows Key + R`, type `cmd`, press Enter)
2. Copy and paste this command, then press Enter:
   ```
   pip install uv
   ```
3. Wait for it to finish (you'll see some download progress)

### Step 3: Download and Set Up Seed Analyzer

1. Download this project folder to your computer
2. Open Command Prompt
3. Navigate to the project folder. For example, if you saved it to your Downloads:
   ```
   cd C:\Users\YourName\Downloads\seeds
   ```
   (Replace `YourName` with your actual Windows username)

4. Install the required packages by running:
   ```
   uv sync
   ```
   This will download everything needed (may take a minute or two).

---

## Running the Analyzer

### Starting the Application

1. Open Command Prompt
2. Navigate to the project folder:
   ```
   cd C:\Users\YourName\Downloads\seeds
   ```
3. Start the server:
   ```
   uv run uvicorn seed_analyzer.main:app --host 127.0.0.1 --port 8000
   ```
4. You should see output ending with:
   ```
   Uvicorn running on http://127.0.0.1:8000
   ```

**Leave this window open** - it's running the server.

### Using the Web Interface

1. Open your web browser (Chrome, Firefox, Edge, etc.)
2. Go to: **http://127.0.0.1:8000**
3. You'll see the Seed Analyzer interface
4. Click the upload area or drag-and-drop your seed image
5. Click **"Analyze Seeds"**
6. View your results!

### Stopping the Server

When you're done, go back to the Command Prompt window and press `Ctrl + C` to stop the server.

---

## Preparing Your Images

For best results:

### Grid Paper
- Use standard **millimeter grid paper** (1mm squares)
- The grid lines should be clearly visible
- Light-colored grid paper (white/cream) works best

### Seeds
- Spread seeds so they're **not touching** each other (touching seeds may be counted as one)
- Place seeds **flat** on the paper
- Ensure good contrast between seeds and paper

### Photography
- Take photo from **directly above** (perpendicular to the paper)
- Use **even lighting** (avoid harsh shadows)
- Make sure the image is **in focus**
- Include enough grid squares for accurate calibration (at least 10x10mm visible)

### Supported Image Formats
- JPEG (.jpg, .jpeg)
- PNG (.png)
- WebP (.webp)
- Maximum file size: 20MB

---

## Understanding the Results

### Summary Statistics

| Metric | Description |
|--------|-------------|
| Seeds Detected | Total number of seeds found in the image |
| Avg Length | Average seed length in millimeters |
| Avg Width | Average seed width in millimeters |
| Processing Time | How long the analysis took |

### Shape Classification

Seeds are classified by their **aspect ratio** (length divided by width):

| Shape | Aspect Ratio | Description |
|-------|--------------|-------------|
| Circular | < 1.2 | Nearly round seeds |
| Oval | 1.2 - 1.8 | Moderately elongated |
| Elongated | > 1.8 | Long, narrow seeds |

### Size Ratio

- **Large Seeds**: Top 25% by area
- **Small Seeds**: Bottom 25% by area
- **Ratio**: Number of large seeds divided by small seeds

### Individual Seed Data

The table at the bottom shows measurements for each detected seed:
- **ID**: Seed number
- **Length**: Major axis in mm
- **Width**: Minor axis in mm
- **Aspect Ratio**: Length / Width
- **Shape**: Classification (circular/oval/elongated)
- **Area**: Calculated area in mm�

---

## Troubleshooting

### "Python is not recognized"
- Python wasn't added to PATH during installation
- Reinstall Python and make sure to check "Add Python to PATH"

### "uv is not recognized"
- Close and reopen Command Prompt after installing uv
- Or try: `python -m pip install uv`

### "No seeds detected"
- Check that grid lines are visible in the image
- Ensure seeds contrast with the background
- Try adjusting lighting and retaking the photo

### "Seeds appearing merged" (detected seeds are too large)
- Spread seeds further apart so they don't touch
- The analyzer assumes seeds are no longer than 6mm; clusters larger than this are filtered out

### Server won't start / "Address already in use"
- Another program is using port 8000
- Either close that program, or use a different port:
  ```
  uv run uvicorn seed_analyzer.main:app --host 127.0.0.1 --port 8001
  ```
  Then go to http://127.0.0.1:8001 instead

### Page won't load in browser
- Make sure the server is still running (Command Prompt window should still be open)
- Check that you typed the address correctly: `http://127.0.0.1:8000`
- Try a different browser

---

## Quick Reference Card

**One-time setup** (only do this once):
```
pip install uv
cd C:\path\to\seeds
uv sync
```

**Start the analyzer** (do this each time you want to use it):
```
cd C:\path\to\seeds
uv run uvicorn seed_analyzer.main:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000** in your web browser.

---

## For Mac/Linux Users

The setup is similar, but use Terminal instead of Command Prompt:

```bash
# Install uv
pip3 install uv

# Navigate to project
cd /path/to/seeds

# Install dependencies
uv sync

# Run the server
uv run uvicorn seed_analyzer.main:app --host 127.0.0.1 --port 8000
```

---

## Technical Details

For those interested in how it works:

- **Grid Detection**: Uses Hough Line Transform to detect grid lines and calculate pixels-per-millimeter calibration
- **Seed Segmentation**: Combines Otsu's thresholding with adaptive thresholding; uses watershed algorithm to separate touching seeds
- **Measurement**: Fits ellipses to seed contours to measure major/minor axes
- **Limits**: Maximum individual seed length of 6mm and area of 12mm� (larger objects are assumed to be multiple merged seeds and are either split or filtered out)

---

## License

This software is licensed under the **Polyform Noncommercial License 1.0.0**.

- **Personal use**: Free for personal projects, research, education, and non-commercial purposes
- **Commercial use**: Requires a separate commercial license - contact the author

See the [LICENSE](LICENSE) file for full terms.
