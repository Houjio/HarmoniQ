import numpy as np
import pandas as pd

from harmoniq.db.schemas import EolienneParc, weather_schema
from harmoniq.modules.eolienne.turbine_data import turbine_models


def adjust_wind_speed(v_meteo, z_meteo, z_eolien, z0=0.03):
    """
    Adjust the wind speed measured at z_ref (m) to the hub height z_hub (m)
    using the logarithmic wind profile law.
    """
    # TODO: @Zineb: PQ on utilise z0 = 0.03 ?
    return v_meteo * (np.log(z_eolien / z0) / np.log(z_meteo / z0))


def air_density(temperature, pressure):
    """
    Calculate the air density (kg/m³) using the ideal gas law.
    temperature in K, pressure in Pa.
    """
    R = 287.05  # J/(kg·K)
    return pressure / (R * temperature)


def piecewise_power_curve(
    v, cut_in_speed, rated_speed, cut_out_speed, rated_power, power_shape_exponent=3.0
):
    """
    Piecewise model of a generic power curve:
      - P=0 if v < cut_in or v > cut_out
      - P rises from 0 to P_nominal between cut_in and rated (law ~ (v - cut_in)^exponent)
      - P = P_nominal between rated and cut_out
    v : wind speed (array or float)
    cut_in_speed, rated_speed, cut_out_speed : key speeds (m/s)
    rated_power : nominal power (W)
    power_shape_exponent : exponent for the rise (3.0 by default)
    Returns an array/float P(v) (W).
    """
    power = np.zeros_like(v, dtype=float)

    # Masks
    mask_cut_in = (v >= cut_in_speed) & (v < rated_speed)
    mask_rated = (v >= rated_speed) & (v <= cut_out_speed)
    # Values outside [cut_in, cut_out] remain at 0

    # Zone 2: power rise
    v_in_zone = v[mask_cut_in]
    power[mask_cut_in] = (
        rated_power
        * ((v_in_zone - cut_in_speed) / (rated_speed - cut_in_speed))
        ** power_shape_exponent
    )

    # Zone 3: nominal power
    power[mask_rated] = rated_power
    
    return power


def apply_directional_losses(direction_series):
    """
    Calculate a directional loss factor vectorized.
    Hypothesis: optimal direction = 180°, max 30% losses if deviation = 180°.
    Bounded at 0.7 minimum (70%).
    """
    # TODO: @Zineb: PQ on utilise optimal_direction = 180, on ne connais pas la direction des éoliennes ?
    optimal_direction = 180
    max_loss = 0.3
    deviation = np.abs(direction_series - optimal_direction)
    deviation = np.where(deviation > 180, 360 - deviation, deviation)
    loss = 1 - (max_loss * (deviation / 180.0))
    loss = np.maximum(loss, 0.7)
    return loss


def apply_wake_losses(direction_series):
    """
    Simplified wake loss factor: 10% losses if |dir - 180| < 30°, otherwise 0%.
    """
    condition = np.abs(direction_series - 180) < 30
    return np.where(condition, 0.9, 1.0)


def ice_loss_factor(t: np.ndarray) -> np.ndarray:
    """
    Ice loss factor if T < 273 K,
    generate a random value [0.5, 1.0], otherwise 1.0.
    """
    # TODO @Zineb: PQ on génère un random ici ?
    t = t + 273.15  # Convert to Kelvin
    return np.where(t < 273, 1.0, np.random.uniform(0.5, 1.0, size=t.shape))


def get_parc_power(parc: EolienneParc, meteo: pd.DataFrame) -> pd.DataFrame:
    # Get the turbine data
    turbine_data = turbine_models.get(parc.modele_turbine, None)
    if turbine_data is None:
        raise ValueError(f"Unknown turbine model: {parc.modele_turbine}")

    # Set tempature to Kelvin
    meteo["temperature"] = meteo["temperature_C"] + 273.15

    # Adjust wind speed to hub height
    # TODO: @Zineb: PQ on utilise 10m comme référence ?
    # TODO: @Zineb: Est-ce que c'est suppose être en m/s ?
    vitesse_vents = adjust_wind_speed(
        meteo["vitesse_vent_kmh"].values, 10, parc.hauteur_moyenne
    )

    # Apply directional losses
    directional_losses = apply_directional_losses(meteo["direction_vent"])
    power_output_direction = piecewise_power_curve(
        vitesse_vents,
        turbine_data["cut_in_wind_speed"],
        (turbine_data["cut_in_wind_speed"] + turbine_data["cut_out_wind_speed"])
        / 2,  # rated speed (TODO find real rated speed)
        turbine_data["cut_out_wind_speed"],
        parc.puissance_nominal,
    )

    # power_with_output_direction = power_output_direction * directional_losses # On ne considère pas la direction pour le moment

    # Apply wake losses
    wake_losses = apply_wake_losses(meteo["direction_vent"])
    power_with_wake_losses = power_output_direction * wake_losses

    # Apply ice losses
    ice_losses = ice_loss_factor(meteo["temperature"])
    power_with_ice_losses = power_with_wake_losses * ice_losses


    # Apply for all turbines in the parc
    power_parc = power_with_ice_losses * parc.nombre_eoliennes
    
    # Calculate the energy produced
    df = pd.DataFrame(
        {
            "tempsdate": meteo.index.values,
            "vitesse_vent_kmh": meteo["vitesse_vent_kmh"].values,
            "direction_vent": meteo["direction_vent"].values,
            "puissance": power_parc,
        }
    )

    return df
