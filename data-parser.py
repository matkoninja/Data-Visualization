import pandas as pd
import numpy as np
from os import listdir
from os.path import join

DATASET_PATH = "./dataset"

#Load Dataset
"""load all datasets into one dictionary as dataframes"""

datasets = {}

for f in listdir(DATASET_PATH):
    #print(f[:-4])
    file_name_wihtout_extension = f[:-4]
    datasets[file_name_wihtout_extension] = pd.read_csv(join(DATASET_PATH, f))

print(datasets)


#Parse individual datasets
