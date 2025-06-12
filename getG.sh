#!/bin/sh

# Define function
function calculate_G() {
    echo -e "501\n298.15\n" | vaspkit > Gcorr.txt
    echo -ne $1"\t"`grep -a 'to G(T)' Gcorr.txt | tail -n 1 | awk '{print $7}'`"\n" >> ../Gcorr.txt
}

# get G from thermal files
thermal=$(basename "$PWD")
if [ "$thermal" == "2-thermal" ]; then
    if [ -d "$PWD/$1" ]; then
        # 添加检查OUTCAR文件是否存在的条件
        if [ -f "$PWD/$1/OUTCAR" ]; then
            cd "$PWD/$1"
            calculate_G $1
            cd -
        else
            echo "OUTCAR file not found in: $PWD/$1, skipping..."
            exit 0
        fi
    else
        echo "No such directory: $thermal/$1"
        exit 0
    fi
else
    echo "Please change to 2-thermal directory first!"
fi

if [ -f Gcorr.txt ]; then
    tac Gcorr.txt | awk '!seen[$1]++' | tac > Gtemp.txt && mv Gtemp.txt Gcorr.txt
    cat Gcorr.txt
    echo '*******'
fi
