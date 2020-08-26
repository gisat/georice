#!/usr/bin/env python
# coding: utf-8

import os
import sys
import gdal
import datetime as dt
import numpy as np
import rasterio as rio
import time
import math
import psutil
import numba
import osr
import gc
import signal

from osgeo import gdal_array
from rasterio.windows import Window
from skimage.morphology import remove_small_objects, remove_small_holes
from multiprocessing import Pool, freeze_support, cpu_count, process
from threading import Thread, Event
from platform import system

THREAD_POOL = None


def signal_handler(sig, frame):
    if THREAD_POOL is not None:
        THREAD_POOL.terminate()
    sys.exit(11)

# Catch SIGINT (ctrl+c) signal


signal.signal(signal.SIGINT, signal_handler)

# ----------------------------------------------------------------------------------------------------------------------
# georice related constants

# Threshold values for rice mapping classification
RICE_THRESHOLD_DB = 5.
urban_trees_threshold_dB = -18.
water_threshold_dB = -18.

# ----------------------------------------------------------------------------------------------------------------------
# data processing tweaks

# Block size when writing geotiff:
# - HAS TO BE a multiple of 16 (WARNING: no checks done, bad values will raise a gdal error)
# - this also represents the MINIMUM block size that can be processed
TIFF_BLOCK_SIZE = 1024

# Maximum block size to be processed at once
# => lowering this allows to reduce memory usage for large timescales
# => input rasters data will be processed in chunks of BLOCK_SIZE x BLOCK_SIZE pixels
# => more efficient if multiple of TIFF_BLOCK_SIZE (but not mandatory)
BLOCK_SIZE = TIFF_BLOCK_SIZE * 4

# ----------------------------------------------------------------------------------------------------------------------
# runtime constants, AVOID modifications here...

