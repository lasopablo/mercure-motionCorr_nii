import subprocess
from pathlib import Path

def convert_dicom_to_nifti(in_folder, out_folder):
    """
    Calls the dcm2niix tool to convert DICOM files in the input folder to NIfTI format
    and saves them to the output folder.
    """
    # Ensure input and output directories exist
    in_path = Path(in_folder)
    out_path = Path(out_folder)
    if not in_path.exists() or not out_path.exists():
        raise ValueError("Input or output path does not exist.")

    # Build the command to run dcm2niix
    # -o specifies the output directory, -f specifies the filename format
    command = ["dcm2niix", "-o", str(out_path), "-f", "%p_%s", str(in_path)]
    subprocess.run(command, check=True)
