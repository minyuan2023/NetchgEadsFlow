#!/bin/sh
# Define function
function Edft() {
if [ -n "$1" ]; then
    result=$(grep '  without' OUTCAR | tail -n 1 | awk '{print $7}')
    echo -e "$1\t$result" >> ../Edft.txt
fi
}

# get E from relax files
if [ "$(basename "$PWD")" = "2-thermal" ]; then
    echo "Please exit from 2-thermal, and go to the relax directory!"
    exit 0
elif [ -d "$PWD/$1" ]; then
    # 添加检查OUTCAR文件是否存在的条件
    if [ -f "$PWD/$1/OUTCAR" ]; then
        cd "$PWD/$1"
        Edft $1
        cd -
    else
        echo "OUTCAR file not found in: $PWD/$1, skipping..."
    fi
else
    echo "No such file: $1"
fi

if [ -f Edft.txt ]; then
    tac Edft.txt | awk '!seen[$1]++' | tac > Etemp.txt && mv Etemp.txt Edft.txt
    echo -e "*******\n"
    cat Edft.txt
    echo -e "*******\n"
fi