# number of parallel processing units
NUMBER_OF_THREADS = max(4, cpu_count() // 2 if cpu_count() < 16 else cpu_count() / 4)

# Each processed block is divided into sub-chunks of lines treated in parallel
# => this value is a hint to choose the most optimal number of sub-chunks  
# => if the block height allows it, this will be NUMBER_OF_THREADS x DATA_CHUNKS_MULTIPLIER
# => else block height / NUMBER_OF_THREADS
DATA_CHUNKS_MULTIPLIER = 128

# disable python garbage collector overhead
DISABLE_GARBAGE_COLLECTOR = False

# nodata / math constants
INF_NEG_FLOAT32 = np.float32(-np.inf)
INF_POS_FLOAT32 = np.float32(np.inf)

# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# utility functions & classes
# -- Memory / threads


def starmap(pool, methods, params, chunksize=1):
    pool = Pool(processes=2)
    return [pool.starmap(methods, params, chunksize)]

# compute total process memory usage, accounting for memory shared with all child processes


def memory_usage(process):
    try:
        if system() == 'Windows':
            mem = process.memory_full_info().rss
            for child in process.children(recursive=True):
                try:
                    mem += child.memory_full_info().uss
                except:
                    pass
        else:
            mem = process.memory_full_info().pss
            for child in process.children(recursive=True):
                try:
                    mem += child.memory_full_info().uss
                except:
                    pass
        return mem
    except:
        # maybe OS does not allow to query this information ?...
        return 0

# memory monitor thread


class MemoryMonitor(Thread):    
    def __init__(self, process, polling_delay):
        self.event = Event()
        self.polling_delay = polling_delay
        self.process = process
        self.memory = 0
        Thread.__init__(self)
        self.setDaemon(True)
    
    def stop(self):
        self.event.set()
    
    def run(self):
        while not self.event.is_set():
            self.memory = max(self.memory, memory_usage(self.process))
            time.sleep(self.polling_delay)
    
    def reset(self):
        self.memory = 0
    
    def get_peak_memory(self):
        return self.memory
    
    def get_peak_memory_gb(self):
        return self.memory / 1024**3

# -- GeoTIFF


def get_geotiff_infos(path):
    tmp_map = gdal.Open(path, gdal.GA_ReadOnly)
    metadata = tmp_map.GetMetadata()
    gcps = tmp_map.GetGCPs()
    projection = tmp_map.GetProjection()
    transform = list(tmp_map.GetGeoTransform())
    tmp_band = tmp_map.GetRasterBand(1)
    nodata = tmp_band.GetNoDataValue()
    compression = tmp_map.GetMetadata('IMAGE_STRUCTURE').get('COMPRESSION', None)
    blocksize = tmp_band.GetBlockSize()
    width, height = tmp_band.XSize, tmp_band.YSize
    epsg = osr.SpatialReference(wkt=projection).GetAttrValue('AUTHORITY', 1)
    tmp_band = None
    tmp_map = None
    return width, height, nodata, projection, transform, compression, blocksize, metadata, gcps, epsg

# save geotiff gdal helper


def saveToGTiff(
                npArray,
                dstFilePath,
                projection=None,
                transform=None,
                dstSRS=None,
                dtype=None,
                nodata=-np.inf,
                metadata=None,
                gcps=None,
                compressor=None,  # deflate, lzw, zstd, jpeg, webp
                comp_level=None,  # compression level
                extra_options=[], # Extra geotiff options like TILED, BLOCKXSIZE, BLOCKYSIZE, NBITS, ... 
                pos=[]            # Upper-left position of data (Warning: if set, disables dstSRS)
                ):
    # disable reprojection if data are saved in partial mode
    if pos is None or len(pos) == 0:
        pos = [0, 0]
        dshape = npArray.shape
    else:
        dstSRS = None
        dshape = pos[2]
    
    driver = gdal.GetDriverByName("GTiff")
    if dtype is None:
        dtype = npArray.dtype.type
    nodata = np.float64(-np.inf if nodata is None else nodata)
    gdal_dtype = gdal_array.NumericTypeCodeToGDALTypeCode(dtype)
    extra_opt = extra_options
    
    # setup compression
    if compressor is not None and type(compressor) is str and compressor.lower() != 'none':
        cl = compressor.lower()
        predictor = []
        # choose proper predictor : 3 if floating point data, else 2
        if cl in ['lzw', 'deflate', 'zstd'] and 'NBITS=1' not in extra_options:
            dummy = dtype(0.5)
            predictor = ['PREDICTOR=3'] if dummy == 0.5 else ['PREDICTOR=2']
        level = []
        if not comp_level is None:
            if cl == 'deflate':
                level = ['ZLEVEL=' + str(comp_level)]
            elif cl == 'zstd':
                level = ['ZSTD_LEVEL=' + str(comp_level)]
            elif cl == 'jpeg':
                level = ['JPEG_QUALITY=' + str(comp_level)]
            elif cl == 'webp':
                level = ['WEBP_LEVEL=' + str(comp_level)]
        extra_opt = ['COMPRESS=' + compressor.upper()] + predictor + level + ['NUM_THREADS=' + str(min(4, cpu_count()))] + extra_opt
    
    # Perform data reprojection if asked (only in full raster mode)
    if not (dstSRS is None or projection is None or transform is None):
        # https://stackoverflow.com/a/48706963
        org = gdal_array.OpenArray(npArray)
        org.SetProjection(projection)
        org.SetGeoTransform(transform)
        org.GetRasterBand(1).SetNoDataValue(nodata)
        if gcps is not None and len(gcps) > 0:
            org.SetGCPs(gcps)
        dest = gdal.Warp('', org, dstSRS=dstSRS, format="VRT", outputType=gdal_dtype)
        projection = dest.GetProjection()
        transform = dest.GetGeoTransform()
        npArray = dest.ReadAsArray()
        dshape = npArray.shape
        gcps = dest.GetGCPs()
    
    dst_ds = driver.Create(dstFilePath, dshape[1], dshape[0], 1, gdal_dtype, options=extra_opt)
    if metadata is not None:
        dst_ds.SetMetadata(metadata)
    if gcps is not None and len(gcps) > 0:
        dst_ds.SetGCPs(gcps)
    dst_ds.GetRasterBand(1).SetNoDataValue(nodata)
    if projection is not None:
        dst_ds.SetProjection(projection)
    if transform is not None:
        dst_ds.SetGeoTransform(transform)
    
    dst_ds.GetRasterBand(1).WriteArray(npArray, pos[0], pos[1])
    dst_ds.FlushCache()
    dst_ds = None

# partial update of geotiff
def updateGTiff(npArray, dstFilePath, pos=[]):
    dst_ds = gdal.Open(dstFilePath, gdal.GA_Update)
    if pos is None or len(pos) == 0:
        pos = [0, 0]
    dst_ds.GetRasterBand(1).WriteArray(npArray, pos[0], pos[1])
    dst_ds.FlushCache()
    dst_ds = None

#--- dates

# gregorian date to julian helper (https://gist.github.com/jiffyclub/1294443)
def date_to_jd(year,month,day):
    if month == 1 or month == 2:
        yearp = year - 1
        monthp = month + 12
    else:
        yearp = year
        monthp = month
    
    # this checks where we are in relation to October 15, 1582, the beginning
    # of the Gregorian calendar.
    if ((year < 1582) or
        (year == 1582 and month < 10) or
        (year == 1582 and month == 10 and day < 15)):
        # before start of Gregorian calendar
        B = 0
    else:
        # after start of Gregorian calendar
        A = math.trunc(yearp / 100.)
        B = 2 - A + math.trunc(A / 4.)
    
    if yearp < 0:
        C = math.trunc((365.25 * yearp) - 0.75)
    else:
        C = math.trunc(365.25 * yearp)
    
    D = math.trunc(30.6001 * (monthp + 1))
    jd = B + C + D + day + 1720994.5
    return jd

YEAR_0 = date_to_jd(0, 1, 1)

# helper function to emulate matlab julian day from first day of year 0
def date_to_jd_from_year_0(datetime64_or_year, month=None, day=None):
    global YEAR_0
    if type(datetime64_or_year) is dt.date:
        return date_to_jd(datetime64_or_year.year, datetime64_or_year.month, datetime64_or_year.day) - YEAR_0
    elif type(datetime64_or_year) is np.datetime64:
        dd = dt.datetime.utcfromtimestamp(datetime64_or_year.astype(object)/1e9)
        return date_to_jd(dd.year, dd.month, dd.day) - YEAR_0
    else:
        return date_to_jd(datetime64_or_year, month, day) - YEAR_0

# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# processing functions

def rice_mapping(temporal_mean, temporal_max_increase, temporal_min, temporal_max, rice_threshold_dB):
    # Define the classes
    class_type={"no_data":0, "rice":1, "urban_tree":2, "water":3, "other":4}
    
    holes_threshold = 20
    holes_connectivity = 2
    objects_threshold = 20
    objects_connectivity = 2
    
    ricemap = np.full(temporal_mean.shape, class_type["no_data"], dtype=np.uint8)
    
    # Apply threshold to the 0 value => no data
    ma = temporal_mean > 0
    remove_small_objects(ma, min_size=objects_threshold, in_place=True, connectivity=objects_connectivity)
    remove_small_holes(ma, area_threshold=holes_threshold, in_place=True, connectivity=holes_connectivity)
    ricemap[ma] = class_type["other"]
    
    # Apply threshold to the temporal maximum increase => Rice
    ma = temporal_max_increase > 10**(rice_threshold_dB/10.)
    remove_small_objects(ma, min_size=objects_threshold, in_place=True, connectivity=objects_connectivity)
    remove_small_holes(ma, area_threshold=holes_threshold, in_place=True, connectivity=holes_connectivity)
    ricemap[ma] = class_type["rice"]
    
    # Apply threshold to the temporal minimum value => Urban or forest
    ma = temporal_min > 10**(urban_trees_threshold_dB/10.)
    remove_small_objects(ma, min_size=objects_threshold, in_place=True, connectivity=objects_connectivity)
    remove_small_holes(ma, area_threshold=holes_threshold, in_place=True, connectivity=holes_connectivity)
    ricemap[ma] = class_type["urban_tree"]
    
    # Apply threshold to the temporal max value => Water
    ma = temporal_max < 10**(water_threshold_dB/10.)
    remove_small_objects(ma, min_size=objects_threshold, in_place=True, connectivity=objects_connectivity)
    remove_small_holes(ma, area_threshold=holes_threshold, in_place=True, connectivity=holes_connectivity)
    ricemap[ma] = class_type["water"]
    
    return ricemap

# ----------------------------------------------------------------------------------------------------------------------
# numba processing functions

@numba.jit(nopython=True, nogil=True, fastmath=False)
def min_argmin(a):
    vmin, imin = a[0], 0
    for i, v in enumerate(a):
        if v < vmin and not (np.isinf(v) or np.isnan(v)):
            vmin, imin = v, i
    return vmin, imin

@numba.jit(nopython=True, nogil=True, fastmath=False)
def min_(a):
    vmin = a[0]
    for i, v in enumerate(a):
        if v < vmin and not (np.isinf(v) or np.isnan(v)):
            vmin = v
    return vmin

@numba.jit(nopython=True, nogil=True, fastmath=False)
def max_(a):
    vmax = a[0]
    for i, v in enumerate(a):
        if v > vmax and not (np.isinf(v) or np.isnan(v)):
            vmax = v
    return vmax

@numba.jit(nopython=True, nogil=True, fastmath=False)
def mean_(a):
    s, cnt = 0, 0
    for i, v in enumerate(a):
        if not np.isinf(v) and not np.isnan(v):
            s += v
            cnt += 1
    return s / cnt if cnt > 0 else np.nan

@numba.jit(nopython=True, nogil=True, fastmath=False)
def global_statistics(vh, time_0):
    h, w = vh.shape[0:2]
    out_mean = np.zeros((h, w), dtype=np.float32)
    out_incr = np.zeros((h, w), dtype=np.float32)
    out_min = np.zeros((h, w), dtype=np.float32)
    out_max = np.zeros((h, w), dtype=np.float32)
    for y in range(h):
        for x in range(w):
            mean_vh, incr_vh, min_vh, max_vh = 0, 0, INF_NEG_FLOAT32, INF_POS_FLOAT32
            pixel_vh = vh[y, x, :]
            # consider only pixels >= -29dB
            db_filter_ids = np.where(pixel_vh > 0.0013)[0]
            if len(db_filter_ids) > 0:
                vh_tmp = pixel_vh[db_filter_ids]
                mean_vh, max_vh, min_vh = mean_(vh_tmp), max_(vh_tmp), min_(vh_tmp)
                # find temporal max increase
                if len(vh_tmp) > 1:
                    t0_tmp = time_0[db_filter_ids]
                    temporal_min, temporal_min_index = min_argmin(vh_tmp[:len(vh_tmp)//2])
                    # the max is located at least 20 days after the min
                    vh_select = vh_tmp[np.where(t0_tmp >= (t0_tmp[temporal_min_index] + 20))[0]]
                    if len(vh_select) > 0:
                        incr_vh = max_(vh_select) / temporal_min
            out_mean[y, x] = mean_vh
            out_incr[y, x] = incr_vh
            out_min[y, x] = min_vh
            out_max[y, x] = max_vh
    return out_mean, out_incr, out_min, out_max

# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

def cmd_help():
    script_name = sys.argv[0].split('/')[-1]
    spc = ' ' * len(script_name)
    print()
    print("   ", script_name, "data_path")
    print("   ",         spc, "orbit")
    print("   ",         spc, "starting_date")
    print("   ",         spc, "ending_date")
    print("   ",         spc, "output_path")
    print("   ",         spc, "[-d direction]")
    print("   ",         spc, "[-i]")
    print("   ",         spc, "[-lzw]")
    print("   ",         spc, "[-m]")
    print("   ",         spc, "[-nr]")
    print("   ",         spc, "[-t number_of_threads]")
    print("   ",         spc, "[-tr rice,trees,water]")
    print("   ",         spc, "[-txxx mode]")
    print()
    print("    NOTE: starting_date / ending_date => YYYYMMDD, inclusive")
    print()
    print("    --- Optional parameters ---")
    print()
    print("    -d direction           : default DES => direction (ASC / DES)")
    print("    -i                     : write intermediate products (min/max/mean/max_increase)")
    print("    -lzw                   : write output tiff products using LZW compression instead of DEFLATE (compatibility with ENVI/IDL)")
    print("    -m                     : generate and write rice, trees, water, other and nodata masks")
    print("    -nr                    : disable automatic reprojection to EPSG:4326")
    print("    -t number_of_threads   : default %d (host dependant) => number of parallel processing units"%NUMBER_OF_THREADS)
    print("    -tr rice,trees,water   : default %d,%d,%d => rice/trees/water thresholds (dB)"%(RICE_THRESHOLD_DB, urban_trees_threshold_dB, water_threshold_dB))
    print("    -txxx mode             : default all => input raster selection mode: 'txxx', 'nontxxx' or 'all'")
    print()

if __name__ == '__main__':
    freeze_support()
    
    process = psutil.Process(os.getpid())
    
    # parameters handling
    if len(sys.argv) < 7:
        cmd_help()
        sys.exit(1)
    
    COMPRESSOR = 'deflate'
    all_products = False
    extra_products = False
    DATA_CHUNKS = 0
    txxx_mode ='all'
    
    data_path = sys.argv[1]
    desiredorbit = sys.argv[2]
    starting_date = sys.argv[3]
    ending_date = sys.argv[4]
    output_path = sys.argv[5]
    part = sys.argv[6]
    desireddirection = 'DES'
    dstSRS = 'EPSG:4326'
    masks = False
    
    i = 6
    while i < len(sys.argv):
        if sys.argv[i] == '-d' or sys.argv[i] == '--direction':
            i += 1
            desireddirection = str(sys.argv[i]).upper()
        elif sys.argv[i] == '-i' or sys.argv[i] == '--intermediate-products':
            all_products = True
        elif sys.argv[i] == '-lzw' or sys.argv[i] == '--lzw':
            COMPRESSOR = 'lzw'
        elif sys.argv[i] == '-m' or sys.argv[i] == '--masks':
            masks = True
        elif sys.argv[i] == '-nr' or sys.argv[i] == '--no-reproject':
            dstSRS = None
        elif sys.argv[i] == '-t' or sys.argv[i] == '--threads':
            i += 1
            NUMBER_OF_THREADS = int(sys.argv[i])
        elif sys.argv[i] == '-tr' or sys.argv[i] == '--threshold':
            i += 1
            RICE_THRESHOLD_DB, urban_trees_threshold_dB, water_threshold_dB = [float(v) for v in sys.argv[i].split(',')]
        elif sys.argv[i] == '-txxx':
            i += 1
            txxx_mode = sys.argv[i]
        i += 1
    
    # Extracting desired data according to parameters
    list_of_raster_vh = []
    list_of_datetime_vh = []
    orbit, orbitdir, polar, date = None, None, None, None
    
    date_start = dt.datetime.strptime(starting_date, '%Y%m%d').date()
    date_end = dt.datetime.strptime(ending_date, '%Y%m%d').date()
    
    print()
    print("- Orbit: " + desiredorbit)
    print("- Direction: " + desireddirection)
    print("- From " + date_start.strftime("%d, %b %Y") + " to " + date_end.strftime("%d, %b %Y"))
    
    try:
        for file in next(os.walk(data_path))[2]:
            print(file)
            # accept only sentinel-1 filtered images
            accept_file = file.startswith('S1') and file.endswith('.tif')
            print(accept_file)
            # accept_file = file.startswith('s1') and file.endswith('_filtered.tif')
            # if txxx_mode == 'txxx':
            #     print(txxx_mode)
            #     accept_file = accept_file and ('txxxxxx' in file)
            # if txxx_mode == 'nontxxx':
            #     accept_file = accept_file and ('txxxxxx' not in file)
            if accept_file:
                print(file.split('_'))
                file_split = file.split('_')
                orbit = file_split[4]
                orbitdir = file_split[3]
                polar = file_split[2]
                polar = polar.lower()
                print(orbit)
                print(polar)
                # date = file_split[5][:8]
                date = file_split[5][:8]
                date = dt.datetime.strptime(date, '%Y%m%d').date()
                print(orbit)
                print(polar)
                print(date)
                if (orbit == desiredorbit) and (orbitdir == desireddirection) and (polar == 'vh') and (date_start <= date <= date_end):
                    # handle duplicated dates
                    if date in list_of_datetime_vh:
                        id = list_of_datetime_vh.index(date)
                        current = list_of_raster_vh[id]
                        if txxx_mode in ['txxx','nontxxx']:
                            print("  [vh] duplicate @ " + str(date) + " => keeping last modified: (" + file + " / " + current + ")")
                            if os.path.getmtime(os.path.join(data_path, file)) > os.path.getmtime(os.path.join(data_path, current)):
                                list_of_raster_vh[id] = file
                        else:
                            print("  [vh] duplicate @ " + str(date) + " => keeping (1)txxxxxx (2)last modified: (" + file + " / " + current + ")")
                            if ('txxxxxx' in file and 'txxxxxx' in current) or (not 'txxxxxx' in file and not 'txxxxxx' in current):
                                if os.path.getmtime(os.path.join(data_path, file)) > os.path.getmtime(os.path.join(data_path, current)):
                                    list_of_raster_vh[id] = file
                            elif 'txxxxxx' in file:
                                list_of_raster_vh[id] = file
                    else:
                        list_of_raster_vh.append(file)
                        list_of_datetime_vh.append(date)
    except:
        print()
        print('Error: folder', data_path,'seems empty...')
        print()
        sys.exit(1)
    
    if len(list_of_raster_vh) == 0:
        print()
        print('Error: unable to find data fitting the selected time period / orbit / direction / ...')
        print()
        sys.exit(1)
    
    # gather some informations about products to prefix output data files
    product = list_of_raster_vh[0].split('_')
    output_suffix_short = '_' + product[1] + '_' + product[3] + '_' + product[4]
    output_suffix = output_suffix_short + '_' + starting_date + '_' + ending_date + '.tif'
    
    # Sorting data in a chronological order
    a = np.empty((len(list_of_raster_vh),2), dtype=object)
    for i in range(len(list_of_raster_vh)):
        a[i,0] = list_of_raster_vh[i]
        a[i,1] = list_of_datetime_vh[i]
    list_of_raster_vh = a[np.argsort(a[:,1]),:]
    
    # ------------------------------------------------------------------------------------------------------------------
    # initialize processing
    
    # output_path = os.path.join(output_path, product[1], 'ricemaps') # org

    output_path = os.path.join(output_path, 'ricemaps')

    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    if NUMBER_OF_THREADS <= 0:
        NUMBER_OF_THREADS = 2
    if DATA_CHUNKS <= 0 and NUMBER_OF_THREADS > 1:
        DATA_CHUNKS = NUMBER_OF_THREADS * DATA_CHUNKS_MULTIPLIER
    
    # gathering informations from 1st date geotiff (to be replicated in output geotiff)
    full_width, full_height, nodata, projection, transform, compression, blocksize, _, _, epsg = get_geotiff_infos(os.path.join(data_path, list_of_raster_vh[0,0]))
    depth = len(list_of_raster_vh)
    
    # check processing block size and set data shape
    if BLOCK_SIZE < TIFF_BLOCK_SIZE:
        BLOCK_SIZE = TIFF_BLOCK_SIZE
    x_pos, y_pos = 0, 0
    width, height = BLOCK_SIZE, BLOCK_SIZE
    full_shape = [full_height, full_width]
    
    # handle output tiff options
    if TIFF_BLOCK_SIZE >= 16:
        GEOTIFF_OPTIONS = ['TILED=YES', 'BLOCKXSIZE='+str(TIFF_BLOCK_SIZE),'BLOCKYSIZE='+str(TIFF_BLOCK_SIZE)]
    else:
        GEOTIFF_OPTIONS = ['TILED=NO']
    
    # create time scale in Jd relative to day 1 of year 0
    time_0 = np.array([int(date_to_jd_from_year_0(list_of_raster_vh[t,1])) for t in range(len(list_of_raster_vh))])
    
    print("- Time scale (julian days, since day 1 of year 0): %d dates, %d -> %d"%(len(time_0), time_0[0], time_0[-1]))
    print("- Threads:", NUMBER_OF_THREADS)
    
    # # create processing units pool
    # THREAD_POOL = Pool(NUMBER_OF_THREADS)
    
    # memory monitor thread
    monitor = MemoryMonitor(process, 1)
    monitor.start()
    
    # ------------------------------------------------------------------------------------------------------------------
    
    NUMBER_OF_CHUNKS = max(1, min(height//NUMBER_OF_THREADS, DATA_CHUNKS))
    
    # number of BLOCK_SIZExBLOCK_SIZE to process
    NB_BLOCKS_X = max(1, 1 + full_width // BLOCK_SIZE)
    NB_BLOCKS_Y = max(1, 1 + full_height // BLOCK_SIZE)
    X_BLOCKS = [i*BLOCK_SIZE for i in range(NB_BLOCKS_X)] + [full_width]
    Y_BLOCKS = [i*BLOCK_SIZE for i in range(NB_BLOCKS_X)] + [full_height]
    
    if DISABLE_GARBAGE_COLLECTOR:
        gc.disable()
    
    # allocate dataset
    cube_shape = [BLOCK_SIZE, BLOCK_SIZE, depth]
    S1_dataset_vh = np.zeros(cube_shape, dtype=np.float32)
    temporal_mean = np.zeros(full_shape, dtype=np.float32)
    temporal_max_increase = np.zeros(full_shape, dtype=np.float32)
    temporal_min = np.zeros(full_shape, dtype=np.float32)
    temporal_max = np.zeros(full_shape, dtype=np.float32)
    
    start_time = time.time()
    
    print()
    print("Gathering data statistics for whole time scale", end=' ', flush=True)
    
    for x_block in range(NB_BLOCKS_X):
        for y_block in range(NB_BLOCKS_Y):
            
            print('%d/%d'%(x_block*NB_BLOCKS_Y+y_block+1, NB_BLOCKS_X*NB_BLOCKS_Y), end=' ', flush=True)
            x_pos, y_pos = X_BLOCKS[x_block], Y_BLOCKS[y_block]
            width = min(BLOCK_SIZE, X_BLOCKS[x_block+1] - x_block*BLOCK_SIZE)
            height = min(BLOCK_SIZE, Y_BLOCKS[y_block+1] - y_block*BLOCK_SIZE)
            NUMBER_OF_CHUNKS = int(NUMBER_OF_CHUNKS)
            lines = [(i*height)//NUMBER_OF_CHUNKS for i in range(NUMBER_OF_CHUNKS)] + [height]
            
            # load vh data
            for i, f in enumerate(list_of_raster_vh[:, 0]):
                S1_dataset_vh[:height, :width, i] = rio.open(os.path.join(data_path, f)).read(1, window=Window(x_pos, y_pos, width, height))[:,:]
            
            # gather statistics (temporal min, max, mean, max_increase) over the whole time scale
            params = []
            for i in range(NUMBER_OF_CHUNKS):
                p = [ S1_dataset_vh[lines[i]:lines[i+1], :width, :len(time_0)], time_0 ]
                params.append(p)
            results = starmap(THREAD_POOL, global_statistics, params)[0]
            for i, r in enumerate(results):
                c0, cn = x_pos, x_pos + width
                l0, ln = y_pos+lines[i], y_pos+lines[i+1]
                temporal_mean[l0:ln, c0:cn] = r[0]
                temporal_max_increase[l0:ln, c0:cn] = r[1]
                temporal_min[l0:ln, c0:cn] = r[2]
                temporal_max[l0:ln, c0:cn] = r[3]
            
            # ------------------------------------------------------------------------------------------------------------------
    
    print()
    print("Building rice map")
    S1_dataset_ricemap = rice_mapping(temporal_mean, temporal_max_increase, temporal_min, temporal_max, RICE_THRESHOLD_DB)
    
    print("Writing output product(s)")

    file = os.path.join(output_path, 'ricemap'+output_suffix)
    saveToGTiff(S1_dataset_ricemap, file, projection, transform, dstSRS, None, 0, None, None, COMPRESSOR, None, GEOTIFF_OPTIONS)
    if all_products:
        file = os.path.join(output_path, 'temporalMean'+output_suffix)
        saveToGTiff(temporal_mean, file, projection, transform, dstSRS, None, None, None, None, COMPRESSOR, None, GEOTIFF_OPTIONS)
        file = os.path.join(output_path, 'temporalMaxIncrease'+output_suffix)
        saveToGTiff(temporal_max_increase, file, projection, transform, dstSRS, None, None, None, None, COMPRESSOR, None, GEOTIFF_OPTIONS)
        file = os.path.join(output_path, 'temporalMin'+output_suffix)
        saveToGTiff(temporal_min, file, projection, transform, dstSRS, None, None, None, None, COMPRESSOR, None, GEOTIFF_OPTIONS)
        file = os.path.join(output_path, 'temporalMax'+output_suffix)
        saveToGTiff(temporal_max, file, projection, transform, dstSRS, None, None, None, None, COMPRESSOR, None, GEOTIFF_OPTIONS)
    
    if masks:
        mask = np.ones(S1_dataset_ricemap.shape, dtype=np.uint8)
        file_out = os.path.join(output_path, 'mask_nodata'+output_suffix)
        saveToGTiff(mask * (S1_dataset_ricemap == 0), file_out, projection, transform, dstSRS, None, 0, None, None, COMPRESSOR, None, ['NBITS=1']+GEOTIFF_OPTIONS)
        file_out = os.path.join(output_path, 'mask_rice'+output_suffix)
        saveToGTiff(mask * (S1_dataset_ricemap == 1), file_out, projection, transform, dstSRS, None, 0, None, None, COMPRESSOR, None, ['NBITS=1']+GEOTIFF_OPTIONS)
        file_out = os.path.join(output_path, 'mask_trees'+output_suffix)
        saveToGTiff(mask * (S1_dataset_ricemap == 2), file_out, projection, transform, dstSRS, None, 0, None, None, COMPRESSOR, None, ['NBITS=1']+GEOTIFF_OPTIONS)
        file_out = os.path.join(output_path, 'mask_water'+output_suffix)
        saveToGTiff(mask * (S1_dataset_ricemap == 3), file_out, projection, transform, dstSRS, None, 0, None, None, COMPRESSOR, None, ['NBITS=1']+GEOTIFF_OPTIONS)
        file_out = os.path.join(output_path, 'mask_other'+output_suffix)
        saveToGTiff(mask * (S1_dataset_ricemap == 4), file_out, projection, transform, dstSRS, None, 0, None, None, COMPRESSOR, None, ['NBITS=1']+GEOTIFF_OPTIONS)
    
    print()
    print("Rice classification completed... Δt = %.6s seconds" % (time.time() - start_time))
    print('Memory peak: %.3fG'%monitor.get_peak_memory_gb())
    print()
    monitor.stop()
    
    if DISABLE_GARBAGE_COLLECTOR:
        gc.collect()
        gc.enable()
    # THREAD_POOL.terminate()

