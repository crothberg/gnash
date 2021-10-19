# #Uncomment for multiprocessing
from multiprocessing import Pool as MpPool, cpu_count
# MP_POOL_SIZE = cpu_count()

#Uncomment for threading
from multiprocessing.dummy import Pool as ThreadPool
THREAD_POOL_SIZE = cpu_count()

# NO_MULTIPROCESSING = True
NO_THREADING = False
# if NO_THREADING: assert NO_MULTIPROCESSING

# class RedisCache:
#     cache = Redis(host='localhost', port=6379, db=0)
#     nextKey = 500
#     def get_unique_redis_key():
#         return str(random.random())
#         # key = RedisCache.nextKey
#         # RedisCache.nextKey = key + 1
#         # return str(key)
# def set_temp_dict(d, key=None):
#     # print("Setting...")
#     key = key or RedisCache.get_unique_redis_key()
#     RedisCache.cache.set(key, json.dumps(d))
#     # print("Set!")
#     return key
# def get_temp_dict(key):
#     # print("Getting")
#     result = json.loads(RedisCache.cache.get(key))
#     # print("Got")
#     return result
# def lock(key):
#     locked = RedisCache.cache.lock(key + "_lock")
#     return locked
def clean_up():
    return
    # RedisCache.cache.flushdb()

def _chunks(lst, chunkSize):
    for i in range(0, len(lst), chunkSize):
        yield lst[i:i+chunkSize]

def _run_func_in_threads(func, paramsForEachCall):
    with ThreadPool(THREAD_POOL_SIZE) as threadpool:
        threadpool.starmap(func, paramsForEachCall)

def run_parallel(func, paramsForEachCall, threadingOnly = True):
    # if len(paramsForEachCall) > 100 and not threadingOnly and not NO_MULTIPROCESSING:
    #     bigChunks = list(_chunks(paramsForEachCall, chunkSize=len(paramsForEachCall)//MP_POOL_SIZE+1))
    #     with MpPool(MP_POOL_SIZE) as mppool:
    #         mppool.starmap(_run_func_in_threads, list((func, chunk) for chunk in bigChunks))
    if not NO_THREADING:
        _run_func_in_threads(func, paramsForEachCall)
    else:
        for paramForCall in paramsForEachCall:
            func(*paramForCall)