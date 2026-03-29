"""Tests for the event system."""
from game.core.events import EventHandler, EventOnDamaged, EventOnDeath, EventOnMoved


class TestEventHandler:
    def test_global_trigger_fires(self):
        handler = EventHandler()
        received = []
        handler.subscribe(EventOnDamaged, lambda e: received.append(e))
        evt = EventOnDamaged(unit="u", damage=10, damage_type="fire", source="s")
        handler.raise_event(evt)
        assert len(received) == 1
        assert received[0].damage == 10

    def test_entity_trigger_fires_for_matching_entity(self):
        handler = EventHandler()
        received = []
        entity = object()
        handler.subscribe(EventOnDamaged, lambda e: received.append(e), entity=entity)
        evt = EventOnDamaged(unit="u", damage=5, damage_type="fire", source="s")
        handler.raise_event(evt, entity=entity)
        assert len(received) == 1

    def test_entity_trigger_ignores_other_entities(self):
        handler = EventHandler()
        received = []
        entity_a = object()
        entity_b = object()
        handler.subscribe(EventOnDamaged, lambda e: received.append(e), entity=entity_a)
        evt = EventOnDamaged(unit="u", damage=5, damage_type="fire", source="s")
        handler.raise_event(evt, entity=entity_b)
        assert len(received) == 0

    def test_entity_trigger_fires_before_global(self):
        handler = EventHandler()
        order = []
        entity = object()
        handler.subscribe(EventOnDamaged, lambda e: order.append("global"))
        handler.subscribe(EventOnDamaged, lambda e: order.append("entity"), entity=entity)
        evt = EventOnDamaged(unit="u", damage=1, damage_type="f", source="s")
        handler.raise_event(evt, entity=entity)
        assert order == ["entity", "global"]

    def test_unsubscribe(self):
        handler = EventHandler()
        received = []
        cb = lambda e: received.append(e)
        handler.subscribe(EventOnDamaged, cb)
        handler.unsubscribe(EventOnDamaged, cb)
        handler.raise_event(EventOnDamaged(unit="u", damage=1, damage_type="f", source="s"))
        assert len(received) == 0

    def test_unsubscribe_entity(self):
        handler = EventHandler()
        received = []
        entity = object()
        cb = lambda e: received.append(e)
        handler.subscribe(EventOnDamaged, cb, entity=entity)
        handler.unsubscribe(EventOnDamaged, cb, entity=entity)
        handler.raise_event(
            EventOnDamaged(unit="u", damage=1, damage_type="f", source="s"),
            entity=entity,
        )
        assert len(received) == 0

    def test_snapshot_safety_subscribe_during_dispatch(self):
        """Subscribing a new handler during dispatch shouldn't affect current iteration."""
        handler = EventHandler()
        received = []

        def first_handler(e):
            received.append("first")
            handler.subscribe(EventOnDamaged, lambda e2: received.append("new"))

        handler.subscribe(EventOnDamaged, first_handler)
        handler.raise_event(EventOnDamaged(unit="u", damage=1, damage_type="f", source="s"))
        # "new" should NOT fire during this dispatch
        assert received == ["first"]

        # But next dispatch should include it
        handler.raise_event(EventOnDamaged(unit="u", damage=1, damage_type="f", source="s"))
        assert "new" in received

    def test_snapshot_safety_unsubscribe_during_dispatch(self):
        """Unsubscribing during dispatch shouldn't skip remaining handlers."""
        handler = EventHandler()
        received = []

        def cb1(e):
            received.append("cb1")
            handler.unsubscribe(EventOnDamaged, cb2)

        def cb2(e):
            received.append("cb2")

        handler.subscribe(EventOnDamaged, cb1)
        handler.subscribe(EventOnDamaged, cb2)
        handler.raise_event(EventOnDamaged(unit="u", damage=1, damage_type="f", source="s"))
        # Both should fire (snapshot taken before iteration)
        assert "cb1" in received
        assert "cb2" in received

    def test_multiple_event_types(self):
        handler = EventHandler()
        damaged = []
        died = []
        handler.subscribe(EventOnDamaged, lambda e: damaged.append(e))
        handler.subscribe(EventOnDeath, lambda e: died.append(e))

        handler.raise_event(EventOnDamaged(unit="u", damage=1, damage_type="f", source="s"))
        assert len(damaged) == 1
        assert len(died) == 0

    def test_clear(self):
        handler = EventHandler()
        received = []
        handler.subscribe(EventOnDamaged, lambda e: received.append(e))
        handler.clear()
        handler.raise_event(EventOnDamaged(unit="u", damage=1, damage_type="f", source="s"))
        assert len(received) == 0

    def test_no_handlers_doesnt_crash(self):
        handler = EventHandler()
        handler.raise_event(EventOnMoved(unit="u", x=0, y=0, teleport=False))
