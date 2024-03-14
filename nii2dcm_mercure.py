import os, sys
from re import S
import argparse
import numpy as np
from dicom_io import Dicom

import nibabel as nib
import json

import ants
from subprocess import check_output, run

def writevol(img, dicom_in_folder, output_dir, scale, type, path):
    DCM = Dicom(dicom_in_folder)
    if type == 'mosaic':
        if output_dir and len(path) > 1:
            outpath = []
            for i in path:
                root, base = os.path.split(i)
                dcmpath = os.path.join(output_dir, base)
                outpath.append(dcmpath)
        # elif output_dir and len(path) == 1:
        #     outpath = os.path.join(output_dir, args.mode + '_' + fname)
        else:
            outpath = path
        DCM.writeMosaicDicom(img, path, outpath, scale)
    if type == 'volume':
        if output_dir and len(path) > 1:
            outpath = []
            for i in path:
                root, base = os.path.split(i)
                dcmpath = os.path.join(output_dir, base)
                outpath.append(dcmpath)
        elif output_dir and len(path) == 1:
            #img = img.transpose(2,0,1)
            root, base = os.path.split(path[0])
            outpath = [os.path.join(output_dir,base)]
        DCM.writeVolDicom(img, path, outpath, scale)

def find_json_for_nifti(nifti_path):
    import glob
    import os
    
    directory = os.path.dirname(nifti_path)# Extract the directory of the NIfTI file
    search_pattern = os.path.join(directory, '*.json') # Construct the search pattern for JSON files in the same directory
    json_files = glob.glob(search_pattern)# Find all JSON files in the directory
    json_files = [file for file in json_files if not file.endswith('task.json')] # Igonre tricky snicky task.json file
    json_files.sort()# Sort the list of files to ensure we are picking the last one
    if json_files:
        #print(f"Found {len(json_files)} JSON files corresponding to the NIfTI file. Selecting the last one, i.e., '{json_files[-1]}'.")
        return json_files[-1] # Select the last JSON file in the list, if any are present
    else:
        print("No JSON file found corresponding to the NIfTI file.")
        return None

    
def mosaic_or_volume(nii_data, nifti_path): 
    result = "volume" 
    # Determine if the image is 3D or 4D
    if nii_data.ndim == 4:
        #get the meta data file
        json_path  = find_json_for_nifti(nifti_path)
        try: # Check if "ImageType" field contains "MOSAIC"
            with open(json_path, 'r') as file:
                metadata = json.load(file)
                if "ImageType" in metadata and "MOSAIC" in metadata["ImageType"]:
                    result = "mosaic"
        except FileNotFoundError:
            print("Metadata JSON file not found.")
        except Exception as e:
            print(f"An error occurred: {e}")

    return result


def check_orientation(image, arr):
    import nibabel as nib
    """
    Check the NIfTI orientation, and flip to  'RPS' if needed.
    :param mr_image: NIfTI file
    :param mr_arr: array file
    :return: array after flipping
    """

    dcmax = ('L','P','S')
    dcmor = nib.orientations.axcodes2ornt(dcmax)
    imax = nib.aff2axcodes(image.affine)
    imor = nib.orientations.axcodes2ornt(imax)
    ornt_xfm = nib.orientations.ornt_transform(imor, dcmor)
    
    arr_dcm = nib.apply_orientation(arr,ornt_xfm)
    return arr.transpose(1,0,2,3)


def convert_nifti_to_dicom(dicom_in_folder, nii_temp_file, output_dir):
    import nibabel as nib

    # # read in dicom data and gradient if data is diffusion
    DCM = Dicom(dicom_in_folder) 

    # get the strides of the nifti
    cmd = ('mrinfo -strides %s' % dicom_in_folder).split() 
    stride = check_output(cmd)
    stride = stride.strip().decode('utf-8').replace(' ',',')
    stride_RAS = '-1,2,3'

    im, dcmdict = DCM.initialize()
    nii = ants.image_read(nii_temp_file).numpy()

    base,fname = os.path.split(nii_temp_file)
    pacsin = os.path.join(base,'for_pacs.nii')
    cmd = ('mrconvert -force -stride %s %s %s' % (stride, nii_temp_file, pacsin)).split()
    p = run(cmd)

    nii1 = ants.image_read(pacsin).numpy()
    nii1 = nii1.astype('uint16')
    # from utils.image import load_mrtrix
    # niim = load_mrtrix(pacsin)
    #nii1 = niim.data()

    niib = nib.load(pacsin)
    nii2 = niib.get_fdata()
    # import pdb; pdb.set_trace()
    nii2 = check_orientation(niib, nii2)

    # import matplotlib.pyplot as plt
    # fig, ax = plt.subplots(1, 2)
    # ax[0].imshow(im[:, :, 33, 1])  
    # ax[0].set_title('Original Image')
    # ax[1].imshow(nii2[:, :, 33, 1])
    # ax[1].set_title('Processed Image')
    # plt.suptitle('Please make sure the images are oriented correctly.')
    # plt.show()


    # fliplr = input('flip the image left-right? [y/n]:')
    # if 'y' in fliplr.lower():
    #     nii2 = np.flip(nii2, axis=2)
    nii2 = np.flip(nii2, axis=2)

    nii_type = mosaic_or_volume(nii2,nii_temp_file)
    writevol(nii2, dicom_in_folder, output_dir, 0, nii_type, dcmdict["dataReadOrder"])
