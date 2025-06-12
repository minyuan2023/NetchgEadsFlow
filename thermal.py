#!/public23/home/a21000011/conda_envs/pymatgen_env/bin/python

import sys
import os
from pymatgen.analysis.adsorption import AdsorbateSiteFinder
from pymatgen.core import Molecule, Structure
from pymatgen.io.vasp import Poscar
import warnings

warnings.simplefilter("ignore")

# 定义变量
support_name = sys.argv[1]     # 催化剂名称，例如 Fe, FePc, Fe2O3, Fe-MOF 等催化剂
adsorbate_name = sys.argv[2]   # 吸附物名称，例如 OOH, OH, CO2, N2, SO4, benzene 等吸附物
site_index = int(sys.argv[3])  # 位点编号，转换为整数类型

# Step 1: 读取优化好的催化剂
support_path = os.path.join('.', support_name, 'CONTCAR')
structure = Structure.from_file(support_path)

# Step 2: 读取目标的吸附物
ads_path = os.path.expanduser(os.path.join('.', adsorbate_name + '.xyz'))
ads_name = Molecule.from_file(ads_path)

# Step 3: 催化剂-吸附物的热力学计算路径定义
input_contcar_path = os.path.join('..', adsorbate_name, support_name, "CONTCAR")
output_poscar_path = os.path.join('..', adsorbate_name, '2-thermal', support_name, "POSCAR")

# Step 4: 获取催化剂表面位置并将吸附物添加到表面结构
site_coords = structure[site_index].coords
ads_coords = [site_coords[0], site_coords[1], site_coords[2] + 2.4]  # above the site
structure = AdsorbateSiteFinder(structure).add_adsorbate(ads_name, ads_coords)
structure = structure.get_sorted_structure()

# Step 5: 获取催化剂和吸附物的组别
group = structure.site_properties["surface_properties"]

# Step 6: 按照组别分配 F 与 T 的信息，定义 selective_dynamics
selective_dynamics = []
for i, site in enumerate(structure):
    # 根据组别设置 selective_dynamics 信息
    if group[i] == "surface":
        selective_dynamics.append([False, False, False])  # 表面原子不动
    elif group[i] == "subsurface":
        selective_dynamics.append([False, False, False])  # 次表面原子也不动
    elif group[i] == "adsorbate":
        selective_dynamics.append([True, True, True])     # 吸附物原子可以自由优化
    else:
        # 对于其他的组别，默认分配为不动，可以根据需要修改
        selective_dynamics.append([False, False, False])

# 添加 `selective_dynamics` 信息到结构中
structure.add_site_property("selective_dynamics", selective_dynamics)

print(f"Number of sites in structure: {len(structure)}")
print(f"Length of selective_dynamics: {len(selective_dynamics)}")

# 创建包含 selective_dynamics 的 POSCAR 对象
poscar = Poscar(structure)

# Step 7: 读取催化剂-吸附物的原始 CONTCAR 文件
contcar_structure = Structure.from_file(input_contcar_path)

# Step 8: 移除 CONTCAR 中已有的 selective_dynamics（如果存在）
if "selective_dynamics" in contcar_structure.site_properties:
    del contcar_structure.site_properties["selective_dynamics"]

# Step 9: 检查 POSCAR 和 CONTCAR 中的原子数量是否一致
if len(poscar.structure) != len(contcar_structure):
    raise ValueError("The number of atoms in POSCAR and CONTCAR does not match.")

# Step 10: 将新的 selective_dynamics 信息添加到 CONTCAR 结构中
contcar_structure.add_site_property("selective_dynamics", selective_dynamics)

# Step 11: 写出更新后的 CONTCAR 文件
new_poscar = Poscar(contcar_structure)
new_poscar.write_file(output_poscar_path)

print(f"Updated CONTCAR with new selective dynamics!")


