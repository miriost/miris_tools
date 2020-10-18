#!/bin/bash

trap "exit" INT

usage="USAGE: create_cluster_anlysis.sh -f [list of fold numbers] -c [list of cluster sizes]"
folds=$(seq 0 1 39)
cluster_sizes=$(seq 100 10 130)
while getopts "hf:c:s:m:o:" opt; do
	case ${opt} in
		h ) echo ${usage} ; exit 1
      			;;
    		f ) folds=${OPTARG}
      			;;
		c ) cluster_sizes=${OPTARG}
			;;
		\? ) echo ${usage}; exit 1
      			;;
	esac
done

# loop folds
for fold in ${folds} ; do
	fold_dir=FOLD${fold}
	# loop cluster size
	for cs in ${cluster_sizes}; do
		output_dir=${fold_dir}/cs_${cs}
		mkdir -p ${output_dir}
		if [ -f ${output_dir}/feautre_list.csv ] ; then
			# already has a feature_list.csv file - skipping
			continue
		fi
		python -u ~/antibody_sequence_embedding/executable_scripts/cluster_proximity_brute_force.py -d ${fold_dir}/FILTERED_DATA_TRAIN.tab -v ${fold_dir}/VECTORS_TRAIN.csv --perform_NN=True --perform_results_analysis=True -of ${output_dir} -od cs_${cs} -cs ${cs} -tm 11474836480 --cpus=12 --step=10000 -id FILENAME 2>&1 | tee -a ${output_dir}/cs_${cs}_cluster_proximity_brute_force.log.txt
	done
done 