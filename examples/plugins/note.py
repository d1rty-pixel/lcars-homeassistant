"""An example plugin: a component type of its own (docs/EXTENDING.md).

In lcars.yaml:
    plugins: [plugins/note.py]
    ...
    content: {type: note, text: "All decks report ready", colour: ice}
"""
from lcars.components.base import REQUIRED, Component, colour, component
from lcars.engine.cards import text_card
from lcars.engine.sizes import font


@component("note")
class Note(Component):
    """A line of text in a colour, as tall as a data row (text: the text or an LCARdS template; entity: the
    entity a template reads)."""
    fields = {"text": REQUIRED, "colour": "peri", "entity": None}

    def render(self, ctx):
        card = text_card(self.text, "center-left", font(22), colour(self.colour, f"{self.where}.colour"),
                         padding={"left": 4})
        if self.entity:
            card["entity"] = self.entity
        return card

    def height(self, ctx):
        from lcars.engine.sizes import DATA_ROW
        return DATA_ROW
