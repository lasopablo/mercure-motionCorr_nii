import sys
import os
import glob
from dcm2nii_mercure import convert_dicom_to_nifti
from nii2dcm_mercure import convert_nifti_to_dicom
from ants_motionCorrection import run_antsMotionCorr

def main():
    if len(sys.argv) != 3:
        print("Error: Missing arguments!")
        print("Usage: python main.py [input-folder] [output-folder]")
        sys.exit(1)

    dicom_in_folder = sys.argv[1]
    nii_temp_folder = dicom_in_folder
    output_dir = sys.argv[2]

    ## dcm2nii module
    try:
        convert_dicom_to_nifti(dicom_in_folder, nii_temp_folder)
        print("DICOM to NIfTI conversion completed successfully.")
    except Exception as e:
        print(f"An error occurred during DICOM to NIfTI conversion: {e}")
        return
    nii_files = glob.glob(f'{nii_temp_folder}/*.nii') + glob.glob(f'{nii_temp_folder}/*.nii.gz')
    if not nii_files:
        print("No NIfTI files found in the temp folder.")
        sys.exit(1)
    nii_temp_file = nii_files[-1]



    ## processing module
    try:
        print("Processing NIfTI file...")
        print(f"Input NIfTI file: {nii_temp_file}")
        print(f"Output folder: {output_dir}")
        nii_temp_file_out = run_antsMotionCorr(nii_temp_file, nii_temp_folder)
        print("Processing completed successfully.")
    except Exception as e:
        print(f"An error occurred during processing: {e}")
        return


    ## nii2dcm module
    try:
        convert_nifti_to_dicom(dicom_in_folder, nii_temp_file_out, output_dir)
        print("NIfTI to DICOM conversion completed successfully.")
    except Exception as e:
        print(f"An error occurred during NIfTI to DICOM conversion: {e}")


if __name__ == "__main__":
    main()
