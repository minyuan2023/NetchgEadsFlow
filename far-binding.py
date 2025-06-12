import os
import subprocess
import time
import datetime
import sys
import glob
import re
import pandas as pd
import csv
from contextlib import contextmanager


@contextmanager
def change_directory(destination):
    original_dir = os.getcwd()
    try:
        os.chdir(destination)
        yield
    finally:
        os.chdir(original_dir)


# Updated Binding Energy formula: Eads = Eadsorbate - Efar_adsorbate
# Usage: python binding.py sys.argv[1] sys.argv[2]

support_name = sys.argv[1]     # 催化剂名称，例如 Fe, FePc, Fe2O3, Fe-MOF 等催化剂
adsorbate_name = sys.argv[2]   # 吸附物名称，例如 OOH, OH, CO2, N2, SO4, benzene 等吸附物

# 计算 Eadsorbate 的目录位于 ../{adsorbate_name}/{support_name}
adsorbate_dir = os.path.join("..", adsorbate_name, support_name)
# 计算 Efar_adsorbate 的目录位于 ../{adsorbate_name}/far-{support_name}
far_adsorbate_dir = os.path.join("..", adsorbate_name, "far-" + support_name)

# getE 命令保持不变
getE_command = "grep '  without' OUTCAR | tail -n 1 | awk '{print $7}'"

with change_directory(adsorbate_dir):
   Eadsorbate = float(subprocess.check_output(getE_command, shell=True, text=True).strip())

with change_directory(far_adsorbate_dir):
   Efar_adsorbate = float(subprocess.check_output(getE_command, shell=True, text=True).strip())

Eads = Eadsorbate - Efar_adsorbate

# Save
output_file = "Eads.csv"
file_exists = os.path.exists(output_file) and os.path.getsize(output_file) > 0

with open(output_file, mode="a", newline="") as file:
    writer = csv.writer(file)
    if not file_exists:
        writer.writerow(["adsorbate_name", "support_name", "Eadsorbate", "Efar_adsorbate", "Eads"])
    writer.writerow([
        adsorbate_name,
        support_name,
        f"{Eadsorbate:.2f}",
        f"{Efar_adsorbate:.2f}",
        f"{Eads:.2f}"
    ])

print(f"Binding Energy 已保存到 {output_file}")
