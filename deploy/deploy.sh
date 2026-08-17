#!/usr/bin/env bash
# PersonaCore 一键部署脚本（Ubuntu/Debian）
# 用法：在 ECS 上以 root 运行： bash deploy.sh
set -euo pipefail

APP_DIR=/opt/personacore
REPO=https://github.com/China-sty/PersonaCore.git
PORT=8000

echo "==> 1/6 安装系统依赖（git / python3-venv / nginx）"
apt-get update -y
apt-get install -y git python3 python3-venv python3-pip nginx

echo "==> 2/6 拉取代码"
if [ -d "$APP_DIR/.git" ]; then
  cd "$APP_DIR" && git pull
else
  git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"

echo "==> 3/6 创建虚拟环境并安装依赖"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "==> 4/6 配置 .env（密钥）"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "   ⚠️  请先编辑 $APP_DIR/.env 填入 OPENAI_API_KEY 后再运行部署步骤 5/6"
  echo "       编辑： nano $APP_DIR/.env"
  exit 1
fi
chmod 600 .env

echo "==> 5/6 配置 systemd 服务"
sed "s|__APP_DIR__|$APP_DIR|g" deploy/personacore.service > /etc/systemd/system/personacore.service
systemctl daemon-reload
systemctl enable --now personacore

echo "==> 6/6 配置 nginx 反向代理"
cp deploy/nginx.conf /etc/nginx/sites-available/personacore
ln -sf /etc/nginx/sites-available/personacore /etc/nginx/sites-enabled/personacore
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "✅ 部署完成，访问： http://<你的公网IP>"
echo "   查看服务日志： journalctl -u personacore -f"
echo "   查看状态：     systemctl status personacore"
