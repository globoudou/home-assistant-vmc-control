# VMC Control

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Intégration Home Assistant pour la gestion intelligente de la VMC :
- Activation post-lumière toilettes
- Détection humidité SDB
- Mode été : comparaison températures int/ext
- Déclenchement périodique minimum toutes les 4h

# VMC Control 🌀

Custom Home Assistant integration to manage bathroom/toilet VMC logic.

Features
- Trigger after toilet light off (configurable delay)
- Trigger on high humidity
- Summer mode: ON if inside temp > outside temp
- Periodic minimum trigger every X hours
- Configurable via UI (Config Flow)

Installation
1. Copy the folder `custom_components/vmc_control/` into your Home Assistant `custom_components/` directory
2. Restart Home Assistant
3. Add integration: **VMC Control** from the UI and choose your entities/thresholds

GitHub: https://github.com/globoudou/vmc_control

License: MIT
