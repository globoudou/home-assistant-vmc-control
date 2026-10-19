# VMC Control 🌀

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Intégration Home Assistant pour piloter une VMC **en marche/arrêt** (relais, prise, `fan`, `input_boolean`…) à partir de plusieurs déclencheurs, avec une carte Lovelace de contrôle et de paramétrage.

## Déclencheurs

| Déclencheur | Fonctionnement | Réglages |
|---|---|---|
| **Toilettes** | Démarre quand la lumière est allumée depuis plus que le délai, puis continue N minutes après extinction. Un passage plus court que le délai est ignoré. | délai avant démarrage (s), marche après extinction (min) |
| **Humidité SDB** | Démarre au-dessus du seuil, s'arrête sous *seuil − hystérésis*. | seuil (%), hystérésis (%) |
| **Renouvellement périodique** | Garantit au moins *durée* de fonctionnement toutes les *intervalle* heures. Tout fonctionnement assez long (humidité, toilettes…) remet le compteur à zéro. | intervalle (h), durée (min) |
| **Différentiel de température** | *Rafraîchir* : marche si T° int > consigne et T° ext plus fraîche d'au moins l'écart. *Réchauffer* : l'inverse. Hystérésis de 0,5 °C. | mode, consigne (°C), écart (°C) |
| **Boost** | Marche temporaire à la demande. | durée (min) |

Le **mode** général : `Auto` (déclencheurs), `Marche forcée`, `Arrêt forcé`.

## Entités créées (appareil « VMC »)

- `select` : Mode, Mode thermique
- `switch` : activation de chaque déclencheur (toilettes, humidité, périodique)
- `number` : tous les seuils et durées (persistés, survivent aux redémarrages)
- `button` : Boost, Arrêter le boost
- `sensor` : État (raison de fonctionnement + détails en attributs), Prochain renouvellement
- `binary_sensor` : Ventilation demandée

Tout se règle depuis l'interface ; aucune automatisation ni `input_*` à créer.

## Installation

1. HACS → Intégrations → ⋮ → Dépôts personnalisés → `https://github.com/globoudou/home-assistant-vmc-control` (catégorie *Intégration*), puis installer.
   *Ou* copier `custom_components/vmc_control/` dans `config/custom_components/`.
2. Redémarrer Home Assistant.
3. Paramètres → Appareils et services → Ajouter → **VMC Control**. Seule l'entité de la VMC est obligatoire ; les capteurs peuvent être ajoutés plus tard (⚙ *Configurer*).
   Cochez **Logique inversée** si la VMC tourne quand l'entité est à `off` (relais normalement fermé).

## Carte

La carte est servie automatiquement par l'intégration (pas de ressource à déclarer, rechargez le navigateur après installation). Elle apparaît dans le sélecteur de cartes sous « VMC Control », ou en YAML :

```yaml
type: custom:vmc-control-card
entity: sensor.vmc_etat   # capteur « État » de l'intégration
title: VMC                # facultatif
```

Elle affiche l'état de la VMC et la raison, le mode (Auto / Marche / Arrêt), le boost, chaque déclencheur avec sa valeur en direct et son interrupteur, et un panneau *Paramètres* repliable.

## Migration depuis la v1

Les entrées v1 sont migrées automatiquement (entités sources conservées). L'ancien `input_boolean` « mode été » est remplacé par l'entité *Mode thermique*, et les seuils se règlent désormais via les entités `number`.

## Développement

```bash
pip install pytest-homeassistant-custom-component home-assistant-frontend
pytest
```

Licence : MIT
