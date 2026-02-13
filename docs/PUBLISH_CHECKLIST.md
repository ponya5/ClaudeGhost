# Publishing Checklist

Before pushing ClaudeGhost to GitHub, complete these steps:

## Pre-Push Checklist

### 1. Update GitHub Username
- [ ] Replace `yourusername` in `README.md`
- [ ] Replace `yourusername` in `MANUAL.md`
- [ ] Replace `yourusername` in `INSTALL.md`
- [ ] Replace `yourusername` in `setup.py`
- [ ] Replace `yourusername` in `docs/NEW_USER_GUIDE.md`
- [ ] Replace `yourusername` in `docs/GITHUB_SETUP.md`

Quick command (PowerShell):
```powershell
$files = Get-ChildItem -Recurse -Include *.md,*.py
foreach ($file in $files) {
    (Get-Content $file.FullName) -replace 'yourusername', 'YOUR_GITHUB_USERNAME' | Set-Content $file.FullName
}
```

### 2. Verify Tests Pass
- [ ] Run `python tests/run_all_tests.py`
- [ ] All 33 tests should pass
- [ ] No errors or warnings

### 3. Clean Repository
- [ ] Remove any `.pyc` files: `Get-ChildItem -Recurse -Filter *.pyc | Remove-Item`
- [ ] Remove `__pycache__` directories: `Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force`
- [ ] Check `.gitignore` is complete

### 4. Documentation Review
- [ ] README.md displays correctly
- [ ] INSTALL.md has clear instructions
- [ ] MANUAL.md is comprehensive
- [ ] All links work (no broken references)

### 5. Configuration Files
- [ ] `.env.example` has all required fields
- [ ] `config.yaml` has sensible defaults
- [ ] `requirements.txt` is up to date

## GitHub Setup

### 1. Create Repository
- [ ] Go to https://github.com/new
- [ ] Name: `ClaudeGhost`
- [ ] Description: `Headless Supervisor for Anthropic Claude CLI with Telegram notifications`
- [ ] Choose Public/Private
- [ ] Don't initialize with README

### 2. Push Code
```bash
git init
git add .
git commit -m "Initial commit: ClaudeGhost v2.0.0 with Telegram Bot API"
git remote add origin https://github.com/YOUR_USERNAME/ClaudeGhost.git
git branch -M main
git push -u origin main
```

### 3. Configure Repository
- [ ] Add topics: `python`, `claude`, `ai`, `telegram`, `automation`, `cli`
- [ ] Enable GitHub Actions (Settings → Actions)
- [ ] Add repository description
- [ ] Add website URL (if applicable)

### 4. Verify GitHub Actions
- [ ] Go to Actions tab
- [ ] Check that tests workflow runs
- [ ] Verify tests pass on all platforms (Windows, macOS, Linux)

## Post-Push Checklist

### 1. Test Installation
```bash
cd /tmp
git clone https://github.com/YOUR_USERNAME/ClaudeGhost.git
cd ClaudeGhost
pip install -r requirements.txt
python tests/run_all_tests.py
```

### 2. Update Badge URLs
- [ ] Update badge URLs in README.md with your username
- [ ] Verify badges display correctly on GitHub

### 3. Create Release (Optional)
- [ ] Go to Releases → Create new release
- [ ] Tag: `v2.0.0`
- [ ] Title: `ClaudeGhost v2.0.0 - Telegram Bot API`
- [ ] Description: Release notes
- [ ] Publish release

## New User Instructions

After publishing, new users can install with:

```bash
git clone https://github.com/YOUR_USERNAME/ClaudeGhost.git
cd ClaudeGhost
pip install -r requirements.txt
python setup_interactive.py
```

## Future: PyPI Publishing

When ready to publish to PyPI:

1. Update `setup.py` with final metadata
2. Build distribution: `python setup.py sdist bdist_wheel`
3. Upload to PyPI: `twine upload dist/*`
4. Test installation: `pip install claudeghost`

---

## Quick Commands Reference

### Clean pycache
```powershell
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter *.pyc | Remove-Item
```

### Run tests
```bash
python tests/run_all_tests.py
```

### Replace username
```powershell
$files = Get-ChildItem -Recurse -Include *.md,*.py
foreach ($file in $files) {
    (Get-Content $file.FullName) -replace 'yourusername', 'YOUR_GITHUB_USERNAME' | Set-Content $file.FullName
}
```

### Git commands
```bash
git status
git add .
git commit -m "Your message"
git push
```
