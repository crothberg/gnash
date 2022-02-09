import math

def entropy(prob_dist, base=math.e):
    return -sum([p * math.log(p,base) for p in prob_dist if p != 0])

# https://stats.stackexchange.com/questions/29578/jensen-shannon-divergence-calculation-for-3-prob-distributions-is-this-ok
def jenson_shannon_divergence(probDists, base=math.e, weights=None):
    weights = weights if weights else [1/len(probDists)]*len(probDists) #all same weight
    assert all(len(probDist)==len(probDists[0]) for probDist in probDists)
    jsLeft = [0]*len(probDists[0])
    jsRight = 0
    for pd, weight in zip(probDists, weights):
        for i in range(len(pd)): 
            jsLeft[i] += pd[i]*weight
        jsRight += weight*entropy(pd,base)
    return entropy(jsLeft)-jsRight
