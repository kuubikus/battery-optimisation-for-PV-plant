import pyomo.environ as pyo
import pandas as pd

# Load data

df = pd.read_csv("sisse.csv",header=0)

# all units in kW
MIN_BATTERY_CAPACITY = 0 
MAX_BATTERY_CAPACITY = 1000 
MAX_RAW_POWER = 200 
INITIAL_CAPACITY = 0 
EFFICIENCY = 0.97 # round trip, only applied at discharge
MLF = 1 

# Define model and solver
battery = pyo.ConcreteModel()

debug = open("debug.txt", 'w')

# defining components of the objective model
# battery parameters
battery.Period = pyo.RangeSet(0,743)
battery.Produced = pyo.Param(battery.Period,initialize=list(df.produced))
battery.Price = pyo.Param(battery.Period,initialize=list(df.spot_price))
for i in range(len(battery.Price)):
    debug.write("Produced: " + str(battery.Produced[i]) + '\n')
    debug.write("price: " + str(battery.Price[i]) + '\n')
    debug.write("\n")
    

# battery varaibles
battery.Capacity = pyo.Var(battery.Period, bounds=(MIN_BATTERY_CAPACITY, MAX_BATTERY_CAPACITY))
battery.Charge_power = pyo.Var(battery.Period, bounds=(0, MAX_RAW_POWER), within=pyo.Any)
battery.Discharge_power = pyo.Var(battery.Period, bounds=(0, MAX_RAW_POWER), within=pyo.Any)

# Set constraints for the battery
# Defining capacity rule for the battery
def capacity_constraint(battery, i):
    # Assigning battery capacity at the beginning of optimisation
    if i == battery.Period.first():
        return battery.Capacity[i] == INITIAL_CAPACITY
    return battery.Capacity[i] == (battery.Capacity[i-1] + (battery.Charge_power[i-1]) - (battery.Discharge_power[i-1]))

# Make sure the battery does not charge above the limit
def over_charge(battery, i):
    return battery.Charge_power[i] <= (MAX_BATTERY_CAPACITY - battery.Capacity[i]) 

# Make sure the battery discharge the amount it actually has
def over_discharge(battery, i):
    return battery.Discharge_power[i] <= battery.Capacity[i] + battery.Produced[i]

# Make sure the battery does not discharge when price are not positive
def negative_discharge(battery, i):
    if battery.Price[i] <= 0:
        return battery.Discharge_power[i] == 0
    return pyo.Constraint.Skip

# max amount that can be loaded to the battery
def max_charge(battery,i):
    return battery.Charge_power[i] <= battery.Produced[i]

# Defining the battery objective (function to be maximised)
def maximise_profit(battery):
    rev = sum(battery.Price[i] * (battery.Discharge_power[i] * EFFICIENCY) * MLF for i in battery.Period)
    return rev


battery.obj = pyo.Objective(rule=maximise_profit, sense=pyo.maximize)
battery.cons1 = pyo.Constraint(battery.Period,rule=capacity_constraint)
battery.cons2 = pyo.Constraint(battery.Period,rule=over_charge)
battery.cons3 = pyo.Constraint(battery.Period,rule=over_discharge)
battery.cons4 = pyo.Constraint(battery.Period,rule=negative_discharge)
battery.cons5 = pyo.Constraint(battery.Period,rule=max_charge)

opt = pyo.SolverFactory('glpk')
log = opt.solve(battery)

log.write()
output = open("output.txt", 'w')

for j in range(len(battery.Capacity)):
    output.write("Capacity at {} is: ".format(j) + str(pyo.value(battery.Capacity[j]))+ '\n')
    output.write("Produced: " + str(battery.Produced[j]) + '\n')
    output.write("price: " + str(battery.Price[j]) + '\n')
    output.write("Charge_power at {} is: ".format(j)+ str(pyo.value(battery.Charge_power[j])) + '\n')
    output.write("Discharge_power at {} is: ".format(j) + str(pyo.value(battery.Discharge_power[j]))+'\n')
    output.write('\n')

output.write(str(battery.obj()/100))
output.close()