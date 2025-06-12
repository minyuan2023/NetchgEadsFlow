import os
import subprocess
import time
import datetime
import sys
import glob
import re
from contextlib import contextmanager

# 定义任务状态枚举
TASK_STATUS = {
    "NOT_EXIST": "not_exist",
    "NOT_EXECUTED": "not_executed",
    "IN_PROGRESS": "in_progress",
    "COMPLETED": "completed",
    "SUCCESS": "success",
    "FAILED": "failed",
    "RETRY": "retry",
    "MAX_RETRY_REACHED": "max_retry_reached"
}

# 外部脚本文件名变量定义
RCHECK_SCRIPT = "rcheck.sh"
BACKUP_SCRIPT = "backup.sh"
RELAX2_SCRIPT = "gam-subvasp.sh"
R2T_SCRIPT = "r2t.sh"
SLAB = 'slab.py'
ADSORBATE_NELECT = 'adsorbate-NELECT.py'
# 新增：用于净电荷不为0时额外计算的吸附物几何优化脚本
FAR_ADSORBATE_NELECT = 'far-adsorbate-NELECT.py'
THERMAL = 'thermal.py'
E_SCRIPT = 'getE.sh'
G_SCRIPT = 'getG.sh'
BINDING = 'binding.py'
FAR_BINDING = 'far-binding.py'

# 获取传入的参数
MAT = sys.argv[1]  # 材料名称
ADS = sys.argv[2]  # 吸附物名称（若有多个，请用逗号分隔）
# ADS = ["HC2O4-1"]
SITE_INDEX = sys.argv[3]  # 吸附位点
net_charge = sys.argv[4]  # 系统净电荷
TOP_LAYER = '3'  # 放开 top layer 数量

contributors_info = r"""

      ____  _           _ _             
     | __ )(_)_ __   __| (_)_ __   __ _ 
     |  _ \| | '_ \ / _` | | '_ \ / _` |
     | |_) | | | | | (_| | | | | | (_| |
     |____/|_|_| |_|\__,_|_|_| |_|\__, |
                                  |___/ 

"""


# 日志函数
def log_info(message):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: {message}")


def log_error(message):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: {message}", file=sys.stderr)


def error_exit(message):
    log_error(message)
    exit(1)


@contextmanager
def change_directory(destination):
    original_dir = os.getcwd()
    try:
        os.chdir(destination)
        yield
    finally:
        os.chdir(original_dir)


# 检查 SLURM 作业是否正在运行
def check_slurm_job_running(identifier):
    slurm_files = glob.glob(f"{identifier}/slurm-*.out")
    for file in slurm_files:
        job_id = re.search(r'\d+', os.path.basename(file)).group()
        try:
            job_status = subprocess.check_output(['squeue', '-j', job_id], stderr=subprocess.DEVNULL).decode()
            if job_id in job_status:
                log_info(f"Job for {file} is currently running. Skipping job submission.")
                return True, job_id
        except subprocess.CalledProcessError:
            pass
    return False, None


# 提交任务
def submit_job(identifier):
    try:
        job_output = subprocess.check_output([RELAX2_SCRIPT, identifier]).decode()
        job_id_match = re.search(r'job (\d+)', job_output)
        if job_id_match:
            job_id = job_id_match.group(1)
            log_info(f"Submitted job {job_id} for {identifier}.")
            return job_id
        else:
            log_error(f"Error: Failed to find job ID in output: {job_output}")
            return
    except subprocess.CalledProcessError as e:
        error_exit(f"Error: Failed to submit job for {identifier}. Details: {e}")


# 备份并重新提交任务
def backup_and_resubmit(identifier):
    try:
        result = subprocess.call([BACKUP_SCRIPT, identifier])
        if result != 0:
            log_error(f"Backup failed for {identifier}. Exit code: {result}")
            return
    except Exception as e:
        log_error(f"Error executing backup script for {identifier}: {e}")
        return
    log_info(f"Backup for {identifier} completed. Resubmitting the job.")
    job_id = submit_job(identifier)
    if job_id:
        log_info(f"Job submitted successfully with ID: {job_id}")
    else:
        log_error(f"Job submission failed for {identifier}.")
    return job_id


