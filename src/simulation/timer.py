from common.configuration import MODEL_START_TIME, MODEL_END_TIME, MODEL_TIME_STEP

class Timer:
    def __init__(self, start=MODEL_START_TIME, end=MODEL_END_TIME, step=MODEL_TIME_STEP):
        self.now = start
        self.end = end
        self.step = step
        self.iteration = 0

    @property
    def running(self):
        return self.now < self.end

    def advance(self):
        self.now += self.step
        self.iteration += 1
