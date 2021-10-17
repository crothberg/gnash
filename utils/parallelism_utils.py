from multiprocessing import Pool
# from multiprocessing.dummy import Pool

POOL_SIZE = 100#mp.cpu_count()-1

def chunks(lst, chunkSize=POOL_SIZE):
    for i in range(0, len(lst), chunkSize):
        yield lst[i:i+chunkSize]

def run_parallel(func, paramsForEachCall):
    with Pool(POOL_SIZE) as pool:
        pool.starmap(func, paramsForEachCall)
