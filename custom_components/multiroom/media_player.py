"""Media players for Multiroom AV."""

import logging
from statistics import mean

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.event import async_track_state_change_event
from .const import DOMAIN

logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up entry media players."""
    match config.data["type"]:
        case "room":
            players = []
            players.append(RoomPlayer(config))
            if config.data.get("video"):
                players.append(RoomPlayer(config, True))
            async_add_entities(players)
            hass.data[DOMAIN].add_sinks(players)
            print(players)


class RoomPlayer(MediaPlayerEntity):
    """Integrated media player combining local and remote sources."""

    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
    )
    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    source_map = {}
    desired_source = None

    def __init__(self, config, audio_only=False):
        self.audio_players = config.data["audio"]
        self.video_players = [] if audio_only else config.data.get("video", [])
        self._attr_unique_id = (
            "virtual_" + ("audio_" if audio_only else "") + config.data["area"]
        )
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, config.data["area"])},
            name=config.data["area"],
            model="Virtual media player",
        )
        if audio_only:
            self._attr_name = "Audio"
        if not self.video_players:
            self._attr_device_class = MediaPlayerDeviceClass.SPEAKER
        if len(self.audio_players) > 1:
            self._attr_supported_features |= MediaPlayerEntityFeature.SELECT_SOUND_MODE
        self.selected_audio_player = self.audio_players[0]

    async def async_added_to_hass(self):
        config_entries = self.hass.config_entries.async_entries(DOMAIN)
        for entry in config_entries:
            if entry.data["type"] == "players" and set(self.players) & set(
                entry.data["players"]
            ):
                self.source_map.update(entry.data["sources"])

        self.async_on_remove(
            async_track_state_change_event(self.hass, self.players, self.on_update)
        )

    @property
    def players(self):
        return self.audio_players + self.video_players

    @property
    def used_players(self):
        return self.video_players + [self.selected_audio_player]

    @property
    def state(self):
        if self.source_entity:
            state = self.hass.states.get(self.source_entity)
            if state:
                if not state.state == MediaPlayerState.OFF:
                    return state.state

        if self.video_players:
            player = self.hass.states.get(self.video_players[0])
            if player and player.state in [MediaPlayerState.IDLE, MediaPlayerState.ON]:
                return MediaPlayerState.IDLE
        elif self.selected_audio_player:
            player = self.hass.states.get(self.selected_audio_player)
            if player and player.state in [MediaPlayerState.IDLE, MediaPlayerState.ON]:
                return MediaPlayerState.IDLE

        return MediaPlayerState.OFF

    @property
    def entity_picture_local(self):
        if state := self.source_state:
            return state.attributes.get("entity_picture_local")

    @property
    def entity_picture(self):
        if state := self.source_state:
            return state.attributes.get("entity_picture")

    @property
    def media_content_type(self):
        if state := self.source_state:
            return state.attributes.get("media_content_type")

    @property
    def media_title(self):
        if state := self.source_state:
            return state.attributes.get("media_title")

    @property
    def media_series_title(self):
        if state := self.source_state:
            return state.attributes.get("media_series_title")

    @property
    def media_channel(self):
        if state := self.source_state:
            return state.attributes.get("media_channel")

    @property
    def icon(self):
        if state := self.source_state:
            return state.attributes.get("icon")
        return super().icon

    @property
    def source(self):
        if self.desired_source:
            print(f"des is {self.desired_source}")
            return self.desired_source
        if self.source_entity:
            return self.hass.states.get(self.source_entity).attributes.get(
                "friendly_name", "unknown"
            )

    @property
    def source_entity(self):
        if self.desired_source:
            return self.source_map[self.desired_source]
        for player in self.used_players:
            if source := self.hass.data[DOMAIN].source(player):
                return source

    @property
    def source_state(self):
        if self.source_entity:
            state = self.hass.states.get(self.source_entity)
            return state

    @property
    def source_list(self):
        source_ids = {
            source
            for player in self.used_players
            for source in self.hass.data[DOMAIN].sources(player)
        }
        states = [self.hass.states.get(source) for source in source_ids]
        states = [state for state in states if state]
        self.source_map = {
            state.attributes.get("friendly_name"): state.entity_id for state in states
        }
        rtn = list(self.source_map.keys())
        return rtn

    @property
    def sound_mode_list(self):
        states = [self.hass.states.get(source) for source in source_ids]
        states = [state for state in states if state]
        return [state.attributes.get("friendly_name") for state in states]

    @property
    def volume_level(self):
        players = [self.hass.states.get(player) for player in self.audio_players]
        players = [player for player in players if player]
        volumes = [player.attributes.get("volume_level", None) for player in players]
        volumes = [v for v in volumes if v is not None]
        if volumes:
            return mean(volumes)

    @property
    def is_volume_muted(self):
        players = [self.hass.states.get(player) for player in self.audio_players]
        players = [player for player in players if player]
        muted = [player.attributes.get("is_volume_muted", None) for player in players]
        muted = [v for v in muted if v is not None]
        return all(muted)

    @property
    def extra_state_attributes(self):
        return {"source_entity": self.source_entity}

    async def async_set_volume_level(self, volume):
        for player in self.audio_players:
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                "volume_set",
                {"volume_level": volume, "entity_id": player},
                blocking=False,
            )

    async def async_mute_volume(self, mute):
        for player in self.audio_players:
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                "volume_mute",
                {"is_volume_muted": mute, "entity_id": player},
                blocking=False,
            )

    async def async_select_source(self, source):
        self.desired_source = source
        old_source = self.source
        await self.hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            "turn_on",
            {"entity_id": self.source_map[source]},
            blocking=True,
        )
        for player in self.used_players:
            source_selections = self.hass.data[DOMAIN].source_selections(
                self.source_map[source], player
            )
            for selector, selection in source_selections.items():
                await self.hass.services.async_call(
                    MEDIA_PLAYER_DOMAIN,
                    "turn_on",
                    {"entity_id": selector},
                    blocking=True,
                )
                await self.hass.services.async_call(
                    MEDIA_PLAYER_DOMAIN,
                    "select_source",
                    {"source": selection["source"], "entity_id": selector},
                    blocking=True,
                )
        self.async_schedule_update_ha_state()
        self.desired_source = None
        self.async_schedule_update_ha_state()

    async def async_media_play(self):
        await self.hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            "media_play",
            {"entity_id": self.source_entity},
            blocking=True,
        )

    async def async_media_pause(self):
        await self.hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            "media_pause",
            {"entity_id": self.source_entity},
            blocking=True,
        )

    async def async_turn_off(self):
        for player in self.players:
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                "turn_off",
                {"entity_id": player},
                blocking=True,
            )

    async def async_turn_on(self):
        for player in self.players:
            logger.debug("turning on %s for %s", player, self.device_info["name"])
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                "turn_on",
                {"entity_id": player},
                blocking=True,
            )

    async def on_update(self, update):
        self.async_schedule_update_ha_state(update)
