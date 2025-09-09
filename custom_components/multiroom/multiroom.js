const get_entity_area_id = (entity, devices) => {
  if (entity.area_id) {
    return entity.area_id;
  }

  const device = devices.filter((device) => device.id === entity.device_id);
  return device[0].area_id;
};

const get_floor_icon = (floor) => {
  if (floor.icon) return floor.icon;
  if (floor.level) return `mdi:home-floor-${floor.level}`;
};

class StrategyDashboardDemo {
  static async generate(config, hass) {
    // Query all data we need. We will make it available to views by storing it in strategy options.
    const [areas, floors, devices, entities] = await Promise.all([
      hass.callWS({ type: "config/area_registry/list" }),
      hass.callWS({ type: "config/floor_registry/list" }),
      hass.callWS({ type: "config/device_registry/list" }),
      hass.callWS({ type: "config/entity_registry/list" }),
    ]);
    var { sources } = config;
    if (!sources) sources = [];

    const multiroom_entities = entities.filter((entity) => {
      return entity.platform === "multiroom";
    });
    const multiroom_area_ids = multiroom_entities.map((entity) =>
      get_entity_area_id(entity, devices),
    );
    const multiroom_areas = areas.filter((area) =>
      multiroom_area_ids.includes(area.area_id),
    );

    const area_views = multiroom_areas.map((area) => ({
      strategy: {
        type: "custom:av-area",
        area,
        devices,
        entities,
      },
      title: area.name,
      path: area.area_id,
      subview: true,
    }));
    const source_entities = entities.filter((entity) =>
      sources.includes(entity.entity_id),
    );
    const source_views = source_entities.map((source) => ({
      strategy: {
        type: "custom:av-source",
        source,
        devices,
        entities,
      },
      title: source.name,
      path: source.entity_id,
      subview: true,
    }));
    // Each view is based on a strategy so we delay rendering until it's opened
    var views = [
      {
        strategy: {
          type: "custom:av-overview",
          multiroom_areas,
          floors,
          devices,
          entities,
          sources,
        },
        title: "Overview",
      },
    ];
    views.push(...area_views);
    views.push(...source_views);
    return {
      views,
    };
  }
}

const get_area_players = (area, devices, entities) => {
  const multiroom_players = entities.filter(
    (entity) => entity.platform === "multiroom",
  );
  const area_device_ids = devices
    .filter((device) => device.area_id === area.area_id)
    .map((device) => device.id);
  const area_multiroom_players = multiroom_players.filter((entity) => {
    return entity.area_id
      ? entity.area_id === area.area_id
      : area_device_ids.includes(entity.device_id);
  });
  return area_multiroom_players;
};

const get_floor_overview_section = (areas, floor, devices, entities) => {
  var cards = [
    {
      type: "heading",
      heading: floor.name,
      heading_style: "heading",
      icon: get_floor_icon(floor),
    },
  ];
  cards.push(
    ...areas
      .filter((area) => area.floor_id === floor.floor_id)
      .map((area) => {
        return {
          type: "tile",
          entity: get_area_players(area, devices, entities).filter(
            (entity) => !entity.original_name,
          )[0].entity_id,
          features: [
            { type: "media-player-playback" },
            { type: "media-player-volume-slider" },
          ],
          tap_action: {
            action: "navigate",
            navigation_path: `${area.area_id}`,
          },
          hide_state: false,
          state_content: "source",
          show_entity_picture: true,
        };
      }),
  );

  return {
    type: "grid",
    cards,
  };
};

class AVSourceViewStrategy {
  static async generate(config, hass) {
    const { source, devices, entities } = config;
    const multiroom_players = entities.filter(
      (entity) => entity.platform === "multiroom",
    );
    const primaries = multiroom_players.filter(
      (entity) => !entity.original_name,
    );
    const cards = [
      {
        type: "custom:mini-media-player",
        entity: source.entity_id,
        artwork: "full-cover",
        info: "scroll",
        hide: { volume: "true" },
      },
    ];
    cards.push(
      ...primaries.map((entity) => {
        return {
          type: "tile",
          entity: entity.entity_id,
          features: [{ type: "media-player-volume-slider" }],
          features_position: "inline",
          state_content: "source",
          tap_action: {
            action: "perform-action",
            perform_action: "media_player.select_source",
            target: { entity_id: entity.entity_id },
            data: { source: source.name },
          },
          hold_action: {
            action: "navigate",
            navigation_path: get_entity_area_id(entity, devices),
          },
          double_tap_action: {
            action: "perform-action",
            perform_action: "media_player.turn_off",
            target: { entity_id: entity.entity_id },
            data: {},
          },
        };
      }),
    );

    return {
      sections: [
        {
          type: "grid",
          cards,
        },
      ],
    };
  }
}

class AVOverviewViewStrategy {
  static async generate(config, hass) {
    const { multiroom_areas, floors, devices, entities, sources } = config;

    const multiroom_floor_ids = multiroom_areas.map((area) => area.floor_id);
    const multiroom_floors = floors.filter((floor) =>
      multiroom_floor_ids.includes(floor.floor_id),
    );

    const sections = multiroom_floors.map((floor) => {
      return get_floor_overview_section(
        multiroom_areas,
        floor,
        devices,
        entities,
      );
    });

    const cards = [
      {
        type: "heading",
        heading: "Sources",
        heading_style: "heading",
      },
    ];

    cards.push(
      ...sources.map((source) => {
        return {
          type: "tile",
          entity: source,
          grid_options: { columns: 3 },
          vertical: true,
          tap_action: {
            action: "navigate",
            navigation_path: source,
          },
          hold_action: { action: "more-info" },
        };
      }),
    );

    const source_section = {
      type: "grid",
      cards,
    };
    if (sources.length) sections.push(source_section);

    return {
      sections,
    };
  }
}

class AVAreaViewStrategy {
  static async generate(config, hass) {
    const { area, devices, entities } = config;

    const players = get_area_players(area, devices, entities);

    const cards = [
      {
        type: "custom:mini-media-player",
        entity: players[0].entity_id,
        toggle_power: false,
        source: "full",
        artwork: "full-cover",
      },
    ];
    if (players[1]) {
      cards.push({
        type: "custom:mini-media-player",
        entity: players[1].entity_id,
        toggle_power: false,
        source: "full",
      });
    }

    return {
      cards,
    };
  }
}

customElements.define("ll-strategy-view-av-area", AVAreaViewStrategy);
customElements.define("ll-strategy-dashboard-my-demo", StrategyDashboardDemo);
customElements.define("ll-strategy-view-av-overview", AVOverviewViewStrategy);
customElements.define("ll-strategy-view-av-source", AVSourceViewStrategy);
