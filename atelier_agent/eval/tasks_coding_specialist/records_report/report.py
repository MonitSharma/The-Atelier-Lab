from records import normalize_records, passing_records


def summarize(records, threshold=0.5):
    rows = normalize_records(records)
    passing = passing_records(rows, threshold)
    return {"count": len(rows), "passing": len(passing), "average": sum(row["score"] for row in rows) / len(rows)}
