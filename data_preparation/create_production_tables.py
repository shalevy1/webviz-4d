import pandas as pd

def write_data(prod_df,fluid,scale,f):
    for index,row in prod_df.iterrows():
        well_name = row["PDM well name"].replace("NO 25/11-","")

        for column in columns:
            if "-" in column:
                interval = column[0:7] + column[10:18]
                value = row[column]/scale
                print(well_name,interval,value)
                f.write(well_name + "," + interval + ",")
                f.write("%d" % value)
                f.write("," + fluid + "\n")  

#Main program

bore_oil_file = "production_data/BORE_OIL_VOL.csv"
bore_gas_file = "production_data/BORE_GAS_VOL.csv"
bore_water_file = "production_data/BORE_WAT_VOL.csv"

bore_oil = pd.read_csv(bore_oil_file)
bore_gas = pd.read_csv(bore_gas_file)
bore_water = pd.read_csv(bore_water_file)

columns = list(bore_oil)

production_file = "production_data/production_fluid_table.csv"

with open(production_file, "w") as f:
    f.write("Well_name,4D_interval,Volumes,Fluid\n")
    fluid = "Oil_[Sm3]"
    write_data(bore_oil,fluid,1,f)
            
    fluid = "Gas_[kSm3]"
    write_data(bore_gas,fluid,1000,f)

    fluid = "Water_[Sm3]"
    write_data(bore_water,fluid,1,f)
    
inject_gas_file = "production_data/BORE_GI_VOL.csv"
inject_water_file = "production_data/BORE_WI_VOL.csv"

inject_gas = pd.read_csv(inject_gas_file)
inject_water = pd.read_csv(inject_water_file)   

injection_file = "production_data/injection_fluid_table.csv"

with open(injection_file, "w") as f:   
    f.write("Well_name,4D_interval,Volumes,Fluid\n")        
    fluid = "Injected_Gas_[kSm3]"
    write_data(inject_gas,fluid,1000,f)

    fluid = "Injected_Water_[Sm3]"
    write_data(inject_water,fluid,1,f) 

