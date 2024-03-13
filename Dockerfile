# Start with the Miniconda base image
FROM continuumio/miniconda3:latest

# Set working directory
WORKDIR /app

# Update conda, install MRtrix3, and other dependencies
RUN conda update -n base -c defaults conda && \
    conda install -c mrtrix3 mrtrix3

# Install dcm2niix using apt-get
RUN apt-get update && apt-get install -y dcm2niix

# Install ANTs dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    g++ \
    make \
    zlib1g-dev

# Clone ANTs, create build and install directories, configure, compile, and install ANTs 
RUN export workingDir=${PWD} && \
    git clone https://github.com/ANTsX/ANTs.git && \
    mkdir build install && \
    cd build && \
    cmake \
        -DCMAKE_INSTALL_PREFIX=${workingDir}/install \
        ../ANTs 2>&1 | tee cmake.log && \
    make -j 16 2>&1 | tee build.log && \
    cd ANTS-build && \
    make install 2>&1 | tee install.log

# Add ANTs to PATH environment variable
ENV PATH="/app/install/bin:${PATH}"

# Set the MPLCONFIGDIR environment variable for Matplotlib to a writable directory
ENV MPLCONFIGDIR=/app/matplotlib_cache

# Create the directory for Matplotlib cache to ensure it's writable
RUN mkdir -p ${MPLCONFIGDIR} && chmod 777 ${MPLCONFIGDIR}

# Now, copy the necessary files into the container
COPY docker-entrypoint.sh main.py requirements.txt dcm2nii_mercure.py nii2dcm_mercure.py ants_motionCorrection.py Siemens_dicom_structreader.py dicom_io.py ./

# Make the entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Install Python dependencies
RUN pip install -r requirements.txt

# Set the original working directory to ensure the entrypoint script runs correctly
WORKDIR /app

# Set the entrypoint script to run when the container starts
ENTRYPOINT ["/app/docker-entrypoint.sh"]
