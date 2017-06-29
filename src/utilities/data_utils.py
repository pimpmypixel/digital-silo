import pandas as pd
import numpy as np
import glob
import os
import math

def _date_parser(pattern):
    def f(date):
        try:
            parsed = pd.datetime.strptime(date, pattern)
        except Exception as e:
            # the first 4 or 8 lines (header) and the last line won't be parsed
            parsed = ''            
        return parsed    
    return f


def _caption_date_parser(col):
    return np.vectorize(_date_parser('%Y%m%d%H%M%S.%f'))(col)


def _cut_date_parser(date_A, date_B):
    date = '{} {}'.format(date_A, date_B)
    return _date_parser('%m/%d/%y %H:%M:%S')(date)


def _load_csv_file(path, sep, names, parse_dates, date_parser, dtype=None):
    try:
        df = pd.read_csv(path, sep=sep, header=None, names=names,
                         parse_dates=parse_dates, date_parser=date_parser,
                         dtype=dtype)
        return df
    except Exception as e:
        print(e)
        pass


def _load_single_caption_file(path):        
    col_names = ['start', 'end', 'marker', 'caption']
    df = _load_csv_file(path, sep='|', names=col_names,
                        parse_dates=['start', 'end'],
                        date_parser=_caption_date_parser,
                        dtype={'start':str, 'end':str})

    df = df.dropna()
    df = df.reset_index(drop=True)
    df['mid'] = df['start'] + 0.5 * (df['end'] - df['start'])
    metadata = annotate_file(path)
    return (df, metadata)


def _load_single_cut_file(path):
    col_names = ['vcr', 'recording_date', 'vcr_2', 'recording_date_2',
        'start', 'end', 'schedule', 'program']
    df = _load_csv_file(path, sep=r'\s+', names=col_names,
                       parse_dates={'cutpoint': ['recording_date', 'start']},
                       date_parser=_cut_date_parser)
    df.dropna()

    #leave the first and the last timestamp as they tend to be noisy
    #they may not be the trust program boundaries so it hinders the training.
    #TODO: a counter argument is that they are roughly right, since we suffer from
    #shortage of labelled boundaries so it may be more useful to keep them?
    df = df[['cutpoint', 'vcr', 'program']][1:]
    df = df.reset_index(drop=True)

    metadata = annotate_file(path)

    return (df, metadata)

def annotate_file(path):
    base = os.path.basename(path)
    filename, ext = os.path.splitext(base)
    filename_components = filename.split('_')
    if len(filename_components) == 9:            
        metadata = {
                       'filename': filename,
                       'filetype': ext,
                       'recording_end_date': filename_components[0],
                       'vcr_index': filename_components[4]
                    }
    else:
        print('corrupted filename: {}'.format(filename))
        # corrupted file name
        metadata = None
    return metadata

def load_files(root_path, file_extension='txt3', recursive_search=False):
    if not file_extension in ['txt3', 'cuts']:
        raise Exception('UnsupportedDataType')

    if root_path.endswith(file_extension):
        if file_extension == 'txt3':
            yield _load_single_caption_file(root_path)
        else:
            # TODO: caption filwee
            yield _load_single_cut_file(root_path)
    else:
        if not root_path.endswith('/'):
            root_path += '/'        
        root_path += '**/*.{}'.format(file_extension)

        filepaths = glob.iglob(root_path, recursive=recursive_search)
        if file_extension == 'txt3':        
            for path in filepaths:
                yield _load_single_caption_file(path)
        else:                
            for path in filepaths:
                yield _load_single_cut_file(path)


def load_caption_files(root_path, recursive_search=False):
    '''[summary]
    
    [description]
    
    Returns:
        [description]
        [type]
    '''
    return load_files(root_path, file_extension='txt3', recursive_search=True)


def load_program_cut_files(root_path, recursive_search=False):
    '''[summary]
    
    [description]
    
    Returns:
        [description]
        [type]
    '''
    return load_files(root_path, file_extension='cuts', recursive_search=True)


def find_matching_filepath(filename, filetype, search_path):    
    pattern = '{}/**/{}.{}'.format(search_path, filename, filetype)
    paths = glob.glob(pattern, recursive=True)
    
    if len(paths) > 1:
        print('duplicate files with matching caption filename')
    return paths[0]


def split_video_to_clips(start_time, end_time, interval):
    pass

def split_audio_to_clips(start_time, end_time, interval):
    pass

def split_caption_to_docs(X, interval=10):
    '''[summary]
    
    [description]
    
    should handle both types of caption (original, speech-recognized)
    
    Args:
        X: [description]
        interval: [in seconds] (default: {10 seconds})
    '''
    freq = '{}s'.format(interval)
    grouper = pd.Grouper(key='start',freq=freq)
    grouped = X.groupby(grouper)
    # TODO: this function takes too much time!
    def _combine_rows(X):
        # params = dict(start=X['start'].min(), 
        #               end=X['end'].max(), 
        #               caption=concat_caption)
        params = dict(caption=' '.join(X['caption'])) 
        return pd.Series(params)
    
    return grouped.apply(_combine_rows)

def convert_program_cuts_to_y(cuts, X, interval=10):    
    y = pd.DataFrame(X.index, columns=['start'])
    y['is_program_boundary'] = False
        
    interval = np.timedelta64(10, 's')
    cuts = cuts['cutpoint'].values
    # TODO: try a vectorized solution later on    
    for cut_time in cuts:
        mask = ((y['start']) <= cut_time) & (cut_time < (y['start'] + interval))
        y['is_program_boundary'] = y['is_program_boundary'] | mask

    return y