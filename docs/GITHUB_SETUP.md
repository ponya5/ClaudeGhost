# Publishing ClaudeGhost to GitHub

Quick guide for pushing your ClaudeGhost project to GitHub.

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `ClaudeGhost`
3. Description: `Headless Supervisor for Anthropic Claude CLI with Telegram notifications`
4. Choose Public or Private
5. Don't initialize with README (we already have one)
6. Click "Create repository"

## Step 2: Update Repository URLs

Replace `yourusername` with your actual GitHub username in these files:

- `README.md` (line 19)
- `MANUAL.md` (line 42)
- `INSTALL.md` (line 12)
- `setup.py` (line 15)

Quick find & replace:
```bash
# On Linux/Mac
find . -type f -name "*.md" -o -name "*.py" | xargs sed -i 's/yourusername/YOUR_GITHUB_USERNAME/g'

# On Windows (PowerShell)
Get-ChildItem -Recurse -Include *.md,*.py | ForEach-Object { (Get-Content $_) -replace 'yourusername', 'YOUR_GITHUB_USERNAME' | Set-Content $_ }
```

## Step 3: Push to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: ClaudeGhost v2.0.0 with Telegram Bot API"

# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/ClaudeGhost.git

# Push
git branch -M main
git push -u origin main
```

## Step 4: Verify

1. Visit your repository: `https://github.com/YOUR_USERNAME/ClaudeGhost`
2. Check that README displays correctly
3. Verify GitHub Actions workflow runs (Actions tab)
4. Test installation from GitHub:

```bash
cd /tmp
git clone https://github.com/YOUR_USERNAME/ClaudeGhost.git
cd ClaudeGhost
pip install -r requirements.txt
python tests/run_all_tests.py
```

## Step 5: Add Topics (Optional)

On your GitHub repository page:
1. Click the gear icon next to "About"
2. Add topics: `python`, `claude`, `ai`, `telegram`, `automation`, `cli`, `supervisor`
3. Save changes

## Step 6: Enable GitHub Actions

1. Go to Settings → Actions → General
2. Enable "Allow all actions and reusable workflows"
3. Save

Now every push will automatically run tests on Windows, macOS, and Linux!

## New User Installation

After pushing to GitHub, new users can install with:

```bash
git clone https://github.com/YOUR_USERNAME/ClaudeGhost.git
cd ClaudeGhost
pip install -r requirements.txt
python setup_interactive.py
```

That's it! Your project is now public and ready for users.
