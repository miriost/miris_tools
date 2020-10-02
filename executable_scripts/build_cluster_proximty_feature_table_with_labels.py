# -*- coding: utf-8 -*-
#!/bin/sh
''''exec python -u -- "$0" ${1+"$@"} # '''

"""
Created on Thu Apr 23 10:18:13 2020

@author: mirio
"""
"""
Cluster proximity to feature table

Feture generation script 
================
Input:
Feature list - a file containing the relevant clusters (max distance + center)
data file
vectors file

Output:
    Feature file, where each row is a subject, each column is a sequence, each cell is the normlized frequency of sequences in each feature
    
"""

import pandas as pd
import numpy as np
import sys, argparse
import os
import random
import ray
import time
from datetime import datetime
from sklearn.metrics.pairwise import pairwise_distances


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--features_list',
                        help='feature list file, contains the list of relevent features, including feature '
                             'center and maximal distance from it')
    parser.add_argument('-d', '--data_file_path',  help='the filtered data file path')
    parser.add_argument('-v', '--vectors_file_path',  help='the vectors file path')
    parser.add_argument('-of', '--output_folder_path', default="./",  help='Output folder for the feature table')
    parser.add_argument('-od', '--output_description',  help='description to use inside output file names')
    parser.add_argument('-s', '--subject_col_name',
                        help='subject column name in data file, default "FILENAME"', default='FILENAME', type=str)
    parser.add_argument('-l', '--labels_col_name',
                        help='labels column name in data file, default "labels"', default='labels', type=str)
    parser.add_argument('-c', '--cpus',
                        help='number of cpus to run parallel computing', default=2, type=int)
    parser.add_argument('-dm', '--dist_metric',
                        help='type of distance to use, default=euclidean', default='euclidean', type=str)
    parser.add_argument('-tm', '--thread_memory', help='memory size for ray thread (bytes)', type=int)
    args = parser.parse_args()
    
    if not(os.path.isfile(args.features_list)):
        print('feature list file error, make sure file path exists\nExiting...')
        sys.exit(1)
                
    if not(os.path.isfile(args.data_file_path)):
        print('feature file error, make sure file path exists\nExiting...')
        sys.exit(1)

    if not os.path.isfile(args.vectors_file_path):
        print('vectors file error, make sure file path exists\nExiting...')
        sys.exit(1) 

    # load files
    cpus = args.cpus
    dist_metric = args.dist_metric
    feature_list = pd.read_csv(args.features_list)
    data_file = pd.read_csv(args.data_file_path, sep='\t')
    vectors_file = pd.read_csv(args.vectors_file_path)

    if args.labels_col_name not in data_file.columns:
        print(f'label "{args.labels_col_name}" column name doesnt exist in data file.\nExiting...')
        sys.exit(1)
        
    if args.subject_col_name not in data_file.columns:
        print(f'"{args.subject_col_name}" column name doesnt exist in data file.\nExiting...')
        sys.exit(1)
    
    if 'feature_index' not in feature_list.columns:
        print(f'"feature list file error, no "feature index" column. please check.\n exiting...')
        sys.exit(1)
    else:
        print(f'feature indexes: {feature_list.index}')

    if args.thread_memory is not None:
        ray.init(memory=args.thread_memory, object_store_memory=args.thread_memory)
    else:
        ray.init()

    by_subject = data_file.groupby(args.subject_col_name)
    # for each subject - add feature frequency columns
    result_ids = []
    for subject, frame in by_subject:
        subject_vectors = vectors_file.iloc[frame.index]
        result_ids += [get_subject_feature_table.remote(subject, feature_list, subject_vectors, cpus, dist_metric)]
    features_table = pd.concat([ray.get(res_id) for res_id in result_ids])

    # normalize the feature table
    features_table = features_table.div(features_table.sum(axis=1), axis=0)

    # add subject labels column
    features_table[args.labels_col_name] = None
    for subject, frame in by_subject:
        label = frame[args.labels_col_name].unique()[0]
        features_table.loc[subject, args.labels_col_name] = label

    # save to file
    features_table.to_csv(os.path.join(args.output_folder_path, args.output_description + '_feature_table.csv'),
                          index_label='SUBJECT')
      
    print('file saved to ', os.path.join(args.output_folder_path, args.output_description + '_feature_table.csv'))


@ray.remote
def get_subject_feature_table(subject, feature_list, subject_vectors, cpus=2, dist_metric='euclidean'):
    # create an empty matrix, each raw is a subject, each column is a feature (cluster)
    features = feature_list.iloc[:, -100:]
    max_distance = np.array(feature_list.loc[:, 'max_distance']).reshape(1, len(feature_list))

    print('Start creating feature table for subject {}'.format(subject))
    t0 = time.time()
    subject_features_table = pd.DataFrame(0, index=[subject], columns=feature_list['feature_index'].to_list())
    # for each vector belonging to the subject
    distances = pairwise_distances(X=subject_vectors, Y=features, metric=dist_metric, n_jobs=cpus)
    distance_close_enough_mat = np.less_equal(distances, max_distance)
    features_count = np.sum(distance_close_enough_mat)
    if features_count >= 1:
        for distance_close_enough_vec in distance_close_enough_mat:
            if np.sum(distance_close_enough_vec) == 0:
                continue
            add_feature_index = np.where(distance_close_enough_vec)
            subject_features_table.loc[subject, feature_list.loc[add_feature_index[0], 'feature_index']] += 1

    print('Finished creating feature table for subject {}, feature count {}, took {}'.format(subject,
                                                                                             features_count,
                                                                                             time.time()-t0))
    return subject_features_table


def test_get_subject_feature_table():
    data = pd.DataFrame()
    data['SUBJECT'] = random.choices(['P1_I1', 'P1_I2', 'P1_I3', 'P1_I4', 'P1_I5', 'P1_I6', 'P1_I7', 'P1_I8'], k=1000)
    for subject in data['SUBJECT'].unique():
        data.loc[data['SUBJECT'] == subject, 'labels'] = random.sample(['healthy', 'celiac'], k=1)[0]
    vectors = pd.DataFrame(np.random.rand(1000, 100))
    feature_list = pd.DataFrame(np.random.rand(100, 100), columns=list(range(100)))
    feature_list['feature_index'] = list(range(100))
    feature_list['max_distance'] = np.random.rand(100, 1) + 4
    cols = feature_list.columns.tolist()
    cols = cols[-2:] + cols[:-2]
    feature_list = feature_list[cols]
    by_subject = data.groupby('SUBJECT')

    result_ids = []
    for subject, frame in by_subject:
        subject_vectors = vectors.iloc[frame.index]
        result_ids += [get_subject_feature_table.remote(subject, feature_list, subject_vectors)]
    features_table = pd.concat([ray.get(id) for id in result_ids])

    features_table = features_table.div(features_table.sum(axis=1), axis=0)

    # add subject labels column
    features_table['labels'] = None
    for subject, frame in by_subject:
        label = frame['labels'].unique()[0]
        features_table.loc[subject, 'labels'] = label

    return features_table


if __name__ == '__main__':
    main()
