#!/public23/home/a21000011/conda_envs/pymatgen_env/bin/python
import warnings
import numpy as np
import sys
import os
from pymatgen.analysis.adsorption import AdsorbateSiteFinder
from pymatgen.io.vasp import Poscar
from pymatgen.core import Lattice, Molecule, Structure
from pymatgen.core.surface import generate_all_slabs
from pymatgen.ext.matproj import MPRester
from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen.io.vasp.sets import MITRelaxSet
from pymatgen.io.vasp.sets import MPNonSCFSet
from pymatgen.io.vasp.inputs import Kpoints

warnings.simplefilter("ignore")

# 定义变量
support_name = sys.argv[1]
#support_path = os.path.join('.', support_name, 'POSCAR')
support_path = os.path.join('.', sys.argv[1] + '.cif')
structure = Structure.from_file(support_path)

# 保存路径
relax_path = os.path.join('.', support_name)

# 接收命令行传递的变量
if len(sys.argv) > 2:
    num_top_layers = int(sys.argv[2])  # 传递的 top 层数
else:
    num_top_layers = 3  # 默认值为 3

# 读取笛卡尔坐标
cart_coords = structure.cart_coords
z_coords = cart_coords[:, 2]

# 将 z 坐标进行分层
eps = 0.5  # 阈值：两个原子属于同一层的最大距离
labels = np.full(len(z_coords), -1, dtype=int)
current_label = 0

for i in range(len(z_coords)):
    if labels[i] == -1:  # 如果尚未被标签
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
print(f"Total number of layers in the z direction: {num_layers}\n")

# 打印每一层的原子信息
for layer_index, layer in enumerate(layers):
    print(f"Layer {layer_index + 1}:")
    for index in layer:
        atom = structure.sites[index]
        print(f"  Atom Index: {index}, Element: {atom.species_string}, Z-Coordinate: {z_coords[index]:.3f}")
    print()

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

# 由所标记的标签，设置原子是否为T或F
group = structure.site_properties["surface_properties"]
selective_dynamics = []
for i, site in enumerate(structure):
    # 根据组别设置 selective_dynamics 信息
    if group[i] == "surface":
        selective_dynamics.append([True, True, True])  # 表面原子动
    elif group[i] == "subsurface":
        selective_dynamics.append([False, False, False])  # 次表面原子不动
    else:
        # 对于其他的组别，默认为不动
        selective_dynamics.append([False, False, False])

# 添加 `selective_dynamics` 信息
structure.add_site_property("selective_dynamics", selective_dynamics)

print(f"Total number of layers in the z direction: {num_layers}\n")

# 生成 vasp 输入文件
#kpoints_set = {'reciprocal_density':100}
kpoints_set = Kpoints.gamma_automatic([1, 1, 1])
incar_set = { 'ALGO':"Normal", 'EDIFFG':-0.02,'EDIFF':0.00001, 'ENCUT':400, 'ISMEAR':0, 'ISPIN':2, 'ICHARG':2, 'NSW':400,'LCHARG':False, 'LWAVE':False,
         'PREC':'Normal', 'NCORE':4, 'ISIF':1, 'NELM':200, 'LDAU': False}
#Relax = MPRelaxSet(structure, user_incar_settings=incar_set, user_kpoints_settings=kpoints_set)
Relax = MITRelaxSet(structure, user_incar_settings=incar_set, user_kpoints_settings=kpoints_set)
Relax.write_input(relax_path)
