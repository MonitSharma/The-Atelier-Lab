def normalize_records(records):
    return [{"name": row["name"].strip(), "score": row["score"]} for row in records]


def passing_records(records, threshold=0.5):
    return [row for row in records if row["score"] > threshold]
