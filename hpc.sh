#!bin/sh

# Interactive
pjsub --interact -j -o interactive.out -g gk77 -L rscgrp=interactive-a,node=1,jobenv=singularity
module load singularity/3.7.3

# Object Detection
singularity shell --pwd $HOME/Instance_level_recognition/app/object_detection/src/ --nv $HOME/Instance_level_recognition/app/object_detection/object_detection_latest.sif
singularity shell --pwd $HOME/Instance_level_recognition/app/object_detection/src/ --nv $HOME/Instance_level_recognition/app/ml/python_ml_latest.sif 

# ML
module load singularity/3.7.3
singularity shell --pwd $HOME/Instance_level_recognition/app/ml/src/ --nv $HOME/Instance_level_recognition/app/ml/python_ml_latest.sif 

# For train
python ./4_ml.py data.category=athlete data.batch_size.train=4 data.batch_size.val=8 optimizer.learning_rate=1e-4 data.data_dir=../../../data/clean/athlete
python ./4_ml.py data.category=athlete data.batch_size.train=4 data.batch_size.val=8 optimizer.learning_rate=1e-4 data.data_dir=../../object_detection/data # For origin
# For test
python ./4_ml.py data.category=athlete data.data_dir=../../../data/clean/athlete data.batch_size.train=4 data.batch_size.val=8 optimizer.learning_rate=1e-4 general.is_train=False +model.weight_file=0306-233847/Loss1.2655_epoch10.bin | tee athlete_clean.log
python ./4_ml.py data.category= data.data_dir=../../../data/clean/ data.batch_size.train=4 data.batch_size.val=8 optimizer.learning_rate=1e-4 general.is_train=False +model.weight_file= | tee .log

# GCS
singularity shell --pwd /$HOME/Instance_level_recognition/app/object_detection $HOME/Instance_level_recognition/app/ml/gc_cli_latest.sif
gsutil -m cp -r gs://entity_dogs/ ./

gcloud auth login
gcloud config set project $PROJECT_ID