# 等待任务完成
def wait_for_job_completion(job_id):
    log_info(f"Waiting for job {job_id} to complete...")
    while True:
        try:
            job_status = subprocess.check_output(['squeue', '-j', job_id], stderr=subprocess.DEVNULL).decode()
            if job_id not in job_status:
                log_info(f"Job {job_id} has completed.")
                break
        except subprocess.CalledProcessError:
            break
        log_info(f"Job {job_id} is still running...")
        time.sleep(60)


# 检查 OUTCAR 文件并处理重试
def check_outcar_and_retry(identifier):
    try:
        check_output = subprocess.check_output([RCHECK_SCRIPT, identifier], stderr=subprocess.STDOUT).decode()
        if f"Success: {identifier}" in check_output:
            log_info(f"Calculation for {identifier} successfully completed.")
            return
    except subprocess.CalledProcessError as e:
        log_error(f"Error checking output for {identifier}: {e.output.decode()}")
        return
    is_running, job_id = check_slurm_job_running(identifier)
    if is_running:
        return job_id
    job_id = backup_and_resubmit(identifier)
    if job_id:
        return job_id
    else:
        log_info("Failed to resubmit the job.")


# 检查 thermal OUTCAR 文件并处理重试
def thermalcheck_outcar_and_retry(identifier):
    try:
        subprocess.check_output(["grep", "-q", "Total CPU time", f"{identifier}/OUTCAR"],
                                stderr=subprocess.STDOUT).decode()
        log_info(f"Calculation for {identifier} successfully completed.")
        return
    except subprocess.CalledProcessError as e:
        log_info(f"Calculation for {identifier} failed. Error: {e.output.decode()}")
    is_running, job_id = check_slurm_job_running(MAT)
    if is_running:
        return job_id
    job_id = backup_and_resubmit(MAT)
    if job_id:
        return job_id
    else:
        log_info("Failed to resubmit the job.")


# 材料几何优化任务管理
def slab_job(identifier):
    target_dir = os.path.join(".", identifier)
    if os.path.isdir(target_dir):
        log_info(f"Directory for {identifier} already exists.")
        slurm_files = glob.glob(os.path.join(".", identifier, "slurm-*.out"))
        if slurm_files:
            log_info("slurm files found.")
            is_running, job_id = check_slurm_job_running(identifier)
            if is_running:
                log_info(f"Job is still running for {identifier}. Skipping new submission.")
                return job_id
        else:
            log_info("slurm files not found.")
        outcar_file = os.path.join(".", identifier, "OUTCAR")
        if os.path.isfile(outcar_file):
            log_info("OUTCAR file found. Checking calculation status...")
            job_id = check_outcar_and_retry(identifier)
            if job_id:
                return job_id
        else:
            log_info("OUTCAR file not found. Submitting new job...")
            job_id = submit_job(identifier)
            if job_id:
                return job_id
    else:
        log_info(f"No existing directory for {identifier}. Creating and submitting job...")
        try:
            subprocess.call(["python", SLAB, identifier, TOP_LAYER])
        except subprocess.CalledProcessError as e:
            error_exit(f"Error: Failed to run script for {identifier}. Details: {e}")
        if not os.path.isdir(target_dir):
            error_exit(f"Error: Failed to create directory for {identifier}.")
        job_id = submit_job(identifier)
        if job_id:
            return job_id
    return 'No action taken'


