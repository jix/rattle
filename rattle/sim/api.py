from .. import context
from ..signal import Signal
from ..type import Bool, Clock


def thread(action):
    context.current().sim.thread(action)
    return action


def on(event, action=None):
    def decorate(action):
        context.current().sim.thread(action, event)
        return action
    if action is None:
        return decorate
    else:
        return decorate(action)


def always_on(event, action=None):
    def decorate(action):
        def action_loop():
            while True:
                action()
                yield event
        context.current().sim.thread(action_loop, event)
        return action
    if action is None:
        return decorate
    else:
        return decorate(action)


def clock(target, period):
    if Signal.isinstance(target, Clock):
        target = target.clk
    if not Signal.isinstance(target, Bool):
        raise TypeError('clock requries a Clock or Bool signal')

    high_period = period // 2
    low_period = (period + 1) // 2

    @thread
    def _clock_thread():
        while True:
            target[:] = 1
            yield high_period
            target[:] = 0
            yield low_period


def time():
    return context.current().sim.time()


__all__ = [
    'thread',
    'on',
    'always_on',
    'clock',
    'time'
]
