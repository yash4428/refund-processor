from refunds.csv_reader import read_requests


def test_reads_all_rows():
    rows = read_requests("data/refund_requests.csv")
    assert len(rows) == 18
    assert rows[0]["request_id"] == "req_001"
    assert rows[0]["charge_id"] == "ch_0001"
