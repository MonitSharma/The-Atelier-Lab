class Store:
    def __init__(self, rows):
        self.rows = list(rows)

    def find(self, query):
        return [row for row in self.rows if query in row["title"]]
