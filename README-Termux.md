# TermuxCodeScan

## Termux installation

```bash
pkg update -y && pkg upgrade -y
pkg install -y python git
```

Clone the GitHub repository, then enter its folder:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
cd YOUR_REPOSITORY
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the script:

```bash
python TermuxCodeScan.py
```

## If pip reports an externally-managed-environment error

```bash
python -m pip install --break-system-packages -r requirements.txt
```

## Important Termux note

`opencv-python` and `ddddocr` may not provide compatible Android/Termux wheels on every device. If installation fails for those packages, use a Debian/Ubuntu environment through `proot-distro` inside Termux, then repeat the same commands there.

Do not commit passwords, API keys, or tokens to GitHub.
