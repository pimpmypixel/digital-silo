import numpy as np
from src.utilities.data_utils import *


def _evaluate_accuracy(y, pred, grace_period=60):
    '''[summary]
        
    [description]
    
    TODO:
        should handle duplicate counts 
    Args:
        y: [description]
        pred: [description]
    '''
    pred = pred['mid'].values
    y = y['cutpoint'].values
    result = {}
    # print('predicted cutpoints dim {}'.format(pred.shape))
    # print(pred)
    # print('labelled cutpoints dim {}'.format(y.shape))
    # print(y)

    delta = np.timedelta64(grace_period, 's')
    is_close = np.abs(y - pred[:, np.newaxis]) <= delta

    num_correct = np.sum(np.any(is_close, axis=1))
    num_cuts = len(y)
    num_pred = len(pred)

    return (num_correct, num_cuts, num_pred)

def accuracy_score_f1(model, X_path, y_path=None):
    '''[summary]
    
    [description]
    
    Args:
        model: [description]
        X_path: [root path for caption files]
        y_path: [root path for cut files] (default: {the same as X_path})
    
    Returns:
        [description]
        [type]
    '''
    caption_files = load_caption_files(X_path)
    results = []

    total_num_correct = 0    
    total_num_cuts = 0
    total_num_pred = 0

    for caption_file in caption_files:
        X, metadata = caption_file

        if y_path == None:
            if X_path.endswith('/'):
                y_path = X_path[:-1]
            else:
                y_path = X_path    

        y_file_path = find_matching_filepath(metadata['filename'], 'cuts', y_path)
        y, _ = next(load_program_cut_files(y_file_path))

        #TODO: decision unit and this is not a true f1 score
        #decision unit (for classification) should be roughly the same as grace period?
        pred = model.predict(X)
        num_correct, num_cuts, num_pred = _evaluate_accuracy(y, pred)

        msg = 'There were {} true program cuts. The model predicted ' \
          '{} cuts and {} predicted cuts were true.'    
        print(msg.format(num_cuts, num_pred, num_correct))

        total_num_correct += num_correct    
        total_num_cuts += num_cuts
        total_num_pred += num_pred

    recall = total_num_correct / total_num_cuts
    precision = total_num_correct / total_num_pred
    print('precision: {}, recall: {}'.format(precision, recall))

    f1_score = 2*(precision*recall)/(precision + recall)
    # return more detailed report like showing failure cases    
    return f1_score