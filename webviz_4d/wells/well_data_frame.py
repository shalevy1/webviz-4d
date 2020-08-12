import os
from pathlib import Path
import pandas as pd


class WellDataFrame(object):

    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.data_frame = pd.DataFrame()
        
        if csv_file and os.path.isfile(csv_file):
            self.data_frame = pd.read_csv(csv_file)
              
        
    def get_wellbore(self,wellbore_key, wellbore_name):
        wellbore = None
        
        if self.data_frame is not None:
            wellbore = self.data_frame[self.data_frame[wellbore_key] == wellbore_name]
            
        return wellbore
        
        
def main():
    file_name = "/private/ashska/development/webviz-4d_fork/webviz-4d/grane/well_data/wellbore_info.csv"
    well_data = WellDataFrame(file_name)
    print(well_data.data_frame)
    
    wellbore = well_data.get_wellbore("wellbore.name","NO 25/11-G-2 A")
    
    print(wellbore)        
        
        
if __name__ == "__main__":
    main()        
