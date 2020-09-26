# -*- coding: utf-8 -*-
"""
Created on Thu Apr  9 14:57:21 2020

@author: mirio
"""

# sample file 

import pandas as pd
import numpy as np
import sys, argparse
from datetime import datetime

def main(argv):

    parser = argparse.ArgumentParser(
        description='''sample sequences by subjects from embedded vectors for the clustering/classification stage ''',
        epilog="""All's well that ends well.""")
    parser.add_argument('--max_samples', type=int, help='max number of sampled sequences per subject')
    parser.add_argument('--min_samples', type=int, help='min number of sampled sequences per subject. Default is 10k.',
                        default=10000)
    parser.add_argument('--input_data_file', type=str, help='input filtered data file path')
    parser.add_argument('--output_data_file', type=str, help='output filtered data file path')
    parser.add_argument('--input_vector_file', type=str, help='input vectors file path')
    parser.add_argument('--output_vector_file', type=str, help='output vectors file path')
    parser.add_argument('--subject_field', type=str, default='FILENAME', help='name of the column which identifies the subjects')

    args = parser.parse_args()
    max_num_smaples_per_subject = args.max_samples
    min_num_samples_per_subject = args.min_samples
    Input_filtered_data_file_path = args.input_data_file
    Output_filtered_data_file_path = args.output_data_file
    Input_vector_file_path = args.input_vector_file
    Output_vector_file_path = args.output_vector_file
    Subject_field = args.subject_field

    Input_data_file = pd.read_csv(Input_filtered_data_file_path, sep='\t')
    Input_vectors_file = pd.read_csv(Input_vector_file_path)

    by_subject = Input_data_file.groupby([Subject_field])
    sub_num = 0
    positive_subjects = 0

    output_data_df = pd.DataFrame(columns = list(Input_data_file.columns))
    output_vectors_df = pd.DataFrame(columns = list(Input_vectors_file.columns))

    np.random.seed(0)
    for subject, frame in by_subject:
        sub_num += 1
        print("------------------------")
        print(f"Analysing {subject!r} {sub_num!r}")
        dateTimeObj = datetime.now()
        timeObj = dateTimeObj.time()
        print(timeObj)
        print('Original number of sequences: ', len(frame), end="\n\n")
        # sample subject without replacement and save to list
        if max_num_smaples_per_subject is not None and len(frame) >= max_num_smaples_per_subject:
            print('High number of sequences, subject removed.\n')
        if len(frame) < min_num_samples_per_subject:
            print('Lower number of sequences, subject removed.\n')
        else:
            positive_subjects += 1
            sampled_frame_indexes = np.random.choice(frame.index, min_num_samples_per_subject, replace=False)
            output_data_df = output_data_df.append(Input_data_file.iloc[sampled_frame_indexes])
            output_vectors_df = output_vectors_df.append(Input_vectors_file.iloc[sampled_frame_indexes])
            print('Subject added.')

    print('----- Summary -----')
    print(f'Analysed {sub_num!r} subjects')
    print(f'Chose {positive_subjects!r} subjects with <= {max_num_smaples_per_subject} number of sequences')

    output_data_df.to_csv(Output_filtered_data_file_path, sep='\t', index=False)
    print('output data set saved to: ', Output_filtered_data_file_path)
    output_vectors_df.to_csv(Output_vector_file_path, index=False)
    print('output vectors set saved to: ', Output_vector_file_path)


if __name__ == "__main__":
	main(sys.argv[1:])