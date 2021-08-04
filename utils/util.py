def normalize(dist):
    total = sum(dist.values())
    for e in dist:
        dist[e] /= total
    return dist