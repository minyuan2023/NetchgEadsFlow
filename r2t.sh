#!/bin/sh

set -e

# Call rcheck.sh to check if CONTCAR exists
rcheck.sh $1
#ls $1

dir="2-thermal/$1"
if [ -f "$dir/OSZICAR" ]; then
echo "Job Running: $dir"
exit 0

elif [ -f "1-contcar/CONTCAR-$1" ]; then
#elif [ -d "$1" ]; then
  if [ -d "$dir" ]; then
    rm -rf "$dir"
  fi
  mkdir -p "$dir"
  cp "$1/"{INCAR,POTCAR,KPOINTS} "$dir"
  cp "$1/CONTCAR" "${dir}/POSCAR"

# edit files for thermal!
cd "$dir"
if [ $? -eq 0 ]; then 
# edit INCAR
 echo "============="$dir"=============="
 sed -i "/IBRION/s/2/5/g" INCAR
 sed -i "/NSW/s/400/10/g" INCAR
# sed -i "/NCORE/d" INCAR
 sed -i '/NFREE/d' INCAR 
 sed -i '/IBRION/a\NFREE = 4' INCAR 
 grep "IBRION" INCAR


cd -

else
echo "No file: $dir" 
fi

else
echo "rcheck.sh failed and cannot build thermal directory for $1"
fi

