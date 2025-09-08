import logging

import networkx as nx

from homeassistant.helpers.event import async_track_state_change_event

logger = logging.getLogger(__name__)

class MultiroomGraph:
    sinks = []
    def __init__(self, hass):
        self.hass = hass
        self.graph = nx.DiGraph()

    async def async_setup_entry(self, entry):
        for player in entry.data["players"]:
            for source, source_player in entry.data["sources"].items():
                self.graph.add_edge(source_player, player, source=source)

        nx.write_network_text(self.graph)
        for sink in self.sinks:
            sink.async_on_remove(
                async_track_state_change_event(
                    self.hass, self.sources(), sink.on_update
                )
            )
            sink.async_schedule_update_ha_state()


    def add_sinks(self, sinks):
        for sink in sinks:
            self.sinks.append(sink)
            sink.async_on_remove(
                async_track_state_change_event(
                    self.hass, self.sources(), sink.async_schedule_update_ha_state
                )
            )
    
    def sources(self, sink=None):
        if sink is None:
            return [node for node in self.graph.nodes() if not self.graph.in_degree(node)]
        if sink not in self.graph:
            return []
        ancestors = nx.ancestors(self.graph, sink)
        
        return [node for node in ancestors if not self.graph.in_degree(node)]

    def source_selections(self, source, sink):
        paths = list(nx.all_simple_paths(self.graph, source, sink))
        logger.debug(paths)
        assert(len(paths)) == 1
        path = paths[0]
        selections = {}
        for i in range(0, len(path) - 1):
            edge = self.graph.edges[path[i], path[i+1]]
            selections[path[i+1]] = edge
        return selections

    def source_uses(self, source):
        rtn = []
        for player in self.sinks:
            if source == player.source:
                rtn.append(player.entity_id)
        return rtn

    def source(self, player):
        while True:
            in_edges = self.graph.in_edges(player, data=True)
            if not in_edges:
                break
            player_state = self.hass.states.get(player)
            if not player_state:
                return
            selected_source = player_state.attributes.get("source")
            players = [edge[0] for edge in in_edges if edge[2]["source"] == selected_source]
            if not players:
                return
            assert len(players) == 1
            player = players[0]
        return player