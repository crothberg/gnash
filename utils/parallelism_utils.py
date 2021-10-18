from multiprocessing import Pool
# from multiprocessing.dummy import Pool
import redis

redisCache = redis.Redis(host='localhost', port=6379, db=0)

POOL_SIZE = 10#mp.cpu_count()-1

def chunks(lst, chunkSize=POOL_SIZE):
    for i in range(0, len(lst), chunkSize):
        yield lst[i:i+chunkSize]

def run_parallel(func, paramsForEachCall):
    with Pool(POOL_SIZE) as pool:
        pool.starmap(func, paramsForEachCall)
