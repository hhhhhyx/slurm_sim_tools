from typing import Tuple

import os
import pandas as pd
import numpy as np

from slurmsim import log
import re
import datetime

def print_progress_bar(iteration, total, prefix='Progress:', suffix='Complete',
                        decimals=1, length=50, fill = '█', print_end ="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    # Print New Line on Complete
    if iteration == total:
        print()


SUPPORTED_COMPRESSION = ('.bz2','.lz4','.xz','.gz','.zstd', '.zst')


def get_file_open(filename):
    """
    Get open function depending on filename extention
    @param filename:
    @return: file open function
    """
    if os.path.splitext(filename)[-1] == '.bz2':
        import bz2
        m_open = bz2.open
    elif os.path.splitext(filename)[-1] == '.lz4':
        import lz4.frame
        m_open = lz4.frame.open
    elif os.path.splitext(filename)[-1] == '.xz':
        import lzma
        m_open = lzma.open
    elif os.path.splitext(filename)[-1] == '.gz':
        import gzip
        m_open = gzip.open
    elif os.path.splitext(filename)[-1] in ('.zstd', '.zst'):
        import zstandard as zstd
        m_open = zstd.open
    else:
        m_open = open
    return m_open


default_na_is = ['', 'Unknown', 'NA', 'NAN', 'NaN', 'NAT', 'NaT', 'nan']


def util_check_na(v: pd.Series, x: pd.Series,
                  na_is: Tuple[str] = None,
                  check_na: str = 'ignore'):
    """
    Check that NA values are true NA and not a result of miss-convertion

    @param v: original str pd.Series
    @param x: converted pd.Series
    @param check_na: check for NA
    @param na_is: tuple with valid NA value, if none use default: ('', 'Unknown', 'NA', 'NAN', 'NaN', 'NAT', 'NaT', 'nan')
    @param check_na: if ignore just return number of non valid values, warning - printwarning
           with non-valid values, error - raise error.
    @return:
    """
    if check_na == 'ignore':
        return
    if na_is is None:
        na_is = default_na_is
    non_valid = x.isna() & ~v.isin(na_is)
    num_of_non_valid = np.sum(non_valid)
    if num_of_non_valid:
        msg = (f"There are {num_of_non_valid} non valid NA entries (valid NA: {str(na_is)}).\n"\
               f"Non valid values: {str(np.unique(v[non_valid].values)[:20])}")
        if check_na == 'warning':
            log.warning(msg)
        elif check_na == 'error':
            log.error(msg)
            raise ValueError(msg)
    return num_of_non_valid


SI_SUFFIXES = {
    'binary': {
        '': 1,
        'k': 1024, 'm': 1024*1024, 'g': 1024*1024*1024, 't': 1024*1024*1024*1024, 'p': 1024*1024*1024*1024*1024, 'e': 1024*1024*1024*1024*1024*1024,
        'K': 1024, 'M': 1024*1024, 'G': 1024*1024*1024, 'T': 1024*1024*1024*1024, 'P': 1024*1024*1024*1024*1024, 'E': 1024*1024*1024*1024*1024*1024
    },
    'decimal': {
        '': 1,
        'k': 1000, 'm': 1000*1000, 'g': 1000*1000*1000, 't': 1000*1000*1000*1000, 'p': 1000*1000*1000*1000*1000, 'e': 1000*1000*1000*1000*1000*1000,
        'K': 1000, 'M': 1000*1000, 'G': 1000*1000*1000, 'T': 1000*1000*1000*1000, 'P': 1000*1000*1000*1000*1000, 'E': 1000*1000*1000*1000*1000*1000
    }}


def util_norm_si(v: pd.Series, convert_to_int=True, return_in='', check_na='ignore', na_is=None,
                 use1024=False) -> pd.Series:
    """
    Convert pd.Series[strings] containing nuber with SI suffixes like 12M, 2.4G and so on to pd.Series with numbers
    here m and M are both mega

    @param v: input
    @param return_in: return in units of return_in ('', k,M,G,...).
    @param convert_to_int: convert finale result to Int64
    @param check_na: check for NA
    @param na_is: valid Not Available strings, if None use default: ('', 'Unknown', 'NA', 'NAN', 'NaN', 'NAT', 'NaT')
    @param check_na_error: reaction on not valid not a number: ignore - do nothing, warning - print violations and
           error raise error
    @param use1024: use 1024 instead of 1000

    @return: pd.Series with convertednumbers
    """

    matches = v.str.extract("^([0-9.]+) ?([kmgtpeKMGTPE]?)$")
    if use1024:
        si_suffixes = SI_SUFFIXES['binary']
    else:
        si_suffixes = SI_SUFFIXES['decimal']
    matches[1].replace(to_replace=si_suffixes, inplace=True)
        
    x = pd.to_numeric(matches[0], errors='coerce')*pd.to_numeric(matches[1], errors='coerce')

    util_check_na(v, x, check_na=check_na, na_is=na_is)
    if return_in != '':
        if return_in not in si_suffixes:
            raise ValueError(f"Incorrect return_in values ({return_in})")
        x = x / si_suffixes[return_in]

    if convert_to_int:
        x = x.round().astype("Int64")
    return x


def util_memory(v: pd.Series, convert_to_int=True, return_in='',
                 check_na='ignore', na_is=None,
                 use1024=True) -> pd.Series:
    """
    Convert pd.Series[strings] containing slurm memory description like 1.5M 1.5Gn 1.5Gc.
    Suffix n for nodes suffix c for cpu, default per nodes

    @param v: input
    @param return_in: return in units of return_in ('', k,M,G,...).
    @param convert_to_int: convert finale result to Int64
    @param check_na: check for NA
    @param na_is: valid Not Available strings, if None use default: ('', 'Unknown', 'NA', 'NAN', 'NaN', 'NAT', 'NaT')
    @param check_na_error: reaction on not valid not a number: ignore - do nothing, warning - print violations and
           error raise error
    @param use1024: use 1024 instead of 1000

    @return: pd.Series with convertednumbers
    """
    matches = v.str.extract("^([0-9.]+ ?[kmgtpeKMGTPE]?)([cnCN]?)$")

    x = util_norm_si(matches[0], convert_to_int=convert_to_int, return_in=return_in,
                     check_na=check_na, na_is=na_is, use1024=use1024)
    c = matches[1].isin(('c','C'))
    return x, c


def util_to_int(v: pd.Series, check_na='ignore', na_is=None, round=False) -> pd.Series:
    x = pd.to_numeric(v, errors='coerce')
    if round:
        x = x.round()
    x = x.astype('Int64')
    util_check_na(v, x, check_na=check_na, na_is=na_is)
    return x

def util_to_float(v: pd.Series, check_na='ignore', na_is=None) -> pd.Series:
    x = pd.to_numeric(v, errors='coerce').astype('float64')
    util_check_na(v, x, check_na=check_na, na_is=na_is)
    return x

def util_to_str(v: pd.Series, check_na='ignore', na_is=None):
    return v


#unknown should be set to NA
def util_to_str_unk(v: pd.Series, check_na='ignore', na_is=None):
    return v


def util_factorize(v: pd.Series, check_na='ignore', na_is=None):
    x = v.astype(dtype='category')
    util_check_na(v, x, check_na=check_na, na_is=na_is)
    return x


def util_slurm_datetime_to_datetime(v: pd.Series, check_na='ignore', na_is=None) -> pd.Series:
    x = pd.to_datetime(v, errors='coerce').astype('datetime64[ns]')
    util_check_na(v, x, check_na=check_na, na_is=na_is)
    return x


def util_slurm_duration_to_timedelta(v: str) -> datetime.timedelta:
    """
    Slur, formats time formats include "minutes",
    "minutes:seconds", "hours:minutes:seconds", "days-hours", "days-hours:minutes" and "days-hours:minutes:seconds".
    @param v:
    @param check_na:
    @param na_is:
    @return:
    """
    # days-hours:minutes:seconds"
    m = re.match(r"^(\d+)-(\d+):(\d+):([0-9.]+)$", v)
    if m:
        return datetime.timedelta(days=int(m.group(1)), hours=int(m.group(2)), minutes=int(m.group(3)),seconds=float(m.group(4)))
    # days-hours:minutes
    m = re.match(r"^(\d+)-(\d+):(\d+)$", v)
    if m:
        return datetime.timedelta(days=int(m.group(1)), hours=int(m.group(2)), minutes=int(m.group(3)))
    # days-hours
    m = re.match(r"^(\d+)-(\d+)$", v)
    if m:
        return datetime.timedelta(days=int(m.group(1)), hours=int(m.group(2)))
    # hours:minutes:seconds
    m = re.match(r"^(\d+):(\d+):([0-9.]+)$", v)
    if m:
        return datetime.timedelta(hours=int(m.group(1)), minutes=int(m.group(2)),seconds=float(m.group(3)))
    # minutes:seconds
    m = re.match(r"^(\d+):([0-9.]+)$", v)
    if m:
        return datetime.timedelta(minutes=int(m.group(1)),seconds=float(m.group(2)))
    # minutes
    m = re.match(r"^(\d+)$", v)
    if m:
        return datetime.timedelta(minutes=int(m.group(1)))
    if v in default_na_is:
        return None
    else:
        raise Exception(f"Unknown format for slurm duration: {v}")


def util_slurm_duration_to_duration(v: pd.Series, check_na='ignore', na_is=None) -> pd.Series:
    """
    Slur, formats time formats include "minutes",
    "minutes:seconds", "hours:minutes:seconds", "days-hours", "days-hours:minutes" and "days-hours:minutes:seconds".
    @param v:
    @param check_na:
    @param na_is:
    @return:
    """
    v = v.str.replace(r"^(\d+)$", "\\1 m", regex=True)
    v = v.str.replace(r"^(\d+):([0-9.]+)$", "\\1 m \\2 S", regex=True)
    v = v.str.replace(r"^(\d+)-(\d+)$", "\\1 D \\2 h", regex=True)
    v = v.str.replace(r"^(\d+-\d+:\d+)$", "\\1:00", regex=True)
    v = v.str.replace("-", " days ")
    x = pd.to_timedelta(v, errors='coerce').astype('timedelta64[ns]')
    util_check_na(v, x, check_na=check_na, na_is=na_is)
    return x


def util_timedelta_to_slurm_duration(v: pd.Series) -> pd.Series:
    days = (v // pd.to_timedelta(1, unit='days')).astype("Int64")
    left = v % pd.to_timedelta(1, unit='D')
    hours = (left // pd.to_timedelta(1, unit='H')).astype("Int64")
    left = v % pd.to_timedelta(1, unit='H')
    minutes = (left // pd.to_timedelta(1, unit='min')).astype("Int64")
    left = v % pd.to_timedelta(1, unit='min')
    seconds = (left // pd.to_timedelta(1, unit='s')).astype("Int64")

    days = days.astype(str) + "-"
    days[days == "0-"] = ""

    s = days + hours.astype(str).str.zfill(2) + ":" + minutes.astype(str).str.zfill(2) + ":" + seconds.astype(
        str).str.zfill(2)
    s[v.isna()] = "NA"
    return s

ZSTD_LOC = None

def get_find_compressor(compression):
    if compression != "zstd":
        global ZSTD_LOC
        if ZSTD_LOC is None:
            # detect zstd
            out = subprocess.run(["which", "zstd"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            if out.returncode != 0:
                raise Exception("Can not find zstd binary, install it")
            ZSTD_LOC = out.stdout.strip()
            log.debug(f"zstd in {ZSTD_LOC}")
        return ZSTD_LOC
    else:
        raise NotImplementedError("only zstd implemented so far!")
def compress(filename, overwrite=False, compressor_loc=None, compression="zstd", keep=False, threads=None):
    """
    compress <filename> to <filename>.<std extention for that compression format>
    @param filename:
    @param overwrite:
    @param compressor_loc:
    @param compression:
    @return:
    """
    if compression != "zstd":
        raise NotImplementedError("only zstd implemented so far!")
    if compressor_loc is None:
        compressor_loc = get_find_compressor(compression)

    log.debug(f"compressing {filename}")
    if os.path.exists(f"{filename}.zst"):
        if self.overwrite:
            os.remove(f"{filename}.zst")
        else:
            log.error(f"Both file {filename} and it compressed version {filename}.zst exist."
                      f"The compressed might be incomplete. Delete it and try again!")
            raise FileExistsError()

    args = [
        compressor_loc,
        '-19']
    if not keep:
        args.append('--rm')

    args.append(f"-T{threads}")
    args.append(filename)

    out = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if out.returncode != 0:
        print(out.stdout)
        raise Exception(f"Can not compress {filename}!")

def decompress(filename, overwrite=False, compressor_loc=None, compression="zstd", keep=False,threads=None):
    if compression != "zstd":
        raise NotImplementedError("only zstd implemented so far!")
    if compressor_loc is None:
        compressor_loc = get_find_compressor(compression)

    log.debug(f"compressing {filename}")
    if os.path.exists(f"{filename}.zst"):
        if self.overwrite:
            os.remove(f"{filename}.zst")
        else:
            log.error(f"Both file {filename} and it compressed version {filename}.zst exist."
                      f"The compressed might be incomplete. Delete it and try again!")
            raise FileExistsError()

    args = [
        compressor_loc,
        '-19']
    if not keep:
        args.append('--rm')

    args.append(f"-T{self.threads_per_file}")
    args.append(filename)

    out = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if out.returncode != 0:
        print(out.stdout)
        raise Exception(f"Can not compress {filename}!")


def eval_shell_cmd(command, debug=False):
    import subprocess
    processes = command.split('|')

    if debug:
        print('Processes:', processes)

    for index, value in enumerate(processes):
        args = value.split(' ')

        if debug:
            print(index, args)

        if index == 0:
            p = subprocess.Popen(args, stdout=subprocess.PIPE)
        else:
            p = subprocess.Popen(args, stdin=p.stdout, stdout=subprocess.PIPE)

        if index == len(processes) - 1:
            result, error = p.communicate()
            return result.decode('utf-8'), error
