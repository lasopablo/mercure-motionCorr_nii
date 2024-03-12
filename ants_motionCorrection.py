import subprocess

def run_antsMotionCorr(input_nifti, base_output_dir):
    output_prefix = f"{base_output_dir}/motcorr"

    # Construct the commands
    average_time_series_cmd = f"antsMotionCorr -d 3 -a {input_nifti} -o {output_prefix}_avg.nii.gz"
    motion_correction_cmd = f"antsMotionCorr -d 3 -o [motcorr,{output_prefix}.nii.gz,{output_prefix}_avg.nii.gz] -m gc[{output_prefix}_avg.nii.gz,{input_nifti}, 1, 1, Random, 0.05] -t Affine[0.005] -i 20 -u 1 -e 1 -s 0 -f 1 -n 10 -v 1"

    # Execute the commands
    subprocess.run(average_time_series_cmd, shell=True, check=True)
    subprocess.run(motion_correction_cmd, shell=True, check=True)

    return f"{output_prefix}.nii.gz"
