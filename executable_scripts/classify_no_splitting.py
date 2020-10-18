import sys, argparse
import os
import pathlib
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).parent.absolute()).split('antibody_sequence_embedding')[0])            
from antibody_sequence_embedding.classifier import classifier
import pickle


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1', "True"):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0', "False"):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")

def main(argv):
    parser = argparse.ArgumentParser(
        description='''classify_no_splitting.py function performs classification based on a train and test feature 
                       tables where each row is an observation and each column is a feature. It's output is a confusion 
                       matrix and a score.''',
        epilog="""All's well that ends well.""")
    parser = argparse.ArgumentParser()
    parser.add_argument('--train_file', help='a *.csv file containing the TRAIN features table, including labels '
                                             'column')
    parser.add_argument('--test_file', help='a *.csv file containing the TEST features table, including labels column')
    parser.add_argument('--labels_col_name', help='Name of the labels column, default: "labels"', default='labels')
    parser.add_argument('--output_file', help='name of the output file, default is None (no output file)', type=str)
    parser.add_argument('--col_names', help='comma separated list of columns names to add to output', type=str)
    parser.add_argument('--col_values', help='comma separated list of columns values to add to output', type=str)
    parser.add_argument('--grid_search', help='use grid search', type=str2bool, default=False)
    parser.add_argument('--output_model_file', help='Suffix of file saving the trained models. if not provided models '
                                                    'will not be saved',
                        type=str)
    parser.add_argument('--input_model_file', help='Input file to load the model from. Makes the models argument '
                                                   'redundant', type=str)
    parser.add_argument('-M', '--models',
                        help='comma separated list of classifiers. current supported models: logistic_regression, '
                             'decision_tree, kNN, linear_svm, RBF_SVM, Gaussian, Random_Forest, MLP, ADA, MLP, '
                             'naive_bayes, QDA. default: "decision_tree"',
                        default="decision_tree")

    args = parser.parse_args()

    if not (os.path.isfile(args.train_file) and os.path.splitext(os.path.split(args.train_file)[1])[1] == '.csv'):
        print('train file {} error! Make sure the file exists and it is *.csv file.\nExiting...'.format(
            args.train_file))
        sys.exit(1)
    train_file = pd.read_csv(args.train_file, index_col=0)
    train_file.fillna(0, inplace=True)
    if not (os.path.isfile(args.test_file) and os.path.splitext(os.path.split(args.test_file)[1])[1] == '.csv'):
        print('test file {} error! Make sure the file exists and it is *.csv file.\nExiting...'.format(
            args.test_file))
        sys.exit(1)
    test_file = pd.read_csv(args.test_file, index_col=0)
    test_file.fillna(0, inplace=True)

    if args.labels_col_name:
        if (not args.labels_col_name in train_file.columns) or (not args.labels_col_name in test_file.columns):
            print('label column name doesnt exist.\nExiting...')
            sys.exit(1)
        else:
            labels_col_name = args.labels_col_name
    else:
        labels_col_name = 'labels'

    if (args.col_names is None) != (args.col_values is None):
        print('col_names and col_values arguments must be provided together.\nExiting...')
        sys.exit(1)

    col_names = None
    col_values = None
    if args.col_names is not None:
        col_names = args.col_names.split(',')
        col_values = args.col_values.split(',')
        if len(col_names) != len(col_values):
            print('col_names and col_values lists must be of the same length.\nExiting...')
            sys.exit(1)

    print("~~~~~~~~ Begin classifing...\nTrain file: {}\nTest file: {}\nLabels column name: {}\nModel: "
          "{}\n~~~~~~~".format(os.path.abspath(args.train_file), os.path.abspath(args.test_file), labels_col_name,
                               args.models))

    x_train = train_file.drop(labels_col_name, axis=1)
    y_train = train_file[labels_col_name]
    x_test = test_file.drop(labels_col_name, axis=1)
    y_test = test_file[labels_col_name]

    labels_all = pd.concat([y_train, y_test])
    feature_table = pd.concat([x_train, x_test])

    if len(x_train.columns) == 0:
        print('No features in training file.\nExiting...')
        sys.exit(1)

    if len(x_test.columns) == 0:
        print('No features in test file.\nExiting...')
        sys.exit(1)

    output = None
    if args.input_model_file:
        loaded_model = pickle.load(open(args.input_model_file, 'rb'))
        file_name = os.path.basename(args.input_model_file)
        our_classifier = classifier(feature_table=feature_table, labels=labels_all, model_name=file_name, C=.9,
                                    grid_search=args.grid_search, model=loaded_model)
        output, model = our_classifier.run_once(x_train, x_test, y_train, y_test)
    else:
        if args.models == 'all':
            models = ["logistic_regression", "decision_tree", "kNN", "linear_svm", "RBF_SVM", "Gaussian",
                      "Random_Forest", "ADA", "naive_bayes", "QDA"]
        else:
            models = args.models.split(",")
        for model_name in models:
            our_classifier = classifier(feature_table=feature_table, labels=labels_all, model_name=model_name, C=.9,
                                        grid_search=args.grid_search)
            if output is None:
                output, model = our_classifier.run_once(x_train, x_test, y_train, y_test)
                print(model)
            else:
                tmp, model = our_classifier.run_once(x_train, x_test, y_train, y_test)
                output = pd.concat([output, tmp], ignore_index=True)
            if args.output_model_file is not None:
                file_name = os.path.basename(args.output_model_file)
                dir_name = os.path.dirname(args.output_model_file)
                pickle.dump(model, open(os.path.join(dir_name, model_name + '_' + file_name), 'wb'))

    if col_names is not None:
        for idx in range(len(col_names)):
            output[col_names[idx]] = col_values[idx]

    # save output if output_file argument was provided
    if args.output_file is not None:
        output.to_csv(args.output_file, index=False)
    # print output
    print(output.to_csv(index=False))


if __name__ == "__main__":
    main(sys.argv[1:])
