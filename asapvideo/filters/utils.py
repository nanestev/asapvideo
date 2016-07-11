"""
    Returns every two elements from collection
"""
def pairwise(it):
    it = iter(it)
    while True:
        yield next(it), next(it)