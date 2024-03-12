import os, sys
import numpy as np
import pydicom
from Siemens_dicom_structreader import Unpacker
import re

def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)

class Dicom(object):
    def __init__(self, inputpath):
        self.input = inputpath

    def initialize(self):
        # Find the paths to any images we can denoise and hold on to them
        DcmDict = dict(dataReadOrder = [], matrixsize = [])
        dims = None

        print('...reading input data')
        #for (subdir, dirs, files) in os.walk(self.input):
        files = list()
        if not os.path.exists(self.input):
            sys.exit('input dicom directory not found')
        for (dirpath, dirnames, filenames) in os.walk(self.input):
            files += [os.path.join(dirpath, file) for file in filenames]

        files = natural_sort(np.unique(files).tolist())


        for f in files:
            if not f or '.DS_Store' in f or 'ED_0001' in f:
                continue

            dcmpath = os.path.join(f)

            info = pydicom.dcmread(dcmpath, force=True)
            if not hasattr(info, 'SeriesDescription'):
                continue

            ismosaic = False
            isorig = False

            if 'ORIGINAL' in info.ImageType:
                isorig = True

            if isorig:
                if dims is None:
                    dims = [info.Rows, info.Columns]
                elif [info.Rows, info.Columns] != dims:
                    print('...series dimension mismatch, skipping slice. check manually')
                    continue
                else:
                    dims = [info.Rows, info.Columns]
                DcmDict["dataReadOrder"].append(dcmpath)
                DcmDict["matrixsize"].append(dims)

        if not DcmDict["dataReadOrder"]:
            sys.exit('no data found')

        im = self.readDicom(DcmDict)
        return im, DcmDict

    def getnewSOPiUID(self):
        """
        Creates an SOPUID based on template dicom. This is deprecated by pydicom.generate_uid()
        """
        
        dcmlist = os.listdir(self.input)
        dcmlist = [x for x in dcmlist if not x == '.DS_Store']
        newSOPUID = []
        for i in range(0, len(dcmlist)):
            info = pydicom.dcmread(os.path.join(self.input, dcmlist[i]), force=True)
            SOPUID = info.SOPInstanceUID
            newSOPUID.append(SOPUID[:-16] + str(int(np.floor(1000000000 + 8999999999*np.random.random()))) + SOPUID[-6:])
        return newSOPUID

    def readDicom(self, dcmdict):
        dcmlist = dcmdict["dataReadOrder"]
        dcmlist = [x for x in dcmlist if not x == '.DS_Store']
        info = pydicom.dcmread(dcmlist[0], force=True)

        if not hasattr(info, 'ImageType'):
            info.ImageType = 'None'

        ismosaic = False
        if 'MOSAIC' in info.ImageType:
            ismosaic = True
        if 'DIFFUSION' in info.ImageType:
            grad = np.zeros((len(dcmlist), 4))
        else:
            grad = None

        datasize = [info.Rows, info.Columns]
        if hasattr(info, 'AcquisitionMatrix'):
            matrixsize = list(info.AcquisitionMatrix[i] for i in [0, 3])

        if ismosaic:
            NumberOfTiles = [int(x)/int(y) for x,y in zip(datasize, matrixsize)]
            csa = info[0x0029,0x1010].value
            csaobj = Unpacker(csa, endian='<')
            csadict = csaobj.csaread(csa)
            nmos = csadict['tags']['NumberOfImagesInMosaic']['items']
            nmos = nmos[0]
        else:
            NumberOfTiles = [0,0]
            nmos = 1

        #print('mosaic size = ' + str(NumberOfTiles))
        #print('matrix size = ' + str(matrixsize))
        if ismosaic:
            img = np.zeros((matrixsize[0], matrixsize[1], nmos, len(dcmlist)))

            # reformat from mosaic to 4D image
            for i in range(0, len(dcmlist)):
                info = pydicom.dcmread(dcmlist[i], force=True)
                data = info.pixel_array
                data = np.reshape(data, (datasize[0], datasize[1]), order='F')

                if 'DIFFUSION' in info.ImageType:
                    csa = info[0x0029,0x1010].value
                    csadict = csaobj.csaread(csa)
                    bvec = csadict['tags']['DiffusionGradientDirection']['items']
                    bval = csadict['tags']['B_value']['items']
                    # bval = info[0x0019,0x0100c].value
                    bval = bval[0]
                    if bval == 0:
                        bvec = [0, 0 ,0]
                    grad[i,:3] = np.array(bvec)
                    grad[i,-1] = bval

                c = 0
                for j in range(1, int(NumberOfTiles[0])+1):
                    for k in range(1, int(NumberOfTiles[1])+1):
                        if c > nmos-1:
                            continue
                        img[:,:,c,i] = data[(j-1)*matrixsize[0]:(j)*matrixsize[0], (k-1)*matrixsize[1]:(k)*matrixsize[1]]
                        c = c+1
        else:
            if len(dcmlist) > 1:
                img = np.zeros((datasize[0], datasize[1], len(dcmlist)))
                for i in range(0, len(dcmlist)):
                    info = pydicom.dcmread(dcmlist[i], force=True)
                    print(dcmlist[i])
                    data = info.pixel_array
                    img[:,:,i] = np.squeeze(data)
                    #dwi[:,:,i] = np.reshape(data, (datasize[0], datasize[1]), order='F')
            else:
                info = pydicom.dcmread(dcmlist[0], force=True)
                img = np.squeeze(info.pixel_array).transpose(1,2,0)
        return img

    def writeMosaicDicom(self, Signal, path, outputpath, scale):
        if isinstance(outputpath, str):
            if not os.path.isdir(outputpath):
                os.makedirs(outputpath)
        else:
            for i in outputpath:
                root, base = os.path.split(i)
                if not os.path.isdir(root):
                    os.mkdir(root)

        SN = []
        SI = []
        if len(path) == 1:
            newSI = []
            newSN = []
            dcmlist = path
            outlist = outputpath

            info = pydicom.dcmread(dcmlist[0], force=True)
            sn = info.SeriesNumber
            newsn = sn + np.random.randint(1000) + 200

            SN.append(sn)
            newSN.append(newsn)
            si = info.SeriesInstanceUID
            newsi = si[:-16] + str(int(np.floor(1000000000 + 8999999999*np.random.random()))) + si[-6:]
            SI.append(si)
            newSI.append(newsi)
        else:
            for i in path:
                info = pydicom.dcmread(i, force=True)
                sn = info.SeriesNumber
                SN.append(sn)
                si = info.SeriesInstanceUID
                SI.append(si)
            newSI = []
            newSN = []
            newuniquesn = []
            newuniquesi = []
            for i in range(0, len(np.unique(SN))):
                newuniquesn.append(np.unique(SN)[i] + np.random.randint(200) + 200)
                newuniquesi.append(np.unique(SI)[i][:-16] + str(int(np.floor(1000000000 + 8999999999*np.random.random()))) + np.unique(SI)[i][-6:])
            for j in range(0, len(path)):
                for i in range(0, len(np.unique(SN))):
                    if SN[j] == np.unique(SN)[i]:
                        newSN.append(newuniquesn[i])
                        newSI.append(newuniquesi[i])
            dcmlist = path
            outlist = outputpath

        info = pydicom.dcmread(dcmlist[0], force=True)
        datasize = [info.Rows, info.Columns]
        matrixsize = list(info.AcquisitionMatrix[i] for i in [0, 3])
        NumberOfTiles = [int(x)/int(y) for x,y in zip(datasize, matrixsize)]

        csa = info[0x0029,0x1010].value
        csaobj = Unpacker(csa, endian='<')
        csadict = csaobj.csaread(csa)
        nmos = csadict['tags']['NumberOfImagesInMosaic']['items'][0]

        newSeriesNumber = 0
        for i in range(0, len(dcmlist)):
            info = pydicom.read_file(dcmlist[i], force=True)
            SeriesID = info.SeriesInstanceUID
            SeriesNumber = info.SeriesNumber
            for ind, num in enumerate(SN):
                if SeriesNumber == SN[ind]:
                    newSeriesNumber = newSN[ind]
                if SeriesID == SI[ind]:
                    newSeriesID = newSI[ind]
            info.SeriesInstanceUID = newSeriesID
            info.SeriesNumber = newSeriesNumber
            SeriesDescription = info.SeriesDescription
            newSeriesDescription = SeriesDescription + ' hb_skullstripped'
            info.SeriesDescription = newSeriesDescription
            SOPUID = info.SOPInstanceUID
            newSOPUID = SOPUID[:-16] + str(int(np.floor(1000000000 + 8999999999*np.random.random()))) + SOPUID[-6:]
            info.SOPInstanceUID = newSOPUID
            info.CommentsOnPerformedProcedureStep = 'test image, DO NOT READ'

            imgdn = np.zeros((datasize[0], datasize[1]))
            c = 0
            for j in range(1, int(NumberOfTiles[0])+1):
                for k in range(1, int(NumberOfTiles[1])+1):
                    if c > nmos - 1:
                        continue
                    if np.ndim(Signal) == 3:
                        imgdn[(j-1)*matrixsize[0]:(j)*matrixsize[0], (k-1)*matrixsize[1]:(k)*matrixsize[1]] = Signal[:,:,c]
                    else:
                        imgdn[(j-1)*matrixsize[0]:(j)*matrixsize[0], (k-1)*matrixsize[1]:(k)*matrixsize[1]] = Signal[:,:,c,i]
                    c = c + 1

            if scale:
                imgdn = imgdn * 1000

            imgdn[imgdn > 65535] = 0
            imgdn[imgdn < 0] = 0
            imgdn = imgdn.astype('uint16')

            info.PixelData = imgdn.tobytes()
            if np.ndim(Signal) == 3:
                rootpath = outputpath
                root, base = os.path.split(path[0])
                tmp, ext = os.path.splitext(base)
            else:
                rootpath, base = os.path.split(outlist[i])
            info.save_as(os.path.join(rootpath, base.replace(".dcm",'_new.dcm')))

    def writeVolDicom(self, Signal, path, outputpath, scale):
        if isinstance(outputpath, str):
            if not os.path.isdir(outputpath):
                os.makedirs(outputpath)
        else:
            for i in outputpath:
                root, base = os.path.split(i)
                if not os.path.isdir(root):
                    os.mkdir(root)
        SI = []
        SN = []
        for i in path:
            info = pydicom.dcmread(i, force=True)
            sn = info.SeriesNumber
            SN.append(sn)
            si = info.SeriesInstanceUID
            SI.append(si)
        newSI = []
        newSN = []
        newuniquesn = []
        newuniquesi = []
        for i in range(0, len(np.unique(SN))):
            newuniquesn.append(np.unique(SN)[i] + 100)
            newuniquesi.append(np.unique(SI)[i][:-16] + str(int(np.floor(1000000000 + 8999999999*np.random.random()))) + np.unique(SI)[i][-6:])
        for j in range(0, len(path)):
            for i in range(0, len(np.unique(SN))):
                if SN[j] == np.unique(SN)[i]:
                    newSN.append(newuniquesn[i])
                    newSI.append(newuniquesi[i])
        dcmlist = path
        outlist = outputpath

        info = pydicom.dcmread(dcmlist[0], force=True)
        datasize = [info.Rows, info.Columns]
        if hasattr(info, 'AcquisitionMatrix'):
            matrixsize = list(info.AcquisitionMatrix[i] for i in [0, 3])

        for i in range(0, len(dcmlist)):
            info = pydicom.read_file(dcmlist[i], force=True)
            SeriesID = info.SeriesInstanceUID
            SeriesNumber = info.SeriesNumber
            for ind, num in enumerate(SN):
                if SeriesNumber == SN[ind]:
                    newSeriesNumber = newSN[ind]
                if SeriesID == SI[ind]:
                    newSeriesID = newSI[ind]
            info.SeriesInstanceUID = newSeriesID
            info.SeriesNumber = newSeriesNumber
            SeriesDescription = info.SeriesDescription
            newSeriesDescription = SeriesDescription + ' hb_skullstripped'
            info.SeriesDescription = newSeriesDescription
            SOPUID = info.SOPInstanceUID
            newSOPUID = SOPUID[:-16] + str(int(np.floor(1000000000 + 8999999999*np.random.random()))) + SOPUID[-6:]
            info.SOPInstanceUID = newSOPUID
            info.CommentsOnPerformedProcedureStep = 'Research image, DO NOT READ'

            #import pdb; pdb.set_trace()
            if len(dcmlist) > 1:
                imgdn = Signal[:,:,i]
            else:
                imgdn = Signal
            imgdn[imgdn > 65500] = 0
            imgdn[imgdn < 0] = 0
            imgdn = imgdn.astype('uint16')

            info.PixelData = imgdn.tobytes()
            #if np.ndim(Signal) == 3:
            #    rootpath = outputpath
            #    root, base = os.path.split(path[0])
            #    tmp, ext = os.path.splitext(base)
            #else:
            rootpath, base = os.path.split(outlist[i])
            iname = os.path.join(rootpath, base + '_' + str(info.SeriesNumber) + '_new.dcm')
            info.save_as(iname)

