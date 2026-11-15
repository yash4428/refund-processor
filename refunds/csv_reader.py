import csv


def read_requests(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))
