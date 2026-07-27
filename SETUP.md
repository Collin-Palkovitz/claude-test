# Setup guide (no dev experience assumed)

Getting this project running on your own computer takes three things: a copy
of the code, Python (the language it's written in), and three commands typed
into a terminal. Once it works, you copy the output and paste it back into
the Claude chat.

## Step 1 — Get the code with GitHub Desktop

GitHub Desktop is a friendly app that handles the "clone the repo" part
visually, no commands needed.

1. Download it from https://desktop.github.com and install it.
2. Sign in with your GitHub account (the one that owns this repository).
3. In the app: **File → Clone Repository**, find `claude-test` in the list,
   and click **Clone**. Remember the folder it saves to.
4. At the top-center of the window there's a **Current Branch** button.
   Click it and select **`claude/crypto-trading-app-plan-ej5ruu`**.
   The name of that branch should now show on the button.

## Step 2 — Install Python

1. Go to https://www.python.org/downloads and download the latest version.
2. Run the installer.
   - **Windows, important:** on the first installer screen, check the box
     that says **"Add python.exe to PATH"** before clicking Install.
   - **Mac:** just click through the installer.

## Step 3 — Open a terminal in the project folder

Back in GitHub Desktop, open the **Repository** menu at the top and choose:

- **Mac:** "Open in Terminal"
- **Windows:** "Open in Command Prompt" (or PowerShell)

A text window opens, already pointed at the right folder. That's the terminal.

## Step 4 — Run the three commands

Type (or paste) these one at a time, pressing Enter after each and letting
each one finish before the next.

**Mac:**

```
python3 -m pip install -r requirements.txt
python3 -m src.main backfill
python3 -m src.main backtest
```

**Windows:**

```
py -m pip install -r requirements.txt
py -m src.main backfill
py -m src.main backtest
```

What each does:

1. Installs the two small libraries the project needs (one-time).
2. Downloads about 20 years of daily prices for the ETF universe
   (takes a minute; needs internet; safe to re-run any time).
3. Runs the backtest and prints the results table.

## Step 5 — Send the results back

1. Select the output text in the terminal with your mouse
   (from the `backtest` line to the end).
2. Copy it — **Mac:** Cmd+C. **Windows:** Ctrl+C usually works; in some
   terminals just right-clicking the selection copies it.
3. Paste it into the Claude chat as a normal message.

## If something goes wrong

Copy whatever error message appeared (the last ~10 lines are the useful
part) and paste it into the chat. Error messages are normal in this work;
they say exactly what's missing and are usually fixed in one step.
