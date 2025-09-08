"""Config flow for the Savant Home Automation integration."""

import logging
import typing

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigFlowResult
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.helpers import selector
from .const import DOMAIN

logger = logging.getLogger(__name__)


class MultiroomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Example config flow."""

    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1

    entry_data: dict[str, typing.Any] = {}

    async def async_step_user(self, user_input=None):
        """User input step - select whether to configure some players or a room."""
        errors = {}
        if user_input is not None:
            self.entry_data = user_input
            match self.entry_data["type"]:
                case "players":
                    return await self.async_step_players()
                case "room":
                    return await self.async_step_rooms()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("type"): vol.In(["players", "room"])}),
            errors=errors,
        )

    async def async_step_rooms(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.entry_data.update(user_input)
            if self.source == SOURCE_RECONFIGURE:
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    data_updates=self.entry_data,
                )
            return self.async_create_entry(
                title=user_input["area"],
                data=self.entry_data,
            )

        schema = vol.Schema(
            {
                vol.Required("area"): str,
                vol.Required("audio"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[MEDIA_PLAYER_DOMAIN],
                        multiple=True,
                    )
                ),
                vol.Required("video"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[MEDIA_PLAYER_DOMAIN],
                        multiple=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="rooms",
            data_schema=self.add_suggested_values_to_schema(
                schema,
                (
                    self._get_reconfigure_entry().data
                    if self.source == SOURCE_RECONFIGURE
                    else {}
                ),
            ),
            errors=errors,
        )

    async def async_step_players(self, user_input=None) -> ConfigFlowResult:
        """Player selection - takes the entity ids of the input players."""
        errors = {}
        if user_input is not None:
            self.entry_data.update(user_input)
            return await self.async_step_ports()
        schema = vol.Schema(
            {
                vol.Required("players"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[MEDIA_PLAYER_DOMAIN],
                        multiple=True,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="players",
            data_schema=self.add_suggested_values_to_schema(
                schema,
                (
                    self._get_reconfigure_entry().data
                    if self.source == SOURCE_RECONFIGURE
                    else {}
                ),
            ),
            errors=errors,
        )

    async def async_step_ports(self, user_input=None) -> ConfigFlowResult:
        """Port definition step - provide entity ids for sources."""
        if user_input is not None:
            data = {k: v for k, v in user_input.items() if v}
            self.entry_data["sources"] = data
            logger.debug("create entry with data %s", data)
            if self.source == SOURCE_RECONFIGURE:
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(),
                    data_updates=self.entry_data,
                )
            return self.async_create_entry(
                title="",
                data=self.entry_data,
            )
        sources = {
            source
            for player in self.entry_data["players"]
            for source in self.hass.states.get(player).attributes["source_list"]
        }
        schema = vol.Schema(
            {
                vol.Optional(source): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=[MEDIA_PLAYER_DOMAIN],
                        multiple=False,
                    )
                )
                for source in sources
            }
        )
        return self.async_show_form(
            step_id="ports",
            data_schema=self.add_suggested_values_to_schema(
                schema,
                (
                    self._get_reconfigure_entry().data["sources"]
                    if self.source == SOURCE_RECONFIGURE
                    else {}
                ),
            ),
        )

    async def async_step_reconfigure(self, user_input=None):
        config_type = self._get_reconfigure_entry().data.get("type", None)
        data = {"type": config_type} if config_type else None
        print(self._get_reconfigure_entry().data)
        print(data)
        return await self.async_step_user(data)
