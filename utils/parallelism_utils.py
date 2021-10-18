#Uncomment for multiprocessing
from multiprocessing import Pool, cpu_count
POOL_SIZE = cpu_count()-1

# #Uncomment for threading
# from multiprocessing.dummy import Pool
# POOL_SIZE = 100

def chunks(lst, chunkSize=POOL_SIZE):
    for i in range(0, len(lst), chunkSize):
        yield lst[i:i+chunkSize]

def run_parallel(func, paramsForEachCall):
    with Pool(POOL_SIZE) as pool:
        pool.starmap(func, paramsForEachCall)
