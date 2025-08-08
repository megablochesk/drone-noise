from common.model_configs import model_config

class Timer:
    def __init__(
            self,
            start=model_config.time.start_s,
            end=model_config.time.end_s,
            step=model_config.time.step_s
    ):
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
