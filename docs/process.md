# RTE-equal-area-criterion-testing
Repository to test the equal area criterion software from RTE with **non-public data**


## Synthetic process

- Load and parse network topology, load flow results, relevant dynamic data		

- Simplify network in pre-fault situation	

- Launch EEAC in parallel per event								
	- Load and parse events
  
	- Simplify network in during-fault and post-fault states
  
	- Identify generators clusters:							
		
        - Filter generators list: delete hydro generators producing less than 
            					  100MW and never_critical_generators (json file parameters)						
        - Rank the machines based on the RTE Criterion, which is a variation of the 
          During Fault Trajectory process for during_fault_identification_time_step (json file parameter)						
      
        - Set the list of critical cluster candidates = 
          [ [1st critical machine], [1st critical machine, 2nd cricital machine], …]
          until the number of clusters reaches max_number_candidates (json file parameter)
      
	- Evaluate Critical Clearing Time  for each critical cluster 							
		- Calculate OMIB characteristics (ZOOMIB option)						
		- Calculate Critical Clearing Angle						
		- Calculate the Critical Clearing Time from the Critical Clearing Time			
      
	- Select the most critical cluster (lowest Critical Clearing Time)
  
- Display and dump results								
								


## Detailed

`deeac/deeac_multiple_paths.py`: Main program

	NetworkLoader – load_network									
	Load and parse network: topology, load flow results, required dynamic data									
										
	Network – initialize_simplified_network									
	Buid simplified network in pre-fault situation									
										
		Network – get_simplified_network								
		Connected buses are merged together								
		Contains only connected equipments								
		Contains only the buses and branches belonging to a connected graph								
		Add fictive buses for synchronous generators (internal voltage)								
										
			SimplifiedNetwork – admittance_matrix							
			Calculate network admittance matrix in pre-fault situation							
										
				AdmittanceMatrix – _build_matrix						
				Build admittance matrix						
										
				ReducedAdmittanceMatrix – _build_matrix						
				Reduce admittance matrix						
										
	run_parallel_fault (deeac/deeac_multiple_paths.py)									
	Launch EEAC in parallel, per event									
										
		EventLoader – load_events (deeac/IO/event_loader.py)								
		Load events								
										
			EurostagEventParser – parse_events (deeac/IO/eurostag/events/event_parser.py)							
			Parse events							
										
		Check protections time and fault impedance								
		Stop computation in case of Islanding or degraded protection								
										
		apply_events_to_network (deeac/deeac_multiple_paths.py)								
		Build simplify network in fault situation								
										
			LineShortCircuitEvent / BusShortCircuitEvent – apply_to_network							
			Bus: calculate fault bus admittance + add fictive bus							
			Line: calculate fault line admittance + add fictive load for each bus of the line							
										
			Network – get_simplified_network							
			Build simplified network in fault situation (same process as for pre-fault situation)							
										
		Build simplified network in post-fault situation								
										
			BranchEvent / BusShortCircuitClearingEvent – apply_to_network							
			Remove fictive load / bus							
										
			Network – get_simplified_network							
			Build simplify network in post-fault situation (same process as for pre-fault situation)							
										
		EEAC - _run_critical_clusters_identifier (deeac/Simulations/eeac.py)								
		Identify generators clusters: 
		- Clusters_1 : all generators except small hydro units and generators specifically 
					   excluded from configuration file (fictive generators)
		- Clusters_2 : nuclear generators only							
										
			CriticalClustersIdentifierFactory – get_identifier (deeac/Simulations/identifiers/critical_clusters_identifier.py)							
										
				DuringFaultTrajectoryCriticalClusterIdentifier - __init__ (deeac/Simulations/identifiers/during_fault_trajectory_identifier.py)						
										
					GapBasedIdentifier - __init__ (deeac/Simulations/identifiers/identifier.py)					
										
						DuringFaultTrajectoryCriticalClustersIdentifier - _compute_angle_variation_list				
						Calculate variation in angle from fault time to time step per generator				
										
							DuringFaultTrajectoryCriticalClustersIdentifier - _get_power_matrices			
							Calculate the power matrices for the Taylor series angle computation			
										
								GeneratorSnapshot arrays		
								Get rotor angles from a vectorized snapshot		
										
								SimplifiedNetwork – reduced admittance		
								Calculate admittance amplitude and angle from the reduced admittance matrix		
										
							DuringFaultTrajectoryCriticalClustersIdentifier - _get_angle_derivatives			
							Calculate 2nd and 4th order angle derivative			
										
						GapBasedIdentifier - _identify_critical_machine_candidates				
						Identify critical machines				
										
							GapBasedIdentifier - _identify_from_list			
							Sort angles			
							Calculate differences between successive elements			
							Keep right elements (resp. left) from maximum difference 
							in absolute value if value is positive (resp. negative)			
										
			CriticalClustersIdentifier - candidate_clusters							
			Create lists of critical clusters: Decrease critical machines list by one at each step. 
											   Each element substracted from the list is the one with the lowest criterion.							
										
				CriticalClustersIdentifier - _get_candidate_cluster						
				Get critical and non critical generators clusters						
										
		Merge clusters_1 and clusters_2								
		Sort critical clusters depending on number of machines per cluster								
		If number of cluster lists is greater than maximum threshold, keep the clusters on the left of the list.								
										
		EEAC - _run_critical_clusters_evaluator (deeac/Simulations/eeac.py)								
		Evaluation of each couple (critical clusters, non-critical clusters)								
										
			ZOOMIB - __init__ (deeac/Simulations/OMIB/zoomib.py)							
			Create OMIB							
										
				ZOOMIB - __init__						
				ZOOMIB model: no deviation of the rotor angle of each generator compare to 
							  Partial Center of Angle of each cluster						
										
					OMIB - __init__					
										
						OMIB - _build_state				
						Calculate electric power in pre-fault situation				
										
						OMIB – initial_rotor_angle				
						Calculate initial rotor angle of the OMIB for fault and 
						post-fault situations, at the intersection of mechanical 
						power and pre-fault electric power				
										
						OMIB - _build_state				
						Calculate electric power in fault and post-fault situations				
										
			EAC - __init__ (deeac/Simulations/eac.py)							
			Apply Equal Area Criterion to calculate the critical clearing angle							
										
				EAC - __init__						
										
					EAC - _get_critical_and_maximum_angles					
					Compute the critical clearing angle and the maximum angle based on OMIB. 
					The critical angle is the one for which the acceleration and deceleration areas are almost equal.					
										
			OMIBTaylorSeries - __init__ (deeac/Simulations/RotorAngleTrajectoryCalculator/omib_series.py)							
			Calculate trajectory							
										
				OMIBRotorAngleTrajectoryCalculator – __init__						
										
				OMIBRotorAngleTrajectoryCalculator – get_trajectory_times						
				Calculate the time to reach a specific angle, considering the machine moves from its initial angle						
										
		select_min_critical_cluster (deeac/Simulations/min_selector.py)								
		Select the most critical cluster (the one with lowest critical clearing time)								
										
	Display results									
