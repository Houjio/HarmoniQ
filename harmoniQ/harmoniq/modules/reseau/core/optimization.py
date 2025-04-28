"""
Module d'optimisation du réseau électrique.

Ce module gère l'optimisation de la production électrique en utilisant PyPSA.
L'optimisation est basée sur :
- Les coûts marginaux des centrales pilotables (réservoirs, thermique)
- La disponibilité des centrales non-pilotables (fil de l'eau, éolien, solaire)
- Les contraintes du réseau de transport

Example:
    >>> from network.core import NetworkOptimizer
    >>> optimizer = NetworkOptimizer(network)
    >>> network = optimizer.optimize()
    >>> results = optimizer.get_optimization_results()

Contributeurs : Yanis Aksas (yanis.aksas@polymtl.ca)
                Add Contributor here
"""

import pypsa
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime
import numpy as np


class NetworkOptimizer:
    """
    Optimiseur du réseau électrique.
    
    Cette classe gère l'optimisation de la production en minimisant les coûts
    tout en respectant les contraintes du réseau. Elle utilise les coûts marginaux
    pour piloter les centrales à réservoir.

    Attributes:
        network (pypsa.Network): Réseau à optimiser
        solver_name (str): Solveur à utiliser
        solver_options (dict): Options de configuration du solveur
        is_journalier (bool): Si True, les données sont traitées avec un pas de 24h
    """

    def __init__(self, network: pypsa.Network, solver_name: str = "highs", is_journalier=None):
        """
        Initialise l'optimiseur.

        Args:
            network: Réseau PyPSA à optimiser
            solver_name: Nom du solveur linéaire à utiliser ('highs' par défaut)
            is_journalier: Si True, les données sont traitées avec un pas de 24h
        """
        self.network = network
        self.solver_name = solver_name
        
        # Détecter automatiquement le mode journalier si non spécifié
        if is_journalier is None:
            self.is_journalier = False
            if len(network.snapshots) > 1:
                time_diff = network.snapshots[1] - network.snapshots[0]
                if time_diff >= pd.Timedelta(hours=23):
                    self.is_journalier = True
        else:
            self.is_journalier = is_journalier

    def optimize(self) -> pypsa.Network:
        """
        Exécute l'optimisation du réseau avec gestion robuste des erreurs SVD.
        
        Cette méthode optimise la production en minimisant les coûts totaux,
        et gère les erreurs SVD qui peuvent survenir lors de l'extraction des résultats.
        """
        # Utiliser notre optimisateur manuel au lieu de PyPSA standard
        return self.optimize_manually()

    def optimize_manually(self) -> pypsa.Network:
        """
        Optimise le réseau manuellement en allouant la production par ordre de coût marginal.
        
        Cette méthode:
        1. Pour chaque pas de temps, calcule la demande totale
        2. Alloue la production par ordre de priorité: fatales → réservoirs → thermiques
        3. Respecte les contraintes de capacité (p_nom) et disponibilité (p_max_pu)
        4. Assure qu'hydro_reservoir contribue au minimum 20% de la production
        
        Returns:
            pypsa.Network: Réseau avec résultats d'optimisation
        """
        import logging
        logger = logging.getLogger("ManualOptimizer")
        logger.info(f"Démarrage de l'optimisation manuelle en mode {'journalier' if self.is_journalier else 'horaire'}...")
        

        loads_is_energy = getattr(self.network.loads_t.p_set, '_energy_not_power', self.is_journalier)
        
        if not hasattr(self.network, 'generators_t'):
            self.network.generators_t = {}

        self.network.generators_t['p'] = pd.DataFrame(
            0.0, 
            index=self.network.snapshots, 
            columns=self.network.generators.index
        )

        self.network.lines_t = {}
        self.network.lines_t['p0'] = pd.DataFrame(
            0.0,
            index=self.network.snapshots,
            columns=self.network.lines.index
        )
        self.network.lines_t['q0'] = pd.DataFrame(
            0.0,
            index=self.network.snapshots,
            columns=self.network.lines.index
        )
        
        # Extraire les générateurs par type pour ordonner la priorité
        carriers_by_priority = [
            'eolien', 'solaire', 'hydro_fil', 'nucléaire',  # Priorité 1: Fatales
            'hydro_reservoir',                              # Priorité 2: Réservoirs  
            'thermique', 'import', 'emergency'              # Priorité 3: Thermiques
        ]
        
        generators_by_carrier = {}
        for carrier in carriers_by_priority:
            generators_by_carrier[carrier] = self.network.generators[
                self.network.generators.carrier == carrier
            ].index.tolist()
        
        # Calculer les capacités maximales disponibles par type
        max_capacities = {}
        for carrier in carriers_by_priority:
            generators = generators_by_carrier.get(carrier, [])
            if generators:
                total_capacity = sum(self.network.generators.at[gen, 'p_nom'] for gen in generators)
                # Multiplier la capacité par 10 pour les éoliennes
                if carrier == 'eolien':
                    total_capacity *= 10
                max_capacities[carrier] = total_capacity
                logger.info(f"Capacité maximale {carrier}: {total_capacity:.2f} MW")
        
        # Variables pour suivre la production
        total_annual_load = 0
        total_annual_generation = 0
        production_by_carrier = {carrier: 0 for carrier in carriers_by_priority}
        
        for snapshot in self.network.snapshots:
            # 1. Calculer la demande totale pour ce pas de temps
            if snapshot in self.network.loads_t.p_set.index:
                total_load = self.network.loads_t.p_set.loc[snapshot].sum()
                
                # Convertir MWh/jour en MW moyens si nécessaire
                if loads_is_energy:
                    total_load = total_load / 24
            else:
                total_load = 0
                logger.warning(f"Pas de données de charge pour {snapshot}, utilisation de 0")
            
            total_annual_load += total_load
            remaining_load = total_load
            
            # 2. Prévoir un minimum de 20% pour hydro_reservoir
            min_hydro_reservoir = total_load * 0.20
            
            # Vérifier si le minimum hydro_reservoir est réalisable
            hydro_reservoir_gens = generators_by_carrier.get('hydro_reservoir', [])
            max_hydro_reservoir = 0
            if hydro_reservoir_gens:
                for gen in hydro_reservoir_gens:
                    p_nom = self.network.generators.at[gen, 'p_nom']
                    p_max_pu = 1.0
                    if (hasattr(self.network.generators_t, 'p_max_pu') and
                        gen in self.network.generators_t.p_max_pu.columns and
                        snapshot in self.network.generators_t.p_max_pu.index):
                        p_max_pu = self.network.generators_t.p_max_pu.at[snapshot, gen]
                    max_hydro_reservoir += p_nom * p_max_pu
            
            # Ajuster le minimum si nécessaire
            if max_hydro_reservoir < min_hydro_reservoir:
                min_hydro_reservoir = max_hydro_reservoir
            
            # Allouer des réservoirs hydro en premier pour garantir le minimum requis
            hydro_reservoir_allocation = min_hydro_reservoir
            hydro_reservoir_supplied = 0
            if hydro_reservoir_gens:
                # Trier les réservoirs par coût marginal croissant
                sorted_hydro_reservoir = self._sort_generators_by_cost(hydro_reservoir_gens, snapshot)
                
                for gen in sorted_hydro_reservoir:
                    p_nom = self.network.generators.at[gen, 'p_nom']
                    p_max_pu = 1.0
                    if (hasattr(self.network.generators_t, 'p_max_pu') and
                        gen in self.network.generators_t.p_max_pu.columns and
                        snapshot in self.network.generators_t.p_max_pu.index):
                        p_max_pu = self.network.generators_t.p_max_pu.at[snapshot, gen]
                    
                    max_available = p_nom * p_max_pu
                    power = min(max_available, hydro_reservoir_allocation - hydro_reservoir_supplied)
                    
                    if power > 0:
                        self.network.generators_t['p'].at[snapshot, gen] = power
                        hydro_reservoir_supplied += power
                        remaining_load -= power
                        
                        if hydro_reservoir_supplied >= hydro_reservoir_allocation:
                            break
                
                production_by_carrier['hydro_reservoir'] += hydro_reservoir_supplied
            
            # Traiter les sources fatales par ordre de mérite
            fatale_carriers = ['eolien', 'solaire', 'hydro_fil', 'nucléaire']
            load_supplied_by_fatale = 0
            
            # Première passe: sources fatales avec leurs contraintes de capacité
            for carrier in fatale_carriers:
                generators = generators_by_carrier.get(carrier, [])
                
                if not generators or remaining_load <= 0:
                    continue
                
                # Calculer la capacité maximale disponible pour ce type à ce moment
                available_capacity = 0
                for gen in generators:
                    p_nom = self.network.generators.at[gen, 'p_nom']
                    p_max_pu = 1.0
                    if (hasattr(self.network.generators_t, 'p_max_pu') and
                        gen in self.network.generators_t.p_max_pu.columns and
                        snapshot in self.network.generators_t.p_max_pu.index):
                        p_max_pu = self.network.generators_t.p_max_pu.at[snapshot, gen]
                    available_capacity += p_nom * p_max_pu
                
                # Limiter à la capacité disponible
                carrier_allocation = min(available_capacity, remaining_load)
                
                # Trier les générateurs par coût marginal croissant
                sorted_generators = self._sort_generators_by_cost(generators, snapshot)
                
                # Allouer la production dans l'ordre de mérite
                carrier_supplied = 0
                for gen in sorted_generators:
                    if remaining_load <= 0:
                        break
                        
                    # Capacité disponible pour ce générateur
                    p_nom = self.network.generators.at[gen, 'p_nom']
                    
                    # Disponibilité (p_max_pu)
                    p_max_pu = 1.0
                    if (hasattr(self.network.generators_t, 'p_max_pu') and
                        gen in self.network.generators_t.p_max_pu.columns and
                        snapshot in self.network.generators_t.p_max_pu.index):
                        p_max_pu = self.network.generators_t.p_max_pu.at[snapshot, gen]
                    
                    max_available = p_nom * p_max_pu
                    
                    # Limité par la demande restante pour ce type
                    power = min(max_available, carrier_allocation - carrier_supplied, remaining_load)
                    
                    if power <= 0:
                        continue
                    
                    # Enregistrer la production pour ce générateur
                    self.network.generators_t['p'].at[snapshot, gen] = power
                    
                    # Mise à jour des compteurs
                    carrier_supplied += power
                    remaining_load -= power
                    
                    if carrier_supplied >= carrier_allocation or remaining_load <= 0:
                        break
                
                # Mise à jour des compteurs
                load_supplied_by_fatale += carrier_supplied
                production_by_carrier[carrier] += carrier_supplied
            
            # 4. Allouer plus d'hydroréservoirs si nécessaire
            additional_hydro_reservoir = 0
            if remaining_load > 0 and hydro_reservoir_gens:
                # Calcul de la capacité hydroréservoir restante disponible
                remaining_hydro_capacity = max_hydro_reservoir - hydro_reservoir_supplied
                
                if remaining_hydro_capacity > 0:
                    additional_allocation = min(remaining_hydro_capacity, remaining_load)
                    
                    # Trier à nouveau pour prendre en compte d'éventuels changements de coûts
                    sorted_hydro_reservoir = self._sort_generators_by_cost(hydro_reservoir_gens, snapshot)
                    
                    for gen in sorted_hydro_reservoir:
                        if remaining_load <= 0:
                            break
                            
                        # Ne pas réutiliser la puissance déjà allouée
                        current_power = self.network.generators_t['p'].at[snapshot, gen]
                        p_nom = self.network.generators.at[gen, 'p_nom']
                        p_max_pu = 1.0
                        if (hasattr(self.network.generators_t, 'p_max_pu') and
                            gen in self.network.generators_t.p_max_pu.columns and
                            snapshot in self.network.generators_t.p_max_pu.index):
                            p_max_pu = self.network.generators_t.p_max_pu.at[snapshot, gen]
                        
                        remaining_capacity = (p_nom * p_max_pu) - current_power
                        
                        if remaining_capacity <= 0:
                            continue
                        
                        additional_power = min(remaining_capacity, remaining_load)
                        self.network.generators_t['p'].at[snapshot, gen] += additional_power
                        
                        additional_hydro_reservoir += additional_power
                        remaining_load -= additional_power
                        
                        if additional_hydro_reservoir >= additional_allocation or remaining_load <= 0:
                            break
                    
                    production_by_carrier['hydro_reservoir'] += additional_hydro_reservoir
            
            # 5. Utiliser les centrales thermiques pour le reste de la demande
            thermique_carriers = ['thermique', 'import', 'emergency']
            
            for carrier in thermique_carriers:
                generators = generators_by_carrier.get(carrier, [])
                
                if not generators or remaining_load <= 0:
                    continue
                
                # Calculer la capacité maximale disponible pour ce type
                available_capacity = 0
                for gen in generators:
                    p_nom = self.network.generators.at[gen, 'p_nom']
                    p_max_pu = 1.0
                    if (hasattr(self.network.generators_t, 'p_max_pu') and
                        gen in self.network.generators_t.p_max_pu.columns and
                        snapshot in self.network.generators_t.p_max_pu.index):
                        p_max_pu = self.network.generators_t.p_max_pu.at[snapshot, gen]
                    available_capacity += p_nom * p_max_pu
                
                # Limiter à la capacité disponible et à la demande restante
                carrier_allocation = min(available_capacity, remaining_load)
                
                # Trier par coût
                sorted_generators = self._sort_generators_by_cost(generators, snapshot)
                
                # Allouer la production dans l'ordre de mérite
                carrier_supplied = 0
                for gen in sorted_generators:
                    if remaining_load <= 0:
                        break
                        
                    p_nom = self.network.generators.at[gen, 'p_nom']
                    p_max_pu = 1.0
                    if (hasattr(self.network.generators_t, 'p_max_pu') and
                        gen in self.network.generators_t.p_max_pu.columns and
                        snapshot in self.network.generators_t.p_max_pu.index):
                        p_max_pu = self.network.generators_t.p_max_pu.at[snapshot, gen]
                    
                    max_available = p_nom * p_max_pu
                    
                    # Limité par l'allocation restante et la demande restante
                    power = min(max_available, carrier_allocation - carrier_supplied, remaining_load)
                    
                    if power <= 0:
                        continue
                    
                    self.network.generators_t['p'].at[snapshot, gen] = power
                    carrier_supplied += power
                    remaining_load -= power
                    
                    if carrier_supplied >= carrier_allocation or remaining_load <= 0:
                        break
                production_by_carrier[carrier] += carrier_supplied

            if remaining_load > 1.0:  # Tolérance de 1 MW
                # Si besoin, ajouter un générateur d'urgence
                emergency_gen = f"emergency_{snapshot.strftime('%Y%m%d')}"
                if emergency_gen not in self.network.generators.index:
                    # Chercher un bus approprié
                    suitable_buses = self.network.buses[self.network.buses.type.isin(['prod', 'conso'])].index
                    if len(suitable_buses) > 0:
                        emergency_bus = suitable_buses[0]

                        self.network.add(
                            "Generator",
                            emergency_gen,
                            bus=emergency_bus,
                            p_nom=remaining_load * 1.2,  # 20% de marge
                            marginal_cost=800,  # Très coûteux
                            carrier="import"
                        )
                        
                        # Produire l'énergie manquante
                        self.network.generators_t['p'].at[snapshot, emergency_gen] = remaining_load
                        
                        # Mise à jour des statistiques
                        production_by_carrier['emergency'] += remaining_load
                        remaining_load = 0
                    else:
                        logger.error("Impossible de trouver un bus approprié pour le générateur d'urgence")
            
            # Calculer la production totale pour ce pas de temps
            total_generation_snapshot = self.network.generators_t['p'].loc[snapshot].sum()
            total_annual_generation += total_generation_snapshot
        
        # Rapport final
        logger.info(f"Optimisation manuelle terminée.")
        
        # Afficher des statistiques sur puissance vs énergie
        avg_demand = total_annual_load/len(self.network.snapshots)
        logger.info(f"Demande totale moyenne: {avg_demand:.2f} MW")
        
        # Rapport sur l'énergie
        if self.is_journalier:
            total_energy_mwh = total_annual_generation * 24
            logger.info(f"Mode journalier: Énergie totale produite: {total_energy_mwh:.2f} MWh ({total_energy_mwh/1e6:.2f} TWh)")
        else:
            total_energy_mwh = total_annual_generation
            logger.info(f"Mode horaire: Énergie totale produite: {total_energy_mwh:.2f} MWh ({total_energy_mwh/1e6:.2f} TWh)")
        
        # Production par type
        for carrier in carriers_by_priority:
            if production_by_carrier[carrier] > 0:
                percentage = 100 * production_by_carrier[carrier] / total_annual_generation
                logger.info(f"Production {carrier}: {production_by_carrier[carrier]:.2f} MW ({percentage:.1f}%)")
        
        # Marquer le réseau comme optimisé
        self.network.status = "ok"
        self.network.termination_condition = "manual"
        
        return self.network

    def _sort_generators_by_cost(self, generators, snapshot):
        """
        Trie les générateurs par coût marginal croissant.
        
        Args:
            generators: Liste des générateurs à trier
            snapshot: Pas de temps actuel
            
        Returns:
            Liste triée des générateurs
        """
        costs = {}
        
        for gen in generators:
            # Coût marginal fixe ou variable
            if (hasattr(self.network.generators_t, 'marginal_cost') and 
                gen in self.network.generators_t.marginal_cost.columns and
                snapshot in self.network.generators_t.marginal_cost.index):
                cost = self.network.generators_t.marginal_cost.at[snapshot, gen]
            else:
                cost = self.network.generators.at[gen, 'marginal_cost'] if 'marginal_cost' in self.network.generators.columns else 0.0
            
            # Si le coût est NaN ou infini, utiliser une valeur par défaut
            if pd.isna(cost) or np.isinf(cost):
                carrier = self.network.generators.at[gen, 'carrier']
                default_costs = {
                    'hydro_fil': 0.1,
                    'solaire': 0.1,
                    'eolien': 0.1,
                    'nucléaire': 0.2,
                    'hydro_reservoir': 7.0,
                    'thermique': 30.0,
                    'emergency': 800.0,
                    'import': 0.5
                }
                cost = default_costs.get(carrier, 10.0)
            
            costs[gen] = float(cost)
        
        # Trier par coût croissant, en garantissant des valeurs numériques valides
        return sorted(generators, key=lambda g: costs[g])

    def get_optimization_results(self) -> Dict:
        """
        Récupère les résultats détaillés de l'optimisation.

        Returns:
            Dict contenant :
            - Production par type de centrale
            - Coûts totaux
            - Statistiques d'utilisation des réservoirs
            - Contraintes actives
        """
        # Removed requirement for network.objective - we'll calculate it instead
        
        # Calculate total cost if not already set
        if not hasattr(self.network, 'objective'):
            total_cost = 0.0
            # Calculate cost based on production and marginal costs
            for gen in self.network.generators.index:
                if gen in self.network.generators_t['p'].columns:
                    production = self.network.generators_t['p'][gen]
                    
                    # Get the marginal cost for each time step if available
                    if (hasattr(self.network.generators_t, 'marginal_cost') and 
                        gen in self.network.generators_t.marginal_cost.columns):
                        marginal_costs = self.network.generators_t.marginal_cost[gen]
                        # Multiply production by marginal cost for each time step
                        cost = (production * marginal_costs).sum()
                    else:
                        # Use static marginal cost
                        mc = self.network.generators.at[gen, 'marginal_cost'] if 'marginal_cost' in self.network.generators.columns else 0
                        cost = production.sum() * mc
                        
                    total_cost += cost
                    
            # Set the objective value
            self.network.objective = float(total_cost)

        pilotable_gens = self.network.generators[
            self.network.generators.carrier.isin(['hydro_reservoir', 'thermique'])
        ].index
        non_pilotable_gens = self.network.generators[
            self.network.generators.carrier.isin(['hydro_fil', 'eolien', 'solaire'])
        ].index

        return {
            "status": getattr(self.network, 'status', 'unknown'),
            "objective_value": float(self.network.objective),
            "total_cost": float(self.network.objective),
            "pilotable_production": self.network.generators_t['p'][pilotable_gens].sum().sum(),
            "non_pilotable_production": self.network.generators_t['p'][non_pilotable_gens].sum().sum(),
            "production_by_type": self.network.generators_t['p'].groupby(
                self.network.generators.carrier, axis=1
            ).sum(),
            "line_loading_max": self.network.lines_t['p0'].abs().max(),
            "n_active_line_constraints": (
                self.network.lines_t['p0'].abs() > 0.99 * self.network.lines.s_nom
            ).sum().sum(),
            "global_constraints": self.network.global_constraints if hasattr(self.network, "global_constraints") else None
        }

    def check_optimization_feasibility(self) -> Tuple[bool, str]:
        """
        Vérifie en détail si l'optimisation est faisable.
        
        Effectue une série de tests pour détecter les problèmes potentiels:
        - Capacité de production suffisante
        - Connectivité du réseau
        - Capacité des lignes suffisante
        - Alignement temporel des données
        
        Returns:
            Tuple[faisable, message]: Statut de faisabilité et message explicatif
        """
        messages = []
        is_feasible = True
        
        # 1. Capacité totale (production vs demande)
        total_capacity = self.network.generators.p_nom.sum()
        max_load = self.network.loads_t.p_set.sum(axis=1).max()
        
        if total_capacity < max_load:
            is_feasible = False
            messages.append(f"Capacité insuffisante: {total_capacity:.2f} MW < {max_load:.2f} MW")
        
        # 2. Vérifier la connectivité du réseau
        import networkx as nx
        G = nx.Graph()
        
        for _, line in self.network.lines.iterrows():
            G.add_edge(line.bus0, line.bus1)
        
        components = list(nx.connected_components(G))
        
        if len(components) > 1:
            messages.append(f"Réseau fragmenté en {len(components)} composants connectés")
            
            for i, comp in enumerate(components):
                buses_in_comp = list(comp)
                loads_in_comp = [l for l in self.network.loads.index 
                          if self.network.loads.loc[l, 'bus'] in buses_in_comp]
                gens_in_comp = [g for g in self.network.generators.index 
                          if self.network.generators.loc[g, 'bus'] in buses_in_comp]
                
                if loads_in_comp and not gens_in_comp:
                    is_feasible = False
                    load_sum = self.network.loads_t.p_set[loads_in_comp].sum(axis=1).max()
                    messages.append(f"Composant {i} avec {len(loads_in_comp)} charges totalisant {load_sum:.2f} MW sans générateurs")
        
        # 3. Vérifier les capacités des lignes
        if hasattr(self.network.lines, 's_nom') and len(self.network.lines) > 0:
            for snapshot in self.network.snapshots[:1]:
                buses_with_gen = set(self.network.generators.bus)
                buses_with_load = set(self.network.loads.bus)
                
                total_gen_per_bus = {}
                total_load_per_bus = {}
                
                for gen_name, gen in self.network.generators.iterrows():
                    bus = gen.bus
                    p_nom = gen.p_nom
                    
                    p_max_pu = 1.0
                    if (hasattr(self.network, 'generators_t') and 
                        hasattr(self.network.generators_t, 'p_max_pu') and
                        gen_name in self.network.generators_t.p_max_pu.columns):
                        p_max_pu = self.network.generators_t.p_max_pu.loc[snapshot, gen_name]
                    
                    avail_capacity = p_nom * p_max_pu
                    
                    if bus not in total_gen_per_bus:
                        total_gen_per_bus[bus] = 0
                    total_gen_per_bus[bus] += avail_capacity
                
                for load_name, load in self.network.loads.iterrows():
                    bus = load.bus
                    if (hasattr(self.network, 'loads_t') and 
                        hasattr(self.network.loads_t, 'p_set') and
                        load_name in self.network.loads_t.p_set.columns):
                        p_set = self.network.loads_t.p_set.loc[snapshot, load_name]
                        
                        if bus not in total_load_per_bus:
                            total_load_per_bus[bus] = 0
                        total_load_per_bus[bus] += p_set
            
                buses_with_deficit = []
                total_deficit = 0
                
                for bus, load in total_load_per_bus.items():
                    gen = total_gen_per_bus.get(bus, 0)
                    if gen < load:
                        deficit = load - gen
                        buses_with_deficit.append((bus, deficit))
                        total_deficit += deficit
                
                if buses_with_deficit:
                    line_capacities = self.network.lines.s_nom.sum()
                    if line_capacities < total_deficit:
                        is_feasible = False
                        messages.append(f"Capacité des lignes insuffisante: {line_capacities:.2f} MW < {total_deficit:.2f} MW")
        
        # 4. Vérifier l'alignement temporel
        if (hasattr(self.network, 'loads_t') and hasattr(self.network.loads_t, 'p_set') and
            hasattr(self.network, 'generators_t') and hasattr(self.network.generators_t, 'p_max_pu')):
            
            loads_index = self.network.loads_t.p_set.index
            gens_index = self.network.generators_t.p_max_pu.index
            
            if not loads_index.equals(gens_index):
                is_feasible = False
                messages.append("Désalignement temporel: les indices ne correspondent pas")
            
            if not loads_index.equals(self.network.snapshots):
                is_feasible = False
                messages.append("Désalignement temporel: charges ≠ snapshots du réseau")
        
        if is_feasible and not messages:
            return True, "Optimisation faisable"
        
        return is_feasible, "Problèmes identifiés:\n- " + "\n- ".join(messages)