# 吸附物几何优化任务管理（调用 ORRadsorbate-NELECT.py 脚本）
def ads_job(identifier):
    target_dir = os.path.join("..", identifier, MAT)
    if os.path.isdir(target_dir):
        log_info(f"Directory for {identifier} already exists.")
        with change_directory(os.path.join("..", identifier)):
            slurm_files = glob.glob(os.path.join('.', MAT, "slurm-*.out"))
            if slurm_files:
                log_info("slurm files found.")
                is_running, job_id = check_slurm_job_running(MAT)
                if is_running:
                    log_info(f"Job is still running for {identifier}. Skipping new submission.")
                    return job_id
            else:
                log_info("slurm files not found.")
            outcar_file = os.path.join('.', MAT, "OUTCAR")
            if os.path.isfile(outcar_file):
                log_info("OUTCAR file found. Checking calculation status...")
                job_id = check_outcar_and_retry(MAT)
                if job_id:
                    return job_id
            else:
                log_info("OUTCAR file not found. Submitting new job...")
                job_id = submit_job(MAT)
                if job_id:
                    return job_id
    else:
        log_info(f"No existing directory for {identifier}. Creating and submitting job...")
        try:
            subprocess.call(["python", ADSORBATE_NELECT, MAT, identifier, net_charge, TOP_LAYER, SITE_INDEX])
        except subprocess.CalledProcessError as e:
            error_exit(f"Error: Failed to run script for {identifier}. Details: {e}")
        if not os.path.isdir(target_dir):
            error_exit(f"Error: Failed to create directory for {identifier}.")
        with change_directory(os.path.join("..", identifier)):
            job_id = submit_job(MAT)
            if job_id:
                return job_id
    return 'No action taken'


# 新增：吸附物几何优化任务管理（非零净电荷时额外调用 far-ORRadsorbate-NELECT.py 脚本）
def far_ads_job(identifier):
    far_mat = "far-" + MAT
    target_dir = os.path.join("..", identifier, far_mat)
    if os.path.isdir(target_dir):
        log_info(f"Directory for {identifier} (far version) already exists.")
        with change_directory(os.path.join("..", identifier)):
            slurm_files = glob.glob(os.path.join('.', far_mat, "slurm-*.out"))
            if slurm_files:
                log_info("slurm files found in far directory.")
                is_running, job_id = check_slurm_job_running(far_mat)
                if is_running:
                    log_info(f"Job is still running for {identifier} (far version). Skipping new submission.")
                    return job_id
            else:
                log_info("slurm files not found in far directory.")
            outcar_file = os.path.join('.', far_mat, "OUTCAR")
            if os.path.isfile(outcar_file):
                log_info("OUTCAR file found in far directory. Checking calculation status...")
                job_id = check_outcar_and_retry(far_mat)
                if job_id:
                    return job_id
            else:
                log_info("OUTCAR file not found in far directory. Submitting new job...")
                job_id = submit_job(far_mat)
                if job_id:
                    return job_id
    else:
        log_info(f"No existing far directory for {identifier}. Creating and submitting job...")
        try:
            subprocess.call(["python", FAR_ADSORBATE_NELECT, MAT, identifier, net_charge, TOP_LAYER, SITE_INDEX])
        except subprocess.CalledProcessError as e:
            error_exit(f"Error: Failed to run far script for {identifier}. Details: {e}")
        if not os.path.isdir(target_dir):
            error_exit(f"Error: Failed to create far directory for {identifier}.")
        with change_directory(os.path.join("..", identifier)):
            job_id = submit_job(far_mat)
            if job_id:
                return job_id
    return 'No action taken'


# 热力学任务管理
def thermal_job(identifier):
    target_dir = os.path.join("..", identifier, '2-thermal', MAT)
    if os.path.isdir(target_dir):
        log_info(f"Directory for 2-thermal {identifier} already exists.")
        with change_directory(os.path.join("..", identifier, '2-thermal')):
            slurm_files = glob.glob(os.path.join('.', MAT, "slurm-*.out"))
            if slurm_files:
                log_info("slurm files found.")
                is_running, job_id = check_slurm_job_running(identifier)
                if is_running:
                    log_info(f"Job is still running for 2-thermal {identifier}. Skipping new submission.")
                    return job_id
            else:
                log_info("slurm files not found.")
            outcar_file = os.path.join('.', MAT, "OUTCAR")
            if os.path.isfile(outcar_file):
                log_info("OUTCAR file found. Checking calculation status...")
                job_id = thermalcheck_outcar_and_retry(MAT)
                if job_id:
                    return job_id
            else:
                log_info("OUTCAR file not found. Submitting new job...")
                job_id = submit_job(MAT)
                if job_id:
                    return job_id
    else:
        with change_directory(os.path.join('..', identifier)):
            subprocess.check_call([R2T_SCRIPT, MAT])
        subprocess.check_call(["python", THERMAL, MAT, identifier, SITE_INDEX])
        log_info(f"Created directory for thermal calculations at {target_dir}")
        with change_directory(os.path.join('..', identifier, '2-thermal')):
            log_info("Submitting thermal calculation...")
            job_id = submit_job(MAT)
            if job_id:
                return job_id
    return 'No action taken'


