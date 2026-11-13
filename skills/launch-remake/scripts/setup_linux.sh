#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg python3-venv python3-pip git jq unzip curl xz-utils fonts-noto fonts-noto-color-emoji fonts-liberation fonts-inter fontconfig >/dev/null
curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor --yes -o /usr/share/keyrings/google-chrome.gpg
echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list >/dev/null
sudo apt-get update -qq
sudo apt-get install -y -qq google-chrome-stable >/dev/null
if ! node -v 2>/dev/null | grep -q '^v22'; then
  V=$(curl -fsSL https://nodejs.org/dist/index.json | python3 -c "import json,sys; print(next(r['version'] for r in json.load(sys.stdin) if r['version'].startswith('v22.')))")
  cd /tmp
  curl -fsSLO "https://nodejs.org/dist/$V/node-$V-linux-x64.tar.xz"
  curl -fsSL "https://nodejs.org/dist/$V/SHASUMS256.txt" | grep "node-$V-linux-x64.tar.xz" | sha256sum -c -
  sudo tar -xJf "node-$V-linux-x64.tar.xz" -C /usr/local --strip-components=1
fi
sudo npm install -g hyperframes@0.9.19 puppeteer-core >/dev/null 2>&1
python3 -m venv ~/venv
~/venv/bin/pip -q install numpy opencv-python-headless
node -v; ffmpeg -version | head -1; google-chrome --version; hyperframes --version
ffmpeg -hide_banner -filters 2>/dev/null | grep drawtext >/dev/null && echo "drawtext ok" || echo "no drawtext: side-by-side labels will be left out"
echo "run capture_page.cjs with NODE_PATH=$(npm root -g)"
