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

    def pop(self):
        if len(self.items) == 0:
            return None

        smallest = self.items[0]
        last = self.items.pop()

        if len(self.items) == 0:
            return smallest

        self.items[0] = last
        i = 0
        n = len(self.items)

        while True:
            left = 2*i +1
            right = 2*i +2

            if left >= n:
                break

            child = left
            if right < n and self.items[right][0] <self.items[left][0]:
                child = right

            if self.items[child][0] < self.items[i][0]:
                self.items[i], self.items[child] = self.items[child], self.items[i]
                i = child
            else:
                break

        return smallest