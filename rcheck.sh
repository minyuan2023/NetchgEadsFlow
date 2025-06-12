#!/bin/sh
[ -d 1-contcar ] || mkdir 1-contcar
dir=$1
if [ -d "$dir" ]; then
cd "$dir" || { echo "Error: directory $dir does not exist"; exit 1; }
if grep -q 'required accuracy' OUTCAR && grep -q 'Total CPU time' OUTCAR; then
cp -r CONTCAR ../1-contcar/CONTCAR-$dir
echo "Success: $dir" || echo "Error: failed to copy files for $dir"
cd ..
else
  echo "Error: pattern not found in OUTCAR for $dir"
  cd ..
fi 
fi
