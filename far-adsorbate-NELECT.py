import numpy as np
import sys
import os
import subprocess
from pymatgen.analysis.adsorption import AdsorbateSiteFinder
from pymatgen.io.vasp import Poscar
from pymatgen.core import Lattice, Molecule, Structure
from pymatgen.core.surface import generate_all_slabs
from pymatgen.ext.matproj import MPRester
from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen.io.vasp.sets import MITRelaxSet
from pymatgen.io.vasp.sets import MPNonSCFSet
from pymatgen.io.vasp.inputs import Kpoints
import warnings

warnings.simplefilter("ignore")

# 添加父目录到 sys.path 以导入 calculate_nelect 模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# 定义变量
support_name = sys.argv[1]     # 催化剂名称，例如 Fe, FePc, Fe2O3, Fe-MOF 等催化剂
adsorbate_name = sys.argv[2]   # 吸附物名称，例如 OOH, OH, CO2, N2, SO4, benzene 等吸附物
net_charge = int(sys.argv[3])  #净电荷
num_top_layers = int(sys.argv[4]) # 打算放开催化剂的top 原子层数
site_index = int(sys.argv[5])  # 位点编号，转换为整数类型


# Step 1: 读取优化好的催化剂
support_path = os.path.join('.', support_name, 'CONTCAR')
structure = Structure.from_file(support_path)

# Step 2: 读取目标的吸附物
ads_path = os.path.expanduser(os.path.join('.', adsorbate_name + '.xyz'))
ads_name = Molecule.from_file(ads_path)

# Step 3: 催化剂-吸附物的保存路径
relax_path = os.path.join('..', adsorbate_name, 'far-' +support_name)

# 读取笛卡尔坐标
cart_coords = structure.cart_coords
z_coords = cart_coords[:, 2]

# 将 z 坐标进行分层
eps = 0.5  # 阈值：两个原子属于同一层的最大距离
labels = np.full(len(z_coords), -1, dtype=int)
current_label = 0

for i in range(len(z_coords)):
    if labels[i] == -1:
        labels[i] = current_label
        for j in range(i + 1, len(z_coords)):
            if labels[j] == -1 and abs(z_coords[i] - z_coords[j]) <= eps:
                labels[j] = current_label
        current_label += 1

layers = []
for label in np.unique(labels):
    layer_indices = np.where(labels == label)[0]
    layers.append(layer_indices)

# z坐标从大到小排序，例如 top 层应对 layer 1
layers = sorted(layers, key=lambda layer: np.mean(z_coords[layer]), reverse=True)
num_layers = len(layers)

# 分层并标记 surface与subsurface
if num_layers <= num_top_layers:
    top_layers = layers[:num_layers]
    bottom_layers = []
else:
    top_layers = layers[:num_top_layers]
    bottom_layers = layers[num_top_layers:]

surface_properties = ["subsurface"] * len(structure.sites)

for layer in top_layers:
    for index in layer:
        surface_properties[index] = "surface"

structure.add_site_property("surface_properties", surface_properties)

# 读取基底上的吸附位点，读取吸附物信息
site_coords = structure[site_index].coords
ads_position = ads_name[0].coords

# 将吸附物平移到原点 (0, 0, 0)
translation_to_origin = -np.array(ads_position)
ads_name.translate_sites(indices=list(range(len(ads_name))), vector=translation_to_origin)
print(f" ads_atom {ads_name[0].specie}, {ads_name[0].coords}")

# 设置吸附距离，例如 2.4 Å
adsorption_distance = 10
adjusted_coords = [site_coords[0], site_coords[1], site_coords[2] + 10]
translation_vector = adjusted_coords

# 将吸附物平移到目标位置
ads_name.translate_sites(indices=list(range(len(ads_name))), vector=translation_vector)
print(f" ads_atom {ads_name[0].specie}, {ads_name[0].coords}")
print(f" site_atom {structure[site_index].specie}: {site_coords}\n")

# 将吸附物的原子逐个添加到基底上，标记为 `adsorbate`
for site in ads_name:
    structure.append(
        site.specie,
        site.coords,
        coords_are_cartesian=True,
        properties={"surface_properties": "adsorbate"}
    )

structure = structure.get_sorted_structure()

selective_dynamics = []

# 由所标记的标签，设置原子是否为T或F
group = structure.site_properties["surface_properties"]
for i, site in enumerate(structure):
    if group[i] == "surface":
        selective_dynamics.append([True, True, True])  # 表面原子动
    elif group[i] == "subsurface":
        selective_dynamics.append([False, False, False])  # 次表面原子不动
    elif group[i] == "adsorbate":
        selective_dynamics.append([True, True, True])     # 吸附物原子动
    else:
        # 对于其他的组别，默认为不动
        selective_dynamics.append([False, False, False])

# 添加 `selective_dynamics` 信息
structure.add_site_property("selective_dynamics", selective_dynamics)

# 生成 vasp 输入文件
#kpoints_set = {'reciprocal_density':100}
kpoints_set = Kpoints.gamma_automatic([1, 1, 1])
incar_set = { 'ALGO':"Normal", 'EDIFFG':-0.02,'EDIFF':0.00001, 'ENCUT':400, 'ISMEAR':0, 'ISPIN':2, 'ICHARG':2, 'NSW':400,'LCHARG':False, 'LWAVE':False,
         'PREC':'Normal', 'NCORE':4, 'ISIF':1, 'NELM':200, 'LDAU': False}
#Relax = MPRelaxSet(structure, user_incar_settings=incar_set, user_kpoints_settings=kpoints_set)
Relax = MITRelaxSet(structure, user_incar_settings=incar_set, user_kpoints_settings=kpoints_set)
Relax.write_input(relax_path)

# ** 使用 subprocess 调用外部脚本以计算并更新 NELECT **

# 生成POSCAR和POTCAR的路径
potcar_path = os.path.join('..', adsorbate_name, 'far-' +support_name, 'POTCAR')
poscar_path = os.path.join('..', adsorbate_name, 'far-' +support_name, 'POSCAR')
incar_path = os.path.join('..', adsorbate_name, 'far-' +support_name, 'INCAR')
# 计算 NELECT 参数并写入到 INCAR

script_path = os.path.join('NELECT.py')

try:
    subprocess.run(['python', script_path, support_name, adsorbate_name, str(net_charge)], check=True)
except subprocess.CalledProcessError as e:
    print(f"Error occurred: {e}")

