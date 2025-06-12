import sys
import os
from pymatgen.io.vasp import Potcar, Poscar

current_dir = os.path.dirname(os.path.abspath(__file__))  # 获取当前脚本的绝对路径
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))  # 获取父目录
if parent_dir not in sys.path:  # 检查父目录是否已在 sys.path 中
    sys.path.append(parent_dir)  # 如果不在 sys.path 中，添加父目录

def calculate_nelect_with_charge(potcar_path, poscar_path, net_charge):
    """
    使用 pymatgen 从 POTCAR 和 POSCAR 文件中计算 NELECT，并考虑净电荷的影响。

    :param potcar_path: POTCAR 文件路径
    :param poscar_path: POSCAR 文件路径
    :param net_charge: 分子体系的净电荷，正值表示失去电子，负值表示得到电子
    :return: NELECT 值
    """
    # 检查文件是否存在
    if not os.path.isfile(potcar_path):
        raise FileNotFoundError(f"POTCAR not found: {potcar_path}")
    if not os.path.isfile(poscar_path):
        raise FileNotFoundError(f"POSCAR not found: {poscar_path}")

    # 读取 POTCAR 文件
    potcar = Potcar.from_file(potcar_path)

    # 读取 POSCAR 文件
    poscar = Poscar.from_file(poscar_path)

    # 构建 POTCAR 的相对路径
    zvals = [float(p.keywords['ZVAL']) for p in potcar]

    # 构建POSCAR的路径
    structure = poscar.structure
    atom_counts = [count for count in structure.composition.values()]  # 获取每种元素的原子数


    # 计算 NELECT
    nelect = sum(zval * count for zval, count in zip(zvals, atom_counts))

    # 调整 NELECT 考虑净电荷
    nelect -= net_charge
    # 确保 NELECT 为整数
    nelect = int(nelect)

    return nelect


def write_nelect_to_incar(nelect, incar_path):
    """
    将 NELECT 值写入 INCAR 文件。

    :param nelect: 计算得到的 NELECT 值
    :param incar_path: INCAR 文件路径
    """
    if not os.path.isfile(incar_path):
        raise FileNotFoundError(f"INCAR 文件未找到: {incar_path}")

    # 读取原始 INCAR 内容
    with open(incar_path, 'r') as f:
        lines = f.readlines()

    # 检查是否已存在 NELECT
    nelect_line_index = None
    for i, line in enumerate(lines):
        if line.strip().startswith("NELECT"):
           nelect_line_index = i
           break

    nelect_entry = f"  NELECT = {nelect}\n"

    if nelect_line_index is not None:
        # 更新现有的 NELECT
        lines[nelect_line_index] = nelect_entry
    else:
        # 添加新的 NELECT
        lines.append(nelect_entry)

    # 写回 INCAR 文件
    with open(incar_path, 'w') as f:
        f.writelines(lines)

if __name__ == "__main__":

    mat_name = sys.argv[1]
    adsorbate_name = sys.argv[2]
    net_charge = int(sys.argv[3])
   
    # 获取脚本所在的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    potcar_path = os.path.join('..', adsorbate_name, mat_name, 'POTCAR')  # 相对路径
    poscar_path = os.path.join('..', adsorbate_name, mat_name, 'POSCAR')  # 相对路径
    incar_path = os.path.join('..', adsorbate_name, mat_name, 'INCAR')    # 相对路径
    # 计算 NELECT 并写入 INCAR
    nelect = calculate_nelect_with_charge(potcar_path, poscar_path, net_charge)
    write_nelect_to_incar(nelect, incar_path)
    print(f"NELECT = {nelect} has been written to INCAR.")
