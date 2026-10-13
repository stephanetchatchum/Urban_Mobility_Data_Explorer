class MinHeap:
    def __init__(self):
        self.items = []

    def push(self, item):
        self.items.append(item)
        i = len(self.items)-1

        while i > 0:
            parent = (i -1) //2
            if self.items[i][0] < self.items[parent][0]:
                self.items[i], self.items[parent] = self.items[parent], self.items[i]
                i = parent
            else:
                break