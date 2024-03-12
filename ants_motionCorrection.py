import os
import subprocess

def run_antsMotionCorr(input_nifti, base_output_dir):
    original_cwd = os.getcwd()
    writable_temp_dir = "/tmp"
    os.chdir(writable_temp_dir)

    # ANTs Motion Correction
    output_prefix = f"{base_output_dir}/motcorr"
    try: 
        average_time_series_cmd = f"antsMotionCorr -d 3 -a {input_nifti} -o {output_prefix}_avg.nii.gz"
        motion_correction_cmd = f"antsMotionCorr -d 3 -o [motcorr,{output_prefix}.nii.gz,{output_prefix}_avg.nii.gz] -m gc[{output_prefix}_avg.nii.gz,{input_nifti}, 1, 1, Random, 0.05] -t Affine[0.005] -i 20 -u 1 -e 1 -s 0 -f 1 -n 10 -v 1"
        subprocess.run(average_time_series_cmd, shell=True, check=True)
        subprocess.run(motion_correction_cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command '{e.cmd}' returned non-zero exit status {e.returncode}.")
        print(f"Error output:\n{e.stderr.decode()}")
    finally:
        os.chdir(original_cwd)

    return f"{output_prefix}.nii.gz"
