#!/usr/bin/env bash
# 取回书法字体（容器/CI 里没有时运行一次）。
# 思路：Expo 的 Google Fonts 包里直接打包了 .ttf，用 npm pack 取 tarball 抽出。
set -e
cd "$(dirname "$0")/fonts"
for pkg in ma-shan-zheng zhi-mang-xing long-cang; do
  echo "fetch @expo-google-fonts/$pkg ..."
  tgz=$(npm pack "@expo-google-fonts/$pkg" 2>/dev/null)
  tar xzf "$tgz" && find package -iname '*.ttf' -exec cp {} . \;
  rm -rf package "$tgz"
done
# 黑体保底（系统自带）
cp /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc . 2>/dev/null || true
ls -la *.ttf *.ttc