if __name__ == "__main__":
    print(contributors_info)
    if len(sys.argv) < 5:
        error_exit(
            "Error: Please provide required arguments.\nUsage: python script.py <material> <adsorbate> <site_index> <net_charge>")

    # 材料几何优化
    runjob_id = slab_job(MAT)
    for _ in range(2):  # 最多检查2次
        if runjob_id:
            wait_for_job_completion(runjob_id)
            runjob_id = check_outcar_and_retry(MAT)
            if runjob_id:
                continue
        else:
            subprocess.check_call([E_SCRIPT, MAT])
            break

    # 吸附物几何优化（并行提交）
    runjob_ids = []
    # 对每个吸附物（可能多个，逗号分隔），均调用 ads_job（调用 adsorbate-NELECT.py 脚本）
    for ads in ADS.split(','):
        runjob_id = ads_job(ads)
        if runjob_id:
            runjob_ids.append(runjob_id)
    for runjob_id in runjob_ids:
        wait_for_job_completion(runjob_id)

    # 若净电荷不为0，则额外执行 far_ads_job（调用 far-adsorbate-NELECT.py 脚本），目标目录为 "../{ads}/far-{MAT}"
    if int(net_charge) != 0:
        runjob_ids = []
        for ads in ADS.split(','):
            runjob_id = far_ads_job(ads)
            if runjob_id:
                runjob_ids.append(runjob_id)
        for runjob_id in runjob_ids:
            wait_for_job_completion(runjob_id)

    # 检查与再提交吸附物（串联检查）
    for ads in ADS.split(','):
        with change_directory(os.path.join('..', ads)):
            runjob_id = check_outcar_and_retry(MAT)
            if runjob_id:
                wait_for_job_completion(runjob_id)
                runjob_id = check_outcar_and_retry(MAT)
                if runjob_id:
                    wait_for_job_completion(runjob_id)
                else:
                    subprocess.check_call([E_SCRIPT, MAT])
            else:
                subprocess.check_call([E_SCRIPT, MAT])
    log_info("GemOpt tasks have been completed.")

    # 吸附物热力学计算
    runjob_ids = []
    for ads in ADS.split(','):
        runjob_id = thermal_job(ads)
        if runjob_id:
            runjob_ids.append(runjob_id)
    for runjob_id in runjob_ids:
        wait_for_job_completion(runjob_id)
    for ads in ADS.split(','):
        with change_directory(os.path.join('..', ads, '2-thermal')):
            runjob_id = thermalcheck_outcar_and_retry(MAT)
            if runjob_id:
                wait_for_job_completion(runjob_id)
                runjob_id = thermalcheck_outcar_and_retry(MAT)
                if runjob_id:
                    wait_for_job_completion(runjob_id)
                else:
                    subprocess.check_call([G_SCRIPT, MAT])
            else:
                subprocess.check_call([G_SCRIPT, MAT])
    log_info("Thermal calculations have been completed.")

    # 结合能计算阶段：
    # 无论净电荷如何，ads_job 已经调用了 adsorbate-NELECT.py；
    # 当净电荷为0时，调用 binding.py；若净电荷不为0，则调用 far-binding.py
    if int(net_charge) == 0:
        for ads in ADS.split(','):
            subprocess.check_call(["python", BINDING, MAT, ads])
    else:
        for ads in ADS.split(','):
            subprocess.check_call(["python", FAR_BINDING, MAT, ads])
