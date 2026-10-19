"""Assistant de configuration : choix des entités sources."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_HUMIDITY,
    CONF_LIGHT,
    CONF_TEMP_IN,
    CONF_TEMP_OUT,
    CONF_VMC,
    DOMAIN,
    LIGHT_DOMAINS,
    VMC_DOMAINS,
)


def _sources_schema() -> dict:
    sensor = lambda dc: selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", device_class=dc)
    )
    return {
        vol.Required(CONF_VMC): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=VMC_DOMAINS)
        ),
        vol.Optional(CONF_LIGHT): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=LIGHT_DOMAINS)
        ),
        vol.Optional(CONF_HUMIDITY): sensor("humidity"),
        vol.Optional(CONF_TEMP_IN): sensor("temperature"),
        vol.Optional(CONF_TEMP_OUT): sensor("temperature"),
    }


class VmcConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_VMC])
            self._abort_if_unique_id_configured()
            title = user_input.pop(CONF_NAME, None) or "VMC"
            return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {vol.Optional(CONF_NAME, default="VMC"): str, **_sources_schema()}
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(entry) -> OptionsFlow:
        return VmcOptionsFlow()


class VmcOptionsFlow(OptionsFlow):
    """Permet de changer les entités sources sans supprimer l'intégration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            # Les options remplacent intégralement les données d'origine,
            # ce qui permet aussi de retirer une entité facultative.
            return self.async_create_entry(data=user_input)

        current = dict(self.config_entry.options or self.config_entry.data)
        schema = self.add_suggested_values_to_schema(
            vol.Schema(_sources_schema()), current
        )
        return self.async_show_form(step_id="init", data_schema=schema)
