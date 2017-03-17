from collections import OrderedDict
from queue import PriorityQueue, Empty
from .engine import SimEngine
from .event import *
from ..bitmath import log2up
from ..bitvec import BitVec, XClass, xnot
from ..primitive import PrimConst, PrimTable, PrimIndex
from ..error import InvalidSignalAssignment
from ..signal import Signal
from ..type import Clock
from .. import context


class SimContext:
    # pylint: disable=attribute-defined-outside-init
    def __init__(self, module):
        module._module_data.circuit.finalize()

        self._module = module
        self._engine = SimEngine(module)

        self.reset(_reset_engine=False)

    def reset(self, *, _reset_engine=True):
        if _reset_engine:
            self._engine.reset()

        self._threads = set()
        self._watched_events = {}
        self._new_events = []

        self._old_values = {}

        self._potential_changes = OrderedDict()
        self._potential_edges = OrderedDict()

        self._future_events_queue = PriorityQueue()

        self._pending_threads = OrderedDict()

        self._activity = False
        self._shadow = None

        self._busy_count = 0
        self._idle = False
        self._stop = False

        self._discover_sim_inits(self._module)

    def activate(self):
        return context.current().activate_sim_context(self)

    def time(self):
        return self._engine.time

    def peek(self, signal):
        const_prims = {}

        for key, prim in signal._prims.items():
            const_prims[key] = self._peek_prim(prim.simplify_read())

        return signal.signal_type._from_prims(const_prims)

    def _peek_prim(self, prim):
        if not prim.dimensions:
            return PrimConst(self._engine.peek(prim))
        else:
            size = prim.dimensions[-1]
            index_width = log2up(size)
            return PrimTable([
                self._peek_prim(
                    PrimIndex(PrimConst(BitVec(index_width, i)), prim))
                for i in range(size)])

    def _poke_prim(self, lvalue, rvalue):
        if lvalue.allowed_writers == set():
            raise InvalidSignalAssignment  # TODO Message

        rvalue = self._peek_prim(rvalue.simplify_read())

        pokes = []

        for assignment in lvalue.lower_assignment((), rvalue):
            storage, lvalue, condition, rvalue = assignment
            condition = self._eval_condition(condition)
            rvalue = self._engine.peek(rvalue)

            if condition is not False:
                xpoke = isinstance(condition, XClass)
                pokes.append([storage, lvalue, rvalue, xpoke])

        for storage, poke_lvalue, poke_rvalue, xpoke in pokes:
            storage.poke_to_sim(self, poke_lvalue, poke_rvalue, xpoke)

    def _eval_condition(self, condition):
        result = True
        for pol, test in condition:
            test = self._engine.peek(test)[0] ^ xnot(pol)
            result &= test
            if result is False:
                break
        return result

    def _poke(self, storage, lvalue, rvalue, xpoke):
        self._engine.poke(
            storage.simplify_read(), lvalue, rvalue,
            xpoke=xpoke, shadow=self._shadow)

    def thread(self, action, events=None):
        events = self._prepare_events(events)
        thread = SimThread(action, events)

        self._threads.add(thread)

        for event in events:
            self._watch_event(event, thread)

        return thread

    def _watch_event(self, event, thread):
        try:
            watchlist = self._watched_events[event]
        except KeyError:
            watchlist = self._watched_events[event] = OrderedDict()
            self._new_events.append(event)
        watchlist[thread] = thread

    def _unwatch_event(self, event, thread):
        watchlist = self._watched_events[event]
        del watchlist[thread]

    def _trigger_thread(self, thread):
        self._activity = True
        old_events = thread._events

        if callable(thread._action):
            thread._action = thread._action()
        if thread._action is not None:
            try:
                new_events = next(thread._action)
            except StopIteration:
                thread._action = None
            else:
                new_events = self._prepare_events(new_events)
                thread._events = new_events

        if thread._action is None or new_events is not None:
            for event in old_events:
                self._unwatch_event(event, thread)

        if thread._action is None:
            self._threads.remove(thread)
            return

        if new_events is not None:
            for event in new_events:
                self._watch_event(event, thread)

    def _prepare_events(self, events):
        # TODO do not use internal events in API
        if events is None:
            events = (SettledEvent(),)
        elif not isinstance(events, tuple):
            events = (events,)

        split_events = []

        for event in events:
            split_events.extend(self._prepare_event(event).split_event())

        return split_events

    def _prepare_event(self, event):
        if isinstance(event, SimEvent):
            return event
        elif isinstance(event, int):
            if event < 0:
                # TODO better error
                raise RuntimeError("negative time delay")
            return TimeEvent(self._engine.time + event)
        elif isinstance(event, Signal):
            if isinstance(event.signal_type, Clock):
                return ClockEvent(event)
            else:
                return ChangeEvent(event)
        raise ValueError("unknown event %r" % event)

    def _step_combinational(self):
        while True:
            self._register_new_events()
            self._engine.step_combinational()
            self._trigger_changes()
            if not self._trigger_threads():
                self._trigger_event(SettledEvent())
                if not self._trigger_threads():
                    break

    def _step(self):
        self._activity = False
        self._trigger_event(TimeEvent(self._engine.time))
        self._step_combinational()

        self._shadow = OrderedDict()
        self._trigger_edges()
        self._trigger_threads()
        self._engine.poke_delayed(self._shadow)
        self._shadow = None

        self._activity |= self._engine.step()

        self._step_combinational()
        return self._activity

    def run(self, timeout=None, stop_on_idle=True):
        with self.activate():
            if timeout:
                timeout += self._engine.time
            self._idle = False
            self._stop = False
            while not self._stop:
                if timeout and self._engine.time >= timeout:
                    break
                if stop_on_idle and self._idle:
                    break
                while self._step():
                    pass
                try:
                    next_time = self._future_events_queue.get(block=False)
                except Empty:
                    break
                step = next_time - self._engine.time
                assert step > 0
                self._engine.advance_time(step)

    def stop(self):
        self._stop = True

    def _register_new_events(self):
        for event in self._new_events:
            if isinstance(event, PrimChangeEvent):
                self._old_values[event] = (
                    self._peek_prim(event.prim))
                for storage in event.prim.accessed_storage:
                    self._engine.add_callback(
                        storage, event, self._change_callback)
            elif isinstance(event, PrimEdgeEvent):
                self._old_values[event] = (
                    self._peek_prim(event.prim))
                for storage in event.prim.accessed_storage:
                    self._engine.add_callback(
                        storage, event, self._edge_callback)
            elif isinstance(event, TimeEvent):
                if event.timestamp < self._engine.time:
                    # TODO better exception
                    raise RuntimeError('event is in the past')
                elif event.timestamp > self._engine.time:
                    self._future_events_queue.put(event.timestamp)
        self._new_events.clear()

    def _change_callback(self, event, storage):
        # TODO remove unwatched events
        self._potential_changes[event] = event

    def _edge_callback(self, event, storage):
        # TODO remove unwatched events
        self._potential_edges[event] = event

    def _trigger_changes(self):
        for event in self._potential_changes:
            new_value = self._peek_prim(event.prim)
            old_value = self._old_values[event]
            if not self._value_same_as(new_value, old_value):
                self._old_values[event] = new_value
                self._trigger_event(event)
        self._potential_changes.clear()

    def _trigger_edges(self):
        for event in self._potential_edges:
            new_value = self._peek_prim(event.prim)
            old_value = self._old_values[event]
            if not self._value_same_as(new_value, old_value):
                self._old_values[event] = new_value
                if (
                        old_value.value.same_as(BitVec(1, 0)) and
                        new_value.value.same_as(BitVec(1, 1))):
                    if event.en is None:
                        self._trigger_event(event)
                    else:
                        en_value = self._peek_prim(event.en)
                        if en_value.value.same_as(BitVec(1, 1)):
                            self._trigger_event(event)
        self._potential_edges.clear()

    def _value_same_as(self, a, b):
        if isinstance(a, PrimConst):
            return a.value.same_as(b.value)
        return all(self._value_same_as(x, y) for x, y in zip(a.table, b.table))

    def _trigger_event(self, event):
        for thread in self._watched_events.get(event, ()):
            self._pending_threads[thread] = thread

    def _trigger_threads(self):
        if not self._pending_threads:
            return False
        for thread in self._pending_threads:
            self._trigger_thread(thread)
        self._pending_threads.clear()
        return True

    def busy(self):
        return BusyToken(self)

    def _acquire_busy(self):
        self._busy_count += 1
        self._idle = False

    def _release_busy(self):
        self._busy_count -= 1
        self._idle = not self._busy_count

    def _discover_sim_inits(self, module):
        # TODO should this be pre-order instead?
        # TODO should this be specified?
        for submodule in module._module_data.submodules:
            self._discover_sim_inits(submodule)

        try:
            setup_fn = module.sim_init
        except AttributeError:
            pass
        else:
            self.thread(setup_fn)


class SimThread:
    def __init__(self, action, events):
        self._action, self._events = action, events


class BusyToken:
    def __init__(self, sim):
        self._sim = sim
        sim._acquire_busy()

    def done(self):
        if self._sim is None:
            raise RuntimeError('busy token already released')
        self._sim._release_busy()
        self._sim = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.done()